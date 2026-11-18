import time
import json
import numpy as np
from sqlalchemy.orm import Session
from backend.database.models import FaceReUser

class FaceUserCache:
    def __init__(self, refresh_interval: int = 10):
        self.refresh_interval = refresh_interval
        self.last_refresh = 0
        self.users = []              # now stores dicts, not ORM objects
        self.embeddings_matrix = np.array([])
        self.ids = []

    def refresh_if_needed(self, db: Session):
        now = time.time()
        if now - self.last_refresh > self.refresh_interval:
            self._refresh(db)
            self.last_refresh = now

    def _refresh(self, db: Session):
        users = db.query(FaceReUser).all()

        # Convert ORM objects into plain dicts
        user_dicts = []
        embeddings = []
        ids = []

        for u in users:
            if isinstance(u.embedding, str):
                emb = json.loads(u.embedding)
            else:
                emb = u.embedding

            user_dicts.append({
                "id": u.id,
                "name": u.name,
                "embedding": np.array(emb)
            })
            embeddings.append(emb)
            ids.append(u.id)

        self.users = user_dicts
        self.ids = ids
        self.embeddings_matrix = np.array(embeddings) if embeddings else np.array([])

    def find_best_match(self, face_embedding, threshold: float = 0.6):
        if self.embeddings_matrix.shape[0] == 0:
            return None, 0.0

        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity([face_embedding], self.embeddings_matrix)[0]

        best_idx = np.argmax(sims)
        best_sim = sims[best_idx]

        if best_sim > threshold:
            return self.users[best_idx], best_sim  # returns dict, not ORM
        return None, best_sim

# Global singleton cache instance
face_cache = FaceUserCache()
