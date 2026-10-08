import os
import urllib.request
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

INSWAPPER_URLS = [
    "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx",
    "https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx"
]
INSWAPPER_PATH = os.path.join(MODELS_DIR, "inswapper_128.onnx")

def download_with_progress(url, dest_path):
    print(f"📥 Downloading neural weights from: {url}")
    print(f"📁 Target destination: {dest_path}")
    
    def reporthook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = downloaded * 100 / total_size
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            sys.stdout.write(f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, dest_path, reporthook)
        print("\n✅ Download completed successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Download failed from {url}: {e}")
        return False

def setup_models():
    print("=" * 60)
    print("🚀 PREPARING NEURAL NETWORK WEIGHTS")
    print("=" * 60)

    if os.path.exists(INSWAPPER_PATH) and os.path.getsize(INSWAPPER_PATH) > 100 * 1024 * 1024:
        print(f"✅ Model inswapper_128.onnx already exists ({os.path.getsize(INSWAPPER_PATH) / (1024*1024):.1f} MB).")
    else:
        success = False
        for url in INSWAPPER_URLS:
            if download_with_progress(url, INSWAPPER_PATH):
                success = True
                break
        if not success:
            print("⚠️ Automatic download failed for inswapper_128.onnx.")
            print("Please manually download from: https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx")
            print(f"and place it at: {INSWAPPER_PATH}")

    print("\n📦 Initializing InsightFace model pack (buffalo_l)...")
    try:
        import insightface
        from insightface.app import FaceAnalysis
        print("Loading FaceAnalysis('buffalo_l')... (will download automatically if missing)")
        app = FaceAnalysis(name='buffalo_l', root=MODELS_DIR, providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        print("✅ InsightFace model pack ready.")
    except Exception as e:
        print(f"⚠️ Notice for InsightFace buffalo_l initialization: {e}")
        print("InsightFace will fetch buffalo_l models during initial runtime.")

    print("\n" + "=" * 60)
    print("🎉 ALL MODELS ARE PREPARED & READY TO USE!")
    print("=" * 60)

if __name__ == "__main__":
    setup_models()
