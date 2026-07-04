import re
from typing import Iterable, Mapping, Optional

from rag_demo.entity_aliases import load_alias_records


def extract_query_entities(
    query: str,
    alias_records: Optional[Iterable[Mapping[str, object]]] = None,
    project_root=None,
):
    records = list(alias_records) if alias_records is not None else load_alias_records(project_root=project_root)
    return _extract_entities_from_text(query, records)


def extract_chunk_entities(
    chunk,
    alias_records: Optional[Iterable[Mapping[str, object]]] = None,
    project_root=None,
):
    records = list(alias_records) if alias_records is not None else load_alias_records(project_root=project_root)
    text = "\n".join(
        str(chunk.get(field, ""))
        for field in ("parent_title", "title", "content")
    )
    return _extract_entities_from_text(text, records)


def _extract_entities_from_text(text: str, records):
    compact_text = _compact(text)
    entities = []
    seen = set()
    for record in records:
        name = str(record.get("canonical") or record.get("name") or "").strip()
        if not name:
            continue
        terms = [name]
        terms.extend(str(alias) for alias in record.get("aliases", []) or [])
        if not any(_compact(term) and _compact(term) in compact_text for term in terms):
            continue
        entity_type = str(record.get("type", "entity")).strip().lower()
        key = (_compact(name), entity_type)
        if key in seen:
            continue
        seen.add(key)
        entities.append(
            {
                "name": name,
                "type": entity_type,
                "matched_terms": [term for term in terms if _compact(term) and _compact(term) in compact_text],
            }
        )
    return entities


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()
