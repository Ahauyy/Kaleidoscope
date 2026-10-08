import os
import sys
import argparse
from PIL import Image

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def parse_args():
    parser = argparse.ArgumentParser(description="Crop and generate reference anchor photo for Kaleidoscope Engine")
    parser.add_argument("--source", type=str, default="templates/reference_source.jpg", help="Path to full source selfie/portrait photo")
    parser.add_argument("--output", type=str, default="templates/ref_anchor.jpg", help="Path to save the cropped anchor portrait")
    parser.add_argument("--side", type=str, default="left", choices=["left", "right", "center"], help="Position of the anchor person in the photo")
    return parser.parse_args()

def crop_anchor(source_path, output_path, side="left"):
    if not os.path.exists(source_path):
        print(f"⚠️ Source file '{source_path}' not found.")
        print("Please place your source selfie image in 'templates/' or specify --source <path>.")
        return False
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    with Image.open(source_path) as img:
        w, h = img.size
        if side == "left":
            # Crop left half of portrait
            crop_box = (0, int(h * 0.10), int(w * 0.55), int(h * 0.85))
        elif side == "right":
            # Crop right half of portrait
            crop_box = (int(w * 0.45), int(h * 0.10), w, int(h * 0.85))
        else:
            # Center crop
            crop_box = (int(w * 0.15), int(h * 0.10), int(w * 0.85), int(h * 0.85))
            
        cropped = img.crop(crop_box)
        cropped.save(output_path, "JPEG", quality=95)
        print(f"✅ Reference anchor successfully saved to: {output_path} (Resolution: {cropped.size})")
        return True

if __name__ == "__main__":
    args = parse_args()
    crop_anchor(args.source, args.output, args.side)
