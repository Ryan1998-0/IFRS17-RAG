import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EvidencePolicy:
    temporal_order: bool = False
    event_list: bool = False
    event_or_result_question: bool = False
    result_only: bool = False
    asks_participant: bool = False
    asks_outcome_detail: bool = False
    asks_vote: bool = False


def build_evidence_policy(question: str) -> EvidencePolicy:
    return EvidencePolicy(
        temporal_order=_has_any(question, ("第一個", "第一次", "最早", "最先", "首次", "first", "earliest")),
        event_list=_has_any(question, ("哪幾", "哪些", "所有", "列出", "全部", "幾次", "幾個", "which", "list all")),
        event_or_result_question=_has_any(
            question,
            (
                "結果",
                "狀態",
                "成功",
                "失敗",
                "通過",
                "未通過",
                "異常",
                "錯誤",
                "完成",
                "任務",
                "事件",
                "流程",
                "步驟",
                "階段",
                "案件",
                "處理",
                "決策",
                "作業",
                "task",
                "event",
                "case",
                "process",
                "step",
            ),
        ),
        result_only=_has_result_only_constraint(question),
        asks_participant=_has_any(
            question,
            (
                "誰",
                "哪位",
                "成員",
                "參與者",
                "負責",
                "執行",
                "隊伍",
                "人員",
                "處理者",
                "指派",
                "承辦",
                "player",
                "member",
                "owner",
                "assignee",
            ),
        ),
        asks_outcome_detail=_has_any(question, ("原因", "為什麼", "怎麼", "失敗", "成功", "異常", "錯誤", "責任", "明細", "細節", "detail", "reason")),
        asks_vote=_has_any(question, ("投票", "支持", "贊成", "反對", "同意", "不同意", "vote", "approve", "reject")),
    )


def sequence_number(metadata_text: str) -> int:
    patterns = (
        r"第\s*(\d+)\s*(輪|章|節|段|步|天|次|回合|階段)",
        r"\b(?:round|chapter|section|step|phase|day)\s*(\d+)\b",
        r"\b(\d+)\s*(?:round|chapter|section|step|phase|day)\b",
    )
    lowered = metadata_text.lower()
    for pattern in patterns:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return 10**9


def evidence_category(line: str, policy: EvidencePolicy) -> int:
    key, value = split_key_value(line)
    if key:
        if policy.event_or_result_question and is_result_field(key, value):
            return 0
        if policy.asks_participant and is_participant_field(key):
            return 1
        if policy.asks_outcome_detail and is_outcome_detail_field(key, value):
            return 2
        return 3

    stripped = line.strip()
    if re.match(r"^[【\[][^】\]]+\s+/\s+[^】\]]+[】\]]$", stripped):
        return 4 if policy.event_or_result_question else 0
    if re.match(r"^[【\[][^】\]]+[】\]]$", stripped):
        return 5 if policy.event_or_result_question else 1
    return 6


def should_include_evidence_line(line: str, policy: EvidencePolicy) -> bool:
    key, value = split_key_value(line)
    if policy.result_only:
        if not key:
            return False
        if is_vote_field(key) and not policy.asks_vote:
            return False
        return (
            is_result_field(key, value)
            or is_participant_field(key)
            or is_outcome_detail_field(key, value)
        )
    if key and is_vote_field(key) and not policy.asks_vote:
        return False
    return True


def has_answerable_event_evidence(question: str, evidence_summary: str) -> bool:
    policy = build_evidence_policy(question)
    if not policy.event_or_result_question:
        return False

    lines = list(_evidence_lines(evidence_summary))
    has_result = any(_line_has_result(line) for line in lines)
    has_participant = not policy.asks_participant or any(_line_has_participant(line) for line in lines)
    has_detail = not policy.asks_outcome_detail or any(_line_has_outcome_detail(line) for line in lines)
    return has_result and has_participant and has_detail


def answerable_event_spans(evidence_summary: str):
    spans = []
    for line in _evidence_lines(evidence_summary):
        key, value = split_key_value(line)
        if key and (
            is_result_field(key, value)
            or is_participant_field(key)
            or is_outcome_detail_field(key, value)
        ):
            spans.append(line.strip())
    return spans


def split_key_value(line: str):
    stripped = line.strip()
    if "] " in stripped:
        stripped = stripped.split("] ", 1)[1].strip()
    match = re.match(r"^([^：:]{1,24})[：:]\s*(\S.*)$", stripped)
    if not match:
        return "", ""
    return match.group(1).strip(), match.group(2).strip()


def is_result_field(key: str, value: str) -> bool:
    return _has_any(
        key,
        ("結果", "狀態", "判定", "結論", "任務", "事件", "流程", "步驟", "階段", "案件", "處理狀態", "result", "status", "outcome"),
    ) or _has_any(
        value,
        ("成功", "失敗", "通過", "未通過", "異常", "錯誤", "完成", "success", "successful", "failed", "failure", "completed", "complete", "error"),
    )


def is_participant_field(key: str) -> bool:
    return _has_any(
        key,
        (
            "人員",
            "成員",
            "參與",
            "負責",
            "執行",
            "對象",
            "隊伍",
            "出任務者",
            "處理者",
            "承辦",
            "指派",
            "owner",
            "assignee",
            "member",
        ),
    )


def is_outcome_detail_field(key: str, value: str) -> bool:
    return _has_any(
        key,
        ("原因", "明細", "細節", "錯誤", "異常", "失敗", "成功", "責任", "牌", "票", "紀錄", "備註", "detail", "reason", "failure", "error", "note"),
    ) or _has_any(value, ("失敗", "成功", "異常", "錯誤", "failed", "failure", "success", "error"))


def is_vote_field(key: str) -> bool:
    return _has_any(key, ("投票", "贊成", "反對", "支持", "同意", "不同意", "vote", "approve", "reject"))


def _line_has_result(line: str) -> bool:
    key, value = split_key_value(line)
    return bool(key and is_result_field(key, value))


def _line_has_participant(line: str) -> bool:
    key, _ = split_key_value(line)
    return bool(key and is_participant_field(key))


def _line_has_outcome_detail(line: str) -> bool:
    key, value = split_key_value(line)
    return bool(key and is_outcome_detail_field(key, value))


def _evidence_lines(evidence_summary: str) -> Iterable[str]:
    for line in evidence_summary.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            yield stripped


def _has_any(text: str, terms) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _has_result_only_constraint(question: str) -> bool:
    lowered = question.lower()
    has_only_constraint = _has_any(lowered, ("只看", "只根據", "僅根據", "只用", "only use", "based only on"))
    has_result_scope = _has_any(
        lowered,
        (
            "任務結果",
            "事件結果",
            "流程結果",
            "步驟結果",
            "階段結果",
            "處理結果",
            "執行結果",
            "案件結果",
            "作業結果",
            "決策結果",
            "測試結果",
            "result",
            "outcome",
        ),
    )
    return has_only_constraint and has_result_scope
