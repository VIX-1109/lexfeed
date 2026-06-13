from sentence_transformers import SentenceTransformer
import numpy as np
from app.config import EMBEDDING_MODEL

# Load model once — runs locally, no API needed
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> list:
    """Convert text to a 384-dimensional embedding vector."""
    model = get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def embed_texts(texts: list) -> list:
    """Batch embed multiple texts."""
    model = get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=True)
    return embeddings.tolist()


def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two vectors."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def average_vectors(vectors: list) -> list:
    """Average multiple vectors into one — used for building user interest vectors."""
    if not vectors:
        return [0.0] * 384
    arr = np.array(vectors)
    avg = np.mean(arr, axis=0)
    norm = np.linalg.norm(avg)
    if norm > 0:
        avg = avg / norm
    return avg.tolist()


def weighted_update(current_vector: list, new_vector: list, weight: float, decay: float = 0.9) -> list:
    """
    Update user interest vector with a new post embedding.
    Uses weighted moving average so recent interactions matter more.
    """
    current = np.array(current_vector)
    new = np.array(new_vector)
    updated = (current * decay) + (new * weight * (1 - decay))
    norm = np.linalg.norm(updated)
    if norm > 0:
        updated = updated / norm
    return updated.tolist()
