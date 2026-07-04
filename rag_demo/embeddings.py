import os
from pathlib import Path
from typing import Callable, Dict, List, Sequence

import numpy as np

from rag_demo.chunking import Chunk


DEFAULT_EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

_EMBEDDING_MODEL_CACHE: Dict[str, object] = {}


def chunk_to_embedding_text(chunk: Chunk) -> str:
    return f"{chunk.get('parent_title', '')}\n{chunk['title']}\n{chunk['content']}"


def embed_texts(
    texts: Sequence[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    model_factory: Callable[[str], object] = None,
) -> List[List[float]]:
    model = _get_embedding_model(model_name, model_factory=model_factory)
    embeddings = model.encode(
        list(texts),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(embeddings, dtype=np.float32).tolist()


def embed_chunks(chunks: Sequence[Chunk], model_name: str = DEFAULT_EMBEDDING_MODEL) -> List[List[float]]:
    return embed_texts([chunk_to_embedding_text(chunk) for chunk in chunks], model_name=model_name)


def embed_query(query: str, model_name: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    return embed_texts([query], model_name=model_name)[0]


def save_embedding_matrix(matrix: Sequence[Sequence[float]], matrix_path: Path) -> None:
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(matrix_path, np.asarray(matrix, dtype=np.float32))


def load_embedding_matrix(matrix_path: Path) -> List[List[float]]:
    return np.load(matrix_path).astype(float).tolist()


def clear_embedding_model_cache() -> None:
    _EMBEDDING_MODEL_CACHE.clear()


def _get_embedding_model(model_name: str, model_factory: Callable[[str], object] = None):
    if model_name not in _EMBEDDING_MODEL_CACHE:
        factory = model_factory or _default_model_factory
        _EMBEDDING_MODEL_CACHE[model_name] = factory(model_name)
    return _EMBEDDING_MODEL_CACHE[model_name]


def _default_model_factory(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers is required for embedding search. "
            "Install it with: python3 -m pip install sentence-transformers"
        ) from exc
    return SentenceTransformer(model_name)
