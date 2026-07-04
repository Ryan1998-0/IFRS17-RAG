from pathlib import Path

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.embeddings import embed_chunks, save_embedding_matrix
from rag_demo.index_store import save_index
from rag_demo.knowledge_base import active_knowledge_base
from rag_demo.vector_store import build_qdrant_vector_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_index() -> Path:
    knowledge_base = active_knowledge_base(project_root=PROJECT_ROOT)
    kb_dir = knowledge_base.raw_dir
    index_dir = knowledge_base.index_dir
    index_path = index_dir / "chunks.json"
    embedding_path = index_dir / "embeddings.npy"
    chunks = load_knowledge_base_chunks(kb_dir)
    save_index(chunks, index_path)
    embeddings = embed_chunks(chunks)
    save_embedding_matrix(embeddings, embedding_path)
    build_qdrant_vector_store(index_dir=index_dir, chunks=chunks, embeddings=embeddings)
    return index_path


def main() -> None:
    index_path = build_index()
    print(f"Index written: {index_path}")
    print(f"Embeddings written: {index_path.parent / 'embeddings.npy'}")
    print(f"Qdrant vector DB written: {index_path.parent / 'qdrant'}")


if __name__ == "__main__":
    main()
