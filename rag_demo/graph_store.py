import json
from pathlib import Path

from rag_demo.knowledge_base import active_knowledge_base


def load_graph(path: Path = None, project_root: Path = None):
    graph_path = path or _default_graph_path(project_root=project_root)
    if not graph_path.exists():
        return {"entities": [], "relations": []}
    loaded = json.loads(graph_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Graph file must contain a JSON object: {graph_path}")
    loaded.setdefault("entities", [])
    loaded.setdefault("relations", [])
    return loaded


def _default_graph_path(project_root: Path = None) -> Path:
    return active_knowledge_base(project_root=project_root).graph_path
