import os
import sys
import cv2
import numpy as np

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

class FaceSwapper:
    """
    Modul Eksekusi Identity Transfer menggunakan model Inswapper ONNX.
    """
    
    def __init__(self, model_path="models/inswapper_128.onnx", device="cuda"):
        self.model_path = os.path.abspath(model_path)
        self.device = device
        self.swapper = None
        self._init_swapper()

    def _init_swapper(self):
        if not os.path.exists(self.model_path):
            print(f"⚠️ Model inswapper belum ditemukan di: {self.model_path}")
            return

        try:
            import insightface
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.device == "cuda" else ['CPUExecutionProvider']
            self.swapper = insightface.model_zoo.get_model(self.model_path, providers=providers)
            print(f"✅ Inswapper model dimuat dari: {self.model_path}")
        except Exception as e:
            print(f"❌ Gagal memuat Inswapper model: {e}")
            self.swapper = None

    def swap_face(self, template_img_rgb, target_face, source_face):
        """
        Melakukan pertukaran wajah:
        - template_img_rgb : citra template selfie penuh (RGB)
        - target_face       : objek Face rekan yang akan diganti pada template
        - source_face       : objek Face teman input yang menyumbangkan identitas
        
        Mengembalikan: citra hasil swap (RGB)
        """
        if self.swapper is None:
            raise RuntimeError("Model swapper belum terinisialisasi!")

        template_bgr = cv2.cvtColor(template_img_rgb, cv2.COLOR_RGB2BGR)
        
        # Eksekusi inswapper (paste_back=True menempelkan kembali ke canvas template asli)
        result_bgr = self.swapper.get(template_bgr, target_face, source_face, paste_back=True)
        
        return cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
