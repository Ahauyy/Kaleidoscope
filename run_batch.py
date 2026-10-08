import os
import sys
import numpy as np
import argparse
from tqdm import tqdm
import cv2

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pipeline.utils import setup_logger, load_image_rgb, save_image_jpeg
from pipeline.detector import FaceLockDetector
from pipeline.swapper import FaceSwapper
from pipeline.postprocess import AntiAiPostProcessor

def parse_args():
    parser = argparse.ArgumentParser(description="Kaleidoscope - Identity-Preserving Dual-Selfie Engine")
    parser.add_argument("--inputs", type=str, default="inputs", help="Directory of companion/input portraits")
    parser.add_argument("--outputs", type=str, default="outputs", help="Directory to save generated selfies")
    parser.add_argument("--templates", type=str, default="templates", help="Directory of base dual-selfie templates")
    parser.add_argument("--ref-anchor", "--ref-face", "--ref-axell", dest="ref_anchor", type=str, default="templates/ref_anchor.jpg", help="Reference portrait image of the anchor person")
    parser.add_argument("--device", type=str, default="cuda", choices=["cuda", "cpu"], help="Compute device (cuda/cpu)")
    parser.add_argument("--quality", type=int, default=82, help="JPEG Quality Factor (78-85 recommended for natural compression)")
    return parser.parse_args()

