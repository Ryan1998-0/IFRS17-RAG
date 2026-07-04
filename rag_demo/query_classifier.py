import re


def classify_query(question: str):
    compact = _compact(question)
    relation_score = _score_terms(
        compact,
        (
            "屬於",
            "属于",
            "哪一派",
            "哪派",
            "哪些人",
            "成員",
            "成员",
            "關係",
            "关系",
            "組織",
            "组织",
            "派別",
            "派别",
            "誰是",
            "谁是",
        ),
    )
    hybrid_score = _score_terms(
        compact,
        (
            "為什麼",
            "为什么",
            "如何",
            "怎麼",
            "怎么",
            "導致",
            "导致",
            "建立",
            "阻止",
            "影響",
            "影响",
        ),
    )
    content_score = _score_terms(
        compact,
        (
            "是什麼",
            "是什么",
            "什麼是",
            "什么是",
            "定義",
            "定义",
            "意思",
            "解釋",
            "解释",
        ),
    )

    if hybrid_score and (relation_score or _has_named_entity_shape(question)):
        query_type = "hybrid"
    elif relation_score:
        query_type = "relation"
    else:
        query_type = "content"

    return {
        "type": query_type,
        "relation_score": relation_score,
        "hybrid_score": hybrid_score,
        "content_score": content_score,
    }


def _score_terms(compact_text: str, terms) -> int:
    return sum(1 for term in terms if _compact(term) in compact_text)


def _has_named_entity_shape(text: str) -> bool:
    return bool(re.search(r"[A-Za-z]{2,}|[\u4e00-\u9fff]{2,}", str(text)))


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()
