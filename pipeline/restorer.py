import os
import sys
import cv2
import numpy as np
import torch

# Ensure torch CUDA dlls are loaded for onnxruntime CUDA execution provider
torch_lib = os.path.join(os.path.dirname(torch.__file__), 'lib')
if os.path.exists(torch_lib):
    try:
        os.add_dll_directory(torch_lib)
    except Exception:
        pass
    os.environ['PATH'] = torch_lib + os.pathsep + os.environ['PATH']

import onnxruntime as ort
from insightface.utils import face_align

class CodeFormerRestorer:
    """
    Modul Restorasi Wajah Beresolusi Tinggi menggunakan CodeFormer ONNX.
    Mengembalikan detail mikro wajah (mata, hidung, bibir, kerutan alami, tekstur)
    dari kompresi 128px inswapper agar sangat mirip dengan wajah asli input.
    """
    def __init__(self, model_path="models/codeformer.onnx", device="cuda"):
        self.model_path = os.path.abspath(model_path)
        self.device = device
        self.session = None
        self._init_session()

    def _init_session(self):
        if not os.path.exists(self.model_path):
            print(f"⚠️ Model CodeFormer tidak ditemukan di {self.model_path}")
            return

        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.device == "cuda" else ['CPUExecutionProvider']
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        try:
            self.session = ort.InferenceSession(self.model_path, sess_options=sess_options, providers=providers)
            active_p = self.session.get_providers()
            print(f"✅ CodeFormer ONNX dimuat sukses dengan provider: {active_p}")
        except Exception as e:
            print(f"⚠️ Gagal memuat CodeFormer dengan GPU ({e}), fallback ke CPU...")
            self.session = ort.InferenceSession(self.model_path, sess_options=sess_options, providers=['CPUExecutionProvider'])

    def restore_face(self, image_rgb, target_face, fidelity_weight=0.75):
        """
        Melakukan face restoration pada target_face di dalam image_rgb:
        - image_rgb: gambar penuh (RGB format)
        - target_face: objek Face dari InsightFace (memiliki kps / landmark 5 titik)
        - fidelity_weight: 0.0 (sangat halus/generatif) s.d. 1.0 (sangat mirip identitas asli).
          Rekomendasi ideal: 0.75 s.d. 0.85
        """
        if self.session is None:
            return image_rgb

        h, w, _ = image_rgb.shape
        lmk = target_face.kps.astype(np.float32)

        # 1. Hitung transformation matrix ke 512x512
        M = face_align.estimate_norm(lmk, image_size=512, mode='arcface')
        if M is None:
            return image_rgb

        # 2. Warp wajah ke 512x512
        aligned_rgb = cv2.warpAffine(image_rgb, M, (512, 512), borderMode=cv2.BORDER_REFLECT)

        # 3. Preprocess CodeFormer (RGB [-1, 1], shape [1, 3, 512, 512])
        norm_img = (aligned_rgb.astype(np.float32) / 255.0 - 0.5) / 0.5
        input_tensor = np.transpose(norm_img, (2, 0, 1))[None, ...].astype(np.float32)
        weight_val = np.array(fidelity_weight, dtype=np.float64)

        # 4. Inferensi CodeFormer
        outputs = self.session.run(None, {
            'input': input_tensor,
            'weight': weight_val
        })
        restored_tensor = outputs[0][0] # shape (3, 512, 512)
        restored_512 = np.transpose(restored_tensor, (1, 2, 0))
        restored_512 = np.clip((restored_512 * 0.5 + 0.5) * 255.0, 0, 255).astype(np.uint8)

        # 5. Buat feathered mask halus untuk penempelan kembali (oval face mask)
        mask_512 = np.zeros((512, 512), dtype=np.float32)
        cv2.ellipse(mask_512, (256, 256), (195, 235), 0, 0, 360, 1.0, -1)
        # Blur feathering lembut
        mask_512 = cv2.GaussianBlur(mask_512, (51, 51), 0)

        # 6. Inverse affine warp kembali ke kanvas gambar penuh
        M_inv = cv2.invertAffineTransform(M)
        restored_full = cv2.warpAffine(restored_512, M_inv, (w, h), borderMode=cv2.BORDER_REFLECT)
        mask_full = cv2.warpAffine(mask_512, M_inv, (w, h), borderValue=0.0)

        # 7. Alpha blending lembut dengan background asli
        mask_3c = np.repeat(mask_full[:, :, None], 3, axis=2)
        blended = (restored_full.astype(np.float32) * mask_3c + image_rgb.astype(np.float32) * (1.0 - mask_3c))
        blended = np.clip(blended, 0, 255).astype(np.uint8)

        return blended