def main():
    args = parse_args()
    logger = setup_logger("logs/execution.log")
    failed_log_path = "logs/failed_images.log"

    print("=" * 65)
    print("✨ KALEIDOSCOPE DUAL-SELFIE ENGINE - BATCH RUNNER")
    print("=" * 65)

    # 1. Validate Anchor Reference
    if not os.path.exists(args.ref_anchor):
        logger.error(f"Anchor reference photo not found at: {args.ref_anchor}")
        print(f"❌ Error: Anchor reference photo not found at '{args.ref_anchor}'!")
        print("💡 Place your reference photo at 'templates/ref_anchor.jpg' or run:")
        print("   python scripts/create_reference_anchor.py --source <path_to_selfie>")
        sys.exit(1)

    template_male = os.path.join(args.templates, "base_male.jpeg")
    template_female = os.path.join(args.templates, "base_female.jpeg")

    # Fallback to any image in templates if standard base names are absent
    if not os.path.exists(template_male) and not os.path.exists(template_female):
        template_candidates = [
            os.path.join(args.templates, f) for f in os.listdir(args.templates)
            if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith("ref_")
        ] if os.path.exists(args.templates) else []
        if template_candidates:
            template_male = template_female = template_candidates[0]
            logger.info(f"Using template fallback: {template_male}")

    # 2. Initialize Neural Modules
    logger.info("Initializing FaceLockDetector and FaceSwapper modules...")
    print("⏳ Loading neural models onto device...")
    detector = FaceLockDetector(models_dir="models", device=args.device)
    swapper = FaceSwapper(model_path="models/inswapper_128.onnx", device=args.device)
    postprocessor = AntiAiPostProcessor(target_jpeg_quality=args.quality)

    print("🔒 Registering biometric anchor identity (Face Lock)...")
    detector.register_anchor_from_file(args.ref_anchor)
    logger.info("Biometric anchor successfully registered and locked.")

    # 3. Scan Input Directory
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    input_files = []
    if os.path.exists(args.inputs):
        for f in os.listdir(args.inputs):
            if os.path.splitext(f.lower())[1] in valid_exts:
                input_files.append(f)

    total_files = len(input_files)
    print(f"📁 Found {total_files} input portrait(s) in: {args.inputs}")
    if total_files == 0:
        print("💡 Please place source portrait images into the 'inputs/' folder.")
        return

    os.makedirs(args.outputs, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    success_count = 0
    failed_count = 0

    # 4. Batch Execution Loop
    print(f"🚀 Processing batch of {total_files} images...\n")
    with open(failed_log_path, "w", encoding="utf-8") as f_fail:
        f_fail.write("# Batch Processing Failure Log\n")

    for filename in tqdm(input_files, desc="Synthesizing Selfies", unit="img"):
        input_path = os.path.join(args.inputs, filename)
        output_path = os.path.join(args.outputs, f"selfie_{filename}")

        try:
            # A. Load Source & Extract Face
            companion_rgb = load_image_rgb(input_path)
            source_face = detector.get_source_face(companion_rgb)

            if source_face is None:
                err_msg = f"No face detected in input: {filename}"
                logger.warning(err_msg)
                with open(failed_log_path, "a", encoding="utf-8") as f_fail:
                    f_fail.write(f"{filename}: {err_msg}\n")
                failed_count += 1
                continue

            # B. Adaptive Template Selection
            is_female = getattr(source_face, 'gender', 1) == 0
            if is_female and os.path.exists(template_female):
                selected_template_path = template_female
            elif os.path.exists(template_male):
                selected_template_path = template_male
            else:
                selected_template_path = template_female if os.path.exists(template_female) else None

            if not selected_template_path or not os.path.exists(selected_template_path):
                raise FileNotFoundError("No valid template found in templates directory.")

            # C. Template Facial Analysis
            template_rgb = load_image_rgb(selected_template_path)
            anchor_face, target_face = detector.analyze_template(template_rgb)

            if target_face is None:
                err_msg = f"Companion target face slot not detected in template for {filename}"
                logger.warning(err_msg)
                with open(failed_log_path, "a", encoding="utf-8") as f_fail:
                    f_fail.write(f"{filename}: {err_msg}\n")
                failed_count += 1
                continue

            # D. Neural Identity Transfer
            swapped_rgb = swapper.swap_face(template_rgb, target_face, source_face)

            # E. Anti-AI Optical Realism & Harmonization
            swapped_bgr = cv2.cvtColor(swapped_rgb, cv2.COLOR_RGB2BGR)
            
            # Anchor face patch for color calibration
            anc_box = [int(v) for v in anchor_face.bbox]
            anchor_patch = swapped_bgr[max(0, anc_box[1]):anc_box[3], max(0, anc_box[0]):anc_box[2]]
            
            # Soft target face mask for grain & lighting harmonization
            h_img, w_img, _ = swapped_bgr.shape
            mask_target = np.zeros((h_img, w_img), dtype=np.uint8)
            t_box = [int(v) for v in target_face.bbox]
            cv2.rectangle(mask_target, (max(0, t_box[0]), max(0, t_box[1])), (min(w_img, t_box[2]), min(h_img, t_box[3])), 255, -1)
            mask_target = cv2.GaussianBlur(mask_target, (25, 25), 10)

            harmonized_bgr = postprocessor.harmonize(
                swapped_bgr, 
                face_mask=mask_target, 
                anchor_patch_bgr=anchor_patch
            )
            harmonized_rgb = cv2.cvtColor(harmonized_bgr, cv2.COLOR_BGR2RGB)

            # F. Save Image with Sensor Compression Profile
            save_image_jpeg(harmonized_rgb, output_path, quality=args.quality)
            success_count += 1
            logger.info(f"Successfully processed: {filename} -> {output_path}")

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}", exc_info=True)
            with open(failed_log_path, "a", encoding="utf-8") as f_fail:
                f_fail.write(f"{filename}: Exception: {str(e)}\n")
            failed_count += 1

    print("\n" + "=" * 65)
    print("🏁 BATCH SYNTHESIS COMPLETE")
    print(f"• Success : {success_count} / {total_files}")
    print(f"• Failed  : {failed_count} / {total_files}")
    print(f"• Outputs : Saved to '{args.outputs}'")
    if failed_count > 0:
        print(f"• Failure log recorded at '{failed_log_path}'")
    print("=" * 65)

if __name__ == "__main__":
    main()
