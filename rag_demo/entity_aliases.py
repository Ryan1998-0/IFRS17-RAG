import json
import re
from pathlib import Path
from typing import Iterable, List, Mapping, Optional

from rag_demo.knowledge_base import active_knowledge_base


def load_alias_records(
    path: Optional[Path] = None,
    project_root: Optional[Path] = None,
) -> List[Mapping[str, object]]:
    alias_path = path or _default_alias_path(project_root=project_root)
    if not alias_path.exists():
        return []
    loaded = json.loads(alias_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise ValueError(f"Entity alias file must contain a JSON list: {alias_path}")
    return [record for record in loaded if isinstance(record, dict)]


def expand_query_with_aliases(
    query: str,
    alias_records: Optional[Iterable[Mapping[str, object]]] = None,
    project_root: Optional[Path] = None,
) -> str:
    records = list(alias_records) if alias_records is not None else load_alias_records(project_root=project_root)
    additions: List[str] = []

    for record in records:
        if not _record_matches(query, record):
            continue
        additions.extend(_record_search_terms(record))

    unique_additions = [term for term in dict.fromkeys(additions) if term and term not in query]
    if not unique_additions:
        return query
    return " ".join([query, *unique_additions])


def _default_alias_path(project_root: Optional[Path] = None) -> Path:
    return active_knowledge_base(project_root=project_root).alias_path


def _record_matches(query: str, record: Mapping[str, object]) -> bool:
    compact_query = _compact(query)
    for term in _record_match_terms(record):
        if _compact(term) and _compact(term) in compact_query:
            return True

    for trigger in record.get("triggers", []) or []:
        if not isinstance(trigger, Mapping):
            continue
        all_terms = [str(term) for term in trigger.get("all", []) if str(term).strip()]
        any_terms = [str(term) for term in trigger.get("any", []) if str(term).strip()]
        if all_terms and not all(_compact(term) in compact_query for term in all_terms):
            continue
        if any_terms and not any(_compact(term) in compact_query for term in any_terms):
            continue
        if all_terms or any_terms:
            return True

    return False


def _record_match_terms(record: Mapping[str, object]) -> List[str]:
    terms = [str(record.get("canonical", ""))]
    terms.extend(str(term) for term in record.get("aliases", []) or [])
    return [term for term in terms if term.strip()]


def _record_search_terms(record: Mapping[str, object]) -> List[str]:
    terms = _record_match_terms(record)
    terms.extend(str(term) for term in record.get("related_terms", []) or [])
    return [_normalize_term(term) for term in terms if _normalize_term(term)]


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text))


def _normalize_term(term: str) -> str:
    return " ".join(str(term).split()).strip()
