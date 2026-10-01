"""Build, save, load and search the index.

Search is hybrid: BM25 (exact keywords) + embeddings (meaning), merged with
Reciprocal Rank Fusion. RRF only uses rank positions, so we don't have to
make BM25 scores and cosine similarities comparable.
"""

import json
from pathlib import Path

import numpy as np

from . import providers
from .bm25 import BM25
from .chunk import Chunk, chunk_blocks
from .config import settings
from .extract import extract_folder

RRF_K = 60


def build_index(docs_dir: Path = settings.docs_dir, index_dir: Path = settings.index_dir) -> int:
    print(f"Extracting PDFs from {docs_dir}")
    blocks = extract_folder(docs_dir)
    chunks = chunk_blocks(blocks, settings.chunk_chars)
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "chunks.json").write_text(json.dumps([c.to_dict() for c in chunks], indent=1))
    print(f"{len(chunks)} chunks written")

    emb_file = index_dir / "embeddings.npy"
    if settings.embed_provider == "none":
        emb_file.unlink(missing_ok=True)
        print("EMBED_PROVIDER=none, keyword search only")
    else:
        print(f"Embedding with {settings.embed_provider} ...")
        vectors = np.array(providers.embed([c.text for c in chunks]), dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
        np.save(emb_file, vectors)
        print(f"Embeddings saved: {vectors.shape}")
    return len(chunks)


class Index:
    def __init__(self, index_dir: Path = settings.index_dir):
        path = index_dir / "chunks.json"
        if not path.exists():
            raise SystemExit("No index found. Run: python -m taxrag ingest")
        self.chunks = [Chunk(**c) for c in json.loads(path.read_text())]
        self.bm25 = BM25([c.text for c in self.chunks])
        emb_file = index_dir / "embeddings.npy"
        use_dense = settings.embed_provider != "none" and emb_file.exists()
        self.vectors = np.load(emb_file) if use_dense else None

    def search(self, query: str, k: int = settings.top_k) -> list[tuple[Chunk, float]]:
        rankings = [np.argsort(self.bm25.scores(query))[::-1]]

        if self.vectors is not None:
            q = np.array(providers.embed([query])[0], dtype=np.float32)
            q /= np.linalg.norm(q) + 1e-9
            rankings.append(np.argsort(self.vectors @ q)[::-1])

        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, idx in enumerate(ranking[:50]):
                fused[int(idx)] = fused.get(int(idx), 0.0) + 1.0 / (RRF_K + rank + 1)

        best = sorted(fused.items(), key=lambda x: x[1], reverse=True)[:k]
        return [(self.chunks[i], score) for i, score in best]
