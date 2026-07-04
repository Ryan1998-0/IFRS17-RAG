import re

from rag_demo.model_providers import ask_model


QUERY_REWRITER_SYSTEM_PROMPT = """你是 RAG 系統的檢索查詢改寫器。

你的任務不是回答問題，而是把使用者原始問題改寫成更適合 embedding / hybrid search 的檢索文字。

請遵守：
- 使用繁體中文。
- 先做一次語意理解，step by step 判斷使用者真正想查的主題。
- 再重新生成一份「向量檢索用查詢」。
- 向量檢索用查詢要比使用者自己的問題更容易找到正確答案。
- 可以加入同義詞、上位概念、制度名稱、章節可能出現的關鍵詞。
- 不要編造文件中不存在的答案。
- 不要直接回答使用者問題。
"""


def build_rewrite_prompt(question: str, section_titles=None) -> str:
    section_titles = section_titles or []
    candidate_section_text = "\n".join(f"- {title}" for title in section_titles)
    if not candidate_section_text:
        candidate_section_text = "- 未提供候選章節"

    return f"""請將下列使用者問題改寫成適合 RAG 檢索與 embedding search 的查詢文字。

要求：
1. 先做一次語意理解，step by step 寫出使用者想查的主題。
2. 再輸出一行「向量檢索用查詢」。
3. 向量檢索用查詢應包含更明確的主題名稱、同義詞與可能出現在 knowledge base 中的章節詞。
4. 不要回答制度內容，只產生檢索用文字。
5. 優先使用候選章節中的詞彙。
6. 不要加入候選章節之外的制度名詞，除非使用者原問題明確提到。
7. 如果問題是廣義分類、總覽或「有哪些」類型，請從候選章節中挑出多個可能相關的章節名稱放進向量檢索用查詢。

輸出格式：
語意理解：...
向量檢索用查詢：...

候選章節：
{candidate_section_text}

使用者問題：
{question}
"""


def rewrite_query_for_retrieval(
    question: str,
    model: str = "qwen2.5:7b",
    section_titles=None,
) -> str:
    output = ask_model(
        build_rewrite_prompt(question, section_titles=section_titles),
        model=model,
        system=QUERY_REWRITER_SYSTEM_PROMPT,
    )
    retrieval_query = extract_retrieval_query(output) or question
    return sanitize_retrieval_query(question, retrieval_query, section_titles or [])


def extract_retrieval_query(output: str) -> str:
    marker = "向量檢索用查詢："
    for line in output.splitlines():
        if marker in line:
            return line.split(marker, 1)[1].strip()
    return output.strip().splitlines()[-1].strip() if output.strip() else ""


def sanitize_retrieval_query(
    original_question: str,
    retrieval_query: str,
    section_titles,
) -> str:
    allowed_terms = set(_split_terms(original_question))
    section_terms = []
    for title in section_titles:
        section_terms.extend(_split_terms(str(title)))
        compact_title = "".join(_split_terms(str(title)))
        if compact_title:
            section_terms.append(compact_title)

    kept = []
    for term in _split_terms(retrieval_query):
        if term in allowed_terms or any(term in section_term or section_term in term for section_term in section_terms):
            kept.append(term)

    sanitized = " ".join(dict.fromkeys(kept))
    if sanitized and _has_core_overlap(original_question, sanitized):
        return sanitized
    return original_question


def _split_terms(text: str):
    normalized = (
        text.replace(",", " ")
        .replace("，", " ")
        .replace("、", " ")
        .replace("？", " ")
        .replace("?", " ")
        .replace("：", " ")
        .replace(":", " ")
    )
    return [term.strip() for term in normalized.split() if term.strip()]


def _has_core_overlap(original_question: str, retrieval_query: str) -> bool:
    question_terms = _core_terms(original_question)
    compact_query = re.sub(r"\s+", "", retrieval_query)
    return any(term in compact_query for term in question_terms)


def _core_terms(text: str):
    compact = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", text)
    stopwords = {"公司", "規定", "相關", "哪些", "什麼", "怎麼樣", "有沒有"}
    terms = set()
    for length in (4, 3, 2):
        for i in range(max(0, len(compact) - length + 1)):
            term = compact[i : i + length]
            if term not in stopwords:
                terms.add(term)
    return terms
