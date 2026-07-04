import json
from pathlib import Path
from typing import List

from rag_demo.chunking import Chunk


def save_index(chunks: List[Chunk], index_path: Path) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_index(index_path: Path) -> List[Chunk]:
    return json.loads(index_path.read_text(encoding="utf-8"))

