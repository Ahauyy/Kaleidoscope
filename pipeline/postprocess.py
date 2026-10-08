import cv2
import numpy as np
from PIL import Image

class AntiAiPostProcessor:
    """
    Modul Anti-Generative Guardrail:
    Bertanggung jawab menghilangkan kesan artifisial AI dengan menyelaraskan
    skin tone, menyuntikkan noise sensor kamera, dan mengemulasikan tekstur kompresi WhatsApp.
    """
    
    def __init__(self, target_jpeg_quality=80):
        self.target_jpeg_quality = target_jpeg_quality

    def reinhard_color_transfer(self, source_bgr, reference_bgr, mask=None):
        """
        Menyelaraskan distribusi warna (skin tone) dari source_bgr agar sesuai
        dengan kondisi pencahayaan dan saturasi reference_bgr menggunakan ruang warna CIELAB.
        """
        src_lab = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        ref_lab = cv2.cvtColor(reference_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)

        if mask is not None and np.sum(mask) > 0:
            mask_bool = mask > 0
            src_pixels = src_lab[mask_bool]
            ref_pixels = ref_lab[mask_bool] if ref_lab.shape == src_lab.shape else ref_lab.reshape(-1, 3)
        else:
            src_pixels = src_lab.reshape(-1, 3)
            ref_pixels = ref_lab.reshape(-1, 3)

        src_mean, src_std = src_pixels.mean(axis=0), src_pixels.std(axis=0) + 1e-6
        ref_mean, ref_std = ref_pixels.mean(axis=0), ref_pixels.std(axis=0) + 1e-6

        # Normalisasi dan scaling deviasi standar
        res_lab = (src_lab - src_mean) * (ref_std / src_std) + ref_mean
        res_lab = np.clip(res_lab, 0, 255).astype(np.uint8)

        return cv2.cvtColor(res_lab, cv2.COLOR_LAB2BGR)

    def inject_sensor_noise(self, image_bgr, mask=None, noise_intensity=3.5):
        """
        Menginjeksikan noise sensor sintetis (Gaussian + Salt & Pepper mikro)
        ke area wajah agar pori-pori dan tekstur kulit tidak tampak seperti 'lilin/plastik'.
        """
        h, w, c = image_bgr.shape
        # Hasilkan noise Gaussian zero-mean
        gaussian_noise = np.random.normal(0, noise_intensity, (h, w, c))
        noisy_image = image_bgr.astype(np.float32) + gaussian_noise
        noisy_image = np.clip(noisy_image, 0, 255).astype(np.uint8)

        if mask is not None:
            # Gunakan mask bergradien lembut (feathered mask)
            if len(mask.shape) == 2:
                mask_3c = np.stack([mask] * 3, axis=-1) / 255.0
            else:
                mask_3c = mask / 255.0
            blended = (noisy_image * mask_3c + image_bgr * (1.0 - mask_3c)).astype(np.uint8)
            return blended

        return noisy_image

    def apply_bloom_spill(self, image_bgr, light_color=(255, 245, 230), intensity=0.08):
        """
        Menambahkan sedikit ambient light bloom halus di bagian atas frame
        khas lampu fluorescent aula/plafon pada kamera HP berbekas sidik jari/minyak.
        """
        h, w, _ = image_bgr.shape
        y_grad = np.linspace(1.0, 0.0, h)[:, None] ** 2.0
        light_layer = np.full((h, w, 3), light_color, dtype=np.float32)
        bloom_mask = np.repeat(y_grad[:, :, None] * intensity, 3, axis=2)
        
        result = image_bgr.astype(np.float32) * (1.0 - bloom_mask) + light_layer * bloom_mask
        return np.clip(result, 0, 255).astype(np.uint8)

    def harmonize(self, full_composite_bgr, face_mask=None, anchor_patch_bgr=None, axell_patch_bgr=None):
        """
        Complete Anti-AI Harmonization pipeline:
        1. Color tone matching with reference anchor
        2. Natural CMOS sensor noise injection
        3. Subtle environmental soft bloom
        """
        processed = full_composite_bgr.copy()
        ref_patch = anchor_patch_bgr if anchor_patch_bgr is not None else axell_patch_bgr
        
        # 1. Color Transfer (if reference anchor patch provided)
        if ref_patch is not None and face_mask is not None:
            processed = self.reinhard_color_transfer(processed, ref_patch, mask=face_mask)
            
        # 2. Camera CMOS sensor noise injection
        processed = self.inject_sensor_noise(processed, mask=face_mask, noise_intensity=3.0)
        
        # 3. Soft environmental bloom
        processed = self.apply_bloom_spill(processed, intensity=0.04)
        
        return processed
