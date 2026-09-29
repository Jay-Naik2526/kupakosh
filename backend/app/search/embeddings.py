"""Local sentence embeddings for every report sentence (SPEC.md §4: bge-small-en-v1.5, 384-dim, offline).

Stand-in for pgvector in this SQLite build: vectors live in data/processed/embeddings.npy (float16, L2-normalised)
with the passage ids in embeddings_ids.npy. `build()` embeds only passages not yet embedded (incremental).
If the model or the files are missing, search falls back to keyword (BM25) only and says so.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np
from sqlalchemy import select

from app.config import DATA_DIR, cfg
from app.db.models import Passage

VEC = DATA_DIR / "processed" / "embeddings.npy"
IDS = DATA_DIR / "processed" / "embeddings_ids.npy"
HASH = DATA_DIR / "processed" / "embeddings_hash.npy"  # text fingerprint: passage ids are reused after a rebuild


def _fp(text: str) -> int:
    return int.from_bytes(hashlib.sha1(text.encode("utf-8", "ignore")).digest()[:8], "little", signed=True)


@lru_cache(maxsize=1)
def model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(cfg()["embeddings"]["model"])


def build(db, log=print, rebuild: bool = False) -> dict:
    """Vectors for every passage. A stored vector is reused for any passage whose text fingerprint matches, so
    unchanged sentences are never re-encoded (ids change when the DB is rebuilt; text does not)."""
    c = cfg()["embeddings"]
    ok = VEC.exists() and HASH.exists() and not rebuild
    old = {}
    if ok:
        ovec, ofp = np.load(VEC), np.load(HASH)
        old = {int(f): i for i, f in enumerate(ofp.tolist())}
    live = db.execute(select(Passage.id, Passage.text).order_by(Passage.id)).all()
    ids = np.array([i for i, _ in live], dtype=np.int64)
    fps = np.array([_fp(t) for _, t in live], dtype=np.int64)
    vec = np.zeros((len(live), c["dim"]), dtype=np.float16)
    todo = []
    for k, f in enumerate(fps.tolist()):
        if f in old:
            vec[k] = ovec[old[f]]
        else:
            todo.append(k)
    if todo:
        log(f"embeddings: encoding {len(todo):,} new passages with {c['model']}")
        new = model().encode([live[k][1] for k in todo], batch_size=c["batch"], normalize_embeddings=True, show_progress_bar=False)
        vec[todo] = new.astype(np.float16)
    VEC.parent.mkdir(parents=True, exist_ok=True)
    np.save(VEC, vec)
    np.save(IDS, ids)
    np.save(HASH, fps)
    index.cache_clear()
    log(f"embeddings: {len(ids):,} passages indexed ({len(todo):,} newly encoded)")
    return {"indexed": int(len(ids)), "new": len(todo)}


@lru_cache(maxsize=1)
def index():
    """(passage ids, vectors). Vectors stay float16 as stored (half the memory of float32); cosine() widens a chunk at a time."""
    if not (VEC.exists() and IDS.exists()):
        return None
    return np.load(IDS), np.load(VEC)


def cosine(qv: np.ndarray, chunk: int = 32768) -> np.ndarray:
    """Cosine of a normalised query vector with every stored vector, computed in float32 chunks."""
    _, vec = index()
    qv = qv.astype(np.float32)
    out = np.empty(len(vec), dtype=np.float32)
    for s in range(0, len(vec), chunk):
        out[s:s + chunk] = vec[s:s + chunk].astype(np.float32) @ qv
    return out


def available() -> bool:
    return index() is not None


def search(q: str, n: int) -> list[tuple[int, float]]:
    """Top-n (passage_id, cosine) by meaning. Empty list when no index exists."""
    ix = index()
    if ix is None:
        return []
    ids, vec = ix
    c = cfg()["embeddings"]
    qv = model().encode([c["query_prefix"] + q], normalize_embeddings=True)[0].astype(np.float32)
    s = cosine(qv)
    top = np.argpartition(-s, min(n, len(s) - 1))[:n]
    top = top[np.argsort(-s[top])]
    return [(int(ids[i]), float(s[i])) for i in top]
