import re
from typing import Optional

from rag_demo.evidence_policy import split_key_value


def answer_action_result(question: str, evidence_summary: str) -> Optional[str]:
    action = _requested_action_success(question)
    if not action:
        return None

    action_line = _find_action_line(evidence_summary, action)
    if not action_line:
        return None

    if _line_confirms_action_success(action_line, action):
        return f"來源可確認{_clean_evidence_text(action_line)}。"

    return (
        f"來源可確認{_clean_evidence_text(action_line)}。"
        f"但無法從來源確認{action}是否成功。"
    )


def _requested_action_success(question: str) -> str:
    if not any(term in question for term in ("是否成功", "有沒有成功", "能不能確認", "能否確認", "成功嗎")):
        return ""

    patterns = (
        r"([\u4e00-\u9fffA-Za-z_]{1,12})是否成功",
        r"([\u4e00-\u9fffA-Za-z_]{1,12})有沒有成功",
        r"確認([\u4e00-\u9fffA-Za-z_]{1,12})是否成功",
        r"([\u4e00-\u9fffA-Za-z_]{1,12})成功嗎",
    )
    for pattern in patterns:
        match = re.search(pattern, question)
        if match:
            return _clean_action(match.group(1))
    return ""


def _find_action_line(evidence_summary: str, action: str) -> str:
    for line in evidence_summary.splitlines():
        key, value = split_key_value(line)
        if key and (action in key or action in value):
            return line.strip()
    return ""


def _line_confirms_action_success(line: str, action: str) -> bool:
    key, value = split_key_value(line)
    if not key:
        return False
    combined = f"{key} {value}"
    return action in combined and any(term in combined for term in ("成功", "已完成", "完成", "命中", "核准", "通過"))


def _clean_evidence_text(line: str) -> str:
    stripped = line.strip()
    if stripped.startswith("- "):
        stripped = stripped[2:].strip()
    if "] " in stripped:
        stripped = stripped.split("] ", 1)[1].strip()
    return stripped


def _clean_action(action: str) -> str:
    cleaned = action
    for prefix in ("資料中能不能", "資料中能否", "能不能", "能否", "是否", "有沒有", "確認", "最後", "結果"):
        cleaned = cleaned.replace(prefix, "")
    return cleaned.strip()
