import os
import sys
import cv2
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from pipeline.utils import cosine_similarity

class FaceLockDetector:
    """
    Biometric Face Lock & Identity Preservation Detector.
    Ensures anchor subject is identified biometrically and never swapped or altered.
    """
    
    def __init__(self, models_dir="models", device="cuda"):
        self.models_dir = os.path.abspath(models_dir)
        self.device = device
        self.app = None
        self.anchor_embedding = None
        self._init_face_analysis()

    def _init_face_analysis(self):
        try:
            import insightface
            from insightface.app import FaceAnalysis

            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.device == "cuda" else ['CPUExecutionProvider']
            self.app = FaceAnalysis(name='buffalo_l', root=self.models_dir, providers=providers)
            self.app.prepare(ctx_id=0 if self.device == "cuda" else -1, det_size=(640, 640))
        except Exception as e:
            print(f"⚠️ FaceAnalysis InsightFace initialization notice: {e}")
            self.app = None

    def register_anchor(self, anchor_img_rgb):
        """
        Extracts and registers 512-dimensional facial embedding for the anchor subject.
        """
        if self.app is None:
            raise RuntimeError("InsightFace FaceAnalysis app is not initialized.")
        
        anchor_bgr = cv2.cvtColor(anchor_img_rgb, cv2.COLOR_RGB2BGR)
        faces = self.app.get(anchor_bgr)
        if not faces:
            raise ValueError("No face detected in reference anchor image!")
        
        # Select largest dominant face
        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        self.anchor_embedding = faces[0].embedding
        return faces[0]

    def register_anchor_from_file(self, file_path):
        from pipeline.utils import load_image_rgb
        img = load_image_rgb(file_path)
        return self.register_anchor(img)

    # Aliases for backwards compatibility
    def register_axell(self, img):
        return self.register_anchor(img)

    def register_axell_from_file(self, file_path):
        return self.register_anchor_from_file(file_path)

    @property
    def axell_embedding(self):
        return self.anchor_embedding

    @axell_embedding.setter
    def axell_embedding(self, value):
        self.anchor_embedding = value

    def analyze_template(self, template_img_rgb, sim_threshold=0.45):
        """
        Analyzes dual-selfie template photo.
        Returns tuple: (anchor_face, target_companion_face)
        """
        if self.app is None:
            raise RuntimeError("InsightFace app is not initialized.")
        if self.anchor_embedding is None:
            raise RuntimeError("Anchor face is not registered! Call register_anchor first.")

        template_bgr = cv2.cvtColor(template_img_rgb, cv2.COLOR_RGB2BGR)
        faces = self.app.get(template_bgr)

        if len(faces) < 2:
            if len(faces) == 1:
                sim = cosine_similarity(self.anchor_embedding, faces[0].embedding)
                if sim >= sim_threshold:
                    return faces[0], None
                else:
                    return None, faces[0]
            return None, None

        # Compare cosine similarity against anchor embedding
        face_scores = []
        for face in faces:
            sim = cosine_similarity(self.anchor_embedding, face.embedding)
            bbox_area = (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
            face_scores.append((face, sim, bbox_area))

        # Best matching face for anchor
        face_scores_sorted_by_sim = sorted(face_scores, key=lambda x: x[1], reverse=True)
        best_match_anchor, best_sim, _ = face_scores_sorted_by_sim[0]

        if best_sim < sim_threshold:
            print(f"⚠️ Notice: Best anchor face similarity is {best_sim:.2f} (below threshold {sim_threshold})")

        anchor_face = best_match_anchor

        # Target companion face is the companion with significant bounding box area
        other_faces = [f for f in face_scores if f[0] is not anchor_face]
        other_faces_sorted = sorted(other_faces, key=lambda x: x[2], reverse=True)
        target_face = other_faces_sorted[0][0] if other_faces else None

        return anchor_face, target_face

    def get_source_face(self, source_img_rgb):
        """
        Extracts dominant source facial features for face swap transfer.
        """
        if self.app is None:
            raise RuntimeError("InsightFace app is not initialized.")
        
        src_bgr = cv2.cvtColor(source_img_rgb, cv2.COLOR_RGB2BGR)
        faces = self.app.get(src_bgr)
        if not faces:
            return None
        
        faces = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0]) * (x.bbox[3]-x.bbox[1]), reverse=True)
        return faces[0]
