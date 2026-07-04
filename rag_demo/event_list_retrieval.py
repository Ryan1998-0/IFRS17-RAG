import re
from typing import List

from rag_demo.chunking import Chunk
from rag_demo.evidence_policy import (
    build_evidence_policy,
    is_outcome_detail_field,
    is_participant_field,
    is_result_field,
    sequence_number,
    split_key_value,
)
from rag_demo.retrieval_verifier import extract_evidence_candidates


def find_event_list_chunks(question: str, chunks: List[Chunk], max_results: int = 12) -> List[Chunk]:
    policy = build_evidence_policy(question)
    if not (policy.event_list and policy.event_or_result_question):
        return []

    outcome_terms = _requested_outcomes(question)
    if not outcome_terms:
        return []

    matches = []
    for chunk in chunks:
        evidence = extract_evidence_candidates(str(chunk.get("content", "")), max_candidates=40)
        if _chunk_matches_outcome(evidence, outcome_terms):
            result = dict(chunk)
            result.setdefault("score", 0.0)
            result["event_list_match"] = True
            result["event_sequence"] = sequence_number(f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}")
            matches.append(result)

    matches.sort(key=lambda chunk: (chunk.get("event_sequence", 10**9), str(chunk.get("title", ""))))
    return matches[:max_results]


def merge_event_list_chunks(event_results: List[Chunk], retrieval_results: List[Chunk]) -> List[Chunk]:
    merged = []
    seen = set()
    for chunk in list(event_results) + list(retrieval_results):
        chunk_id = chunk.get("id") or f"{chunk.get('source', '')}:{chunk.get('title', '')}"
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        merged.append(chunk)
    return merged


def find_result_constrained_chunks(question: str, chunks: List[Chunk], max_results: int = 12) -> List[Chunk]:
    policy = build_evidence_policy(question)
    if not policy.result_only:
        return []

    target_numbers = _target_numbers(question)
    matches = []
    for chunk in chunks:
        content = str(chunk.get("content", ""))
        evidence = extract_evidence_candidates(content, max_candidates=60)
        if not _chunk_has_result_evidence(evidence, _result_scope_terms(question)):
            continue
        if target_numbers and not _chunk_mentions_any_target(content, target_numbers):
            continue
        result = dict(chunk)
        result.setdefault("score", 0.0)
        result["result_constraint_match"] = True
        result["event_sequence"] = sequence_number(f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}")
        matches.append(result)

    matches.sort(key=lambda chunk: (chunk.get("event_sequence", 10**9), str(chunk.get("title", ""))))
    return matches[:max_results]


def _requested_outcomes(question: str):
    outcomes = []
    for term in ("失敗", "成功", "未通過", "通過", "異常", "錯誤", "完成"):
        if term in question:
            outcomes.append(term)
    return outcomes


def _chunk_matches_outcome(evidence_lines, outcome_terms):
    for line in evidence_lines:
        key, value = split_key_value(line)
        if not key or not _is_event_result_key(key):
            continue
        if any(outcome in value for outcome in outcome_terms):
            return True
    return False


def _is_event_result_key(key: str) -> bool:
    normalized = key.strip().lower()
    return normalized in {
        "結果",
        "狀態",
        "判定",
        "結論",
        "任務",
        "事件",
        "流程",
        "步驟",
        "階段",
        "案件",
        "處理狀態",
        "status",
        "result",
        "outcome",
        "task",
        "event",
        "process",
        "step",
        "case",
    }


def _chunk_has_result_evidence(evidence_lines, scope_terms=None) -> bool:
    for line in evidence_lines:
        key, value = split_key_value(line)
        if key and is_result_field(key, value) and _matches_scope(key, value, scope_terms or []):
            return True
    return False


def _target_numbers(question: str) -> List[int]:
    numbers = []
    for match in re.finditer(r"(?<!第)(\d+)\s*號", question):
        numbers.append(int(match.group(1)))
    for match in re.finditer(r"\b(?:player|agent|service|user|customer|client|device|account)\s*(\d+)\b", question, flags=re.IGNORECASE):
        numbers.append(int(match.group(1)))
    if not numbers and build_evidence_policy(question).result_only:
        for match in re.finditer(r"\b(\d+)\b", question):
            numbers.append(int(match.group(1)))
    return sorted(set(numbers))


def _chunk_mentions_any_target(content: str, target_numbers: List[int]) -> bool:
    evidence = extract_evidence_candidates(content, max_candidates=60)
    relevant_text = []
    for line in evidence:
        key, value = split_key_value(line)
        if key and (is_result_field(key, value) or is_participant_field(key) or is_outcome_detail_field(key, value)):
            relevant_text.append(line)
    haystack = "\n".join(relevant_text) if relevant_text else content
    return any(_mentions_numbered_entity(haystack, number) for number in target_numbers)


def _mentions_numbered_entity(text: str, number: int) -> bool:
    patterns = (
        rf"\b(?:[A-Za-z][A-Za-z0-9_-]*\s+){{1,3}}{number}\b",
        rf"\b{number}\s+(?:[A-Za-z][A-Za-z0-9_-]*)\b",
        rf"[\u4e00-\u9fffA-Za-z_]+\s*{number}\b",
        rf"{number}\s*號",
    )
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _result_scope_terms(question: str) -> List[str]:
    lowered = question.lower()
    scope_terms = []
    for match in re.finditer(r"([\u4e00-\u9fffA-Za-z_]{1,12})結果", question):
        scope = _clean_result_scope(match.group(1))
        if scope:
            scope_terms.append(scope)
    for match in re.finditer(r"\b([a-z][a-z_-]{1,30})\s+(?:result|outcome)\b", lowered):
        scope = _clean_result_scope(match.group(1))
        if scope:
            scope_terms.append(scope)
    return scope_terms


def _clean_result_scope(scope: str) -> str:
    cleaned = scope.strip()
    for prefix in ("如果只看", "只看", "只根據", "僅根據", "根據", "使用", "用", "only", "use", "based"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    if cleaned in {"結果", "事件", "資料", "result", "outcome", "only", "use", "based"}:
        return ""
    return cleaned


def _matches_scope(key: str, value: str, scope_terms: List[str]) -> bool:
    if not scope_terms:
        return True
    combined = f"{key}\n{value}".lower()
    return any(term.lower() in combined for term in scope_terms)
