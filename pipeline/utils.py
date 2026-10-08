import os
import logging
from PIL import Image, ImageOps
import numpy as np

def setup_logger(log_file="logs/execution.log"):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logger = logging.getLogger("Kaleidoscope")
    logger.setLevel(logging.INFO)
    
    # Hindari duplikasi handler jika sudah ada
    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger

def load_image_rgb(image_path):
    """
    Memuat gambar, memperbaiki orientasi EXIF kamera HP secara otomatis,
    dan mengembalikan dalam format numpy array RGB (H, W, 3).
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"File tidak ditemukan: {image_path}")
    
    with Image.open(image_path) as img:
        # Perbaiki rotasi EXIF yang sering ada di foto smartphone
        img = ImageOps.exif_transpose(img)
        img_rgb = img.convert("RGB")
        return np.array(img_rgb)

def save_image_jpeg(numpy_rgb, output_path, quality=80):
    """
    Menyimpan numpy array RGB ke format JPEG dengan Quality Factor dan subsampling 4:2:0.
    """
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    pil_img = Image.fromarray(numpy_rgb)
    pil_img.save(output_path, "JPEG", quality=quality, subsampling="4:2:0", optimize=True)

def cosine_similarity(feat1, feat2):
    """
    Menghitung kemiripan kosinus antara dua vektor embedding 512-dimensi.
    """
    f1 = np.asarray(feat1, dtype=np.float32)
    f2 = np.asarray(feat2, dtype=np.float32)
    dot = np.dot(f1, f2)
    norm = np.linalg.norm(f1) * np.linalg.norm(f2)
    if norm < 1e-6:
        return 0.0
    return float(dot / norm)
