import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class EntityExistenceQuery:
    entity_type: str
    target_number: int
    target_label: str


def parse_entity_existence_query(question: str) -> Optional[EntityExistenceQuery]:
    if not _asks_existence(question):
        return None

    match = re.search(r"(\d+)\s*號\s*([\u4e00-\u9fffA-Za-z_]+)", question)
    if not match:
        match = re.search(r"\b(player|customer|client|device|account|user)\s*(\d+)\b", question, flags=re.IGNORECASE)
        if not match:
            return None
        entity_type = match.group(1).lower()
        target_number = int(match.group(2))
    else:
        target_number = int(match.group(1))
        entity_type = _clean_entity_type(match.group(2))
        if not _is_valid_entity_type(entity_type):
            return None

    target_label = f"{target_number}號{entity_type}"
    return EntityExistenceQuery(entity_type=entity_type, target_number=target_number, target_label=target_label)


def _clean_entity_type(entity_type: str) -> str:
    cleaned = re.split(r"(參與|存在|出現|嗎|呢|是否|有沒有)", entity_type, maxsplit=1)[0]
    return cleaned.strip()


def _is_valid_entity_type(entity_type: str) -> bool:
    if not entity_type:
        return False
    if entity_type in {"第", "輪", "章", "節", "步", "天", "次", "回合", "階段", "part"}:
        return False
    return True


def answer_entity_existence(question: str, evidence_summary: str) -> Optional[str]:
    query = parse_entity_existence_query(question)
    if query is None:
        return None

    observed_numbers = extract_entity_numbers(evidence_summary, query.entity_type)
    if not observed_numbers:
        return None

    observed_text = "、".join(str(number) for number in observed_numbers)
    if query.target_number in observed_numbers:
        return (
            f"可以確認有{query.target_label}參與。"
            f"來源中的{query.entity_type}編號包含：{observed_text}。"
        )

    return (
        f"無法從來源確認有{query.target_label}參與。"
        f"目前來源中的{query.entity_type}編號只有：{observed_text}。"
    )


def extract_entity_numbers(evidence_summary: str, entity_type: str) -> List[int]:
    numbers = []
    seen = set()
    for line in evidence_summary.splitlines():
        content = _strip_source_prefix(line.strip())
        for number in _numbers_from_entity_line(content, entity_type):
            if number not in seen:
                seen.add(number)
                numbers.append(number)
    return sorted(numbers)


def _numbers_from_entity_line(content: str, entity_type: str) -> List[int]:
    numbers = []
    bracket_match = re.match(r"^[【\[](.+)[】\]]$", content)
    if bracket_match:
        content = bracket_match.group(1)

    patterns = [
        rf"API\s*AI\s*(\d+)",
        rf"(\d+)\s*號\s*{re.escape(entity_type)}",
        rf"{re.escape(entity_type)}\s*(\d+)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content, flags=re.IGNORECASE):
            numbers.append(int(match.group(1)))
    return numbers


def _strip_source_prefix(line: str) -> str:
    if line.startswith("- "):
        line = line[2:].strip()
    if "] " in line:
        return line.split("] ", 1)[1].strip()
    return line


def _asks_existence(question: str) -> bool:
    return any(term in question for term in ("有", "存在", "參與", "出現", "是否", "嗎", "沒有"))
