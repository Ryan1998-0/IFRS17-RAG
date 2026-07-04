import re
from typing import List

from rag_demo.chunking import Chunk


def build_answer_prompt(question: str, chunks: List[Chunk], context_summary: str = "") -> str:
    if context_summary:
        context_instruction = "請根據以下彙整資料回答。"
        context_block = f"""## 彙整資料
{context_summary}
"""
    else:
        context_instruction = "請根據以下檢索資料回答。"
        context_block = f"""## 檢索資料
{render_retrieved_context(chunks)}
"""

    return f"""你是一個本機 RAG 系統的回答模型。你的任務是根據 retrieval 結果回答使用者問題。

使用者問：
{question}

{context_instruction}

{context_block}

## 回答規則
請只能根據下列來源回答使用者問題。
請使用繁體中文回答。
不要使用簡體字。
若來源沒有明確提到，請回答「無法從來源確認」。
不要使用一般常識、模型內部知識或來源外資訊補答案；只能根據目前 knowledge base 來源回答。
不要把已經有來源支持的內容列入無法確認。
無法確認只限於使用者問題本身，不要延伸評論其他未被詢問的議題。
可以在答案後簡短列出依據來源；不需要固定輸出第 2 點或第 3 點。
不能把推測內容當成已確認答案。
動作發生不等於結果成功；如果來源只提到動作、操作、申請、嘗試或執行，沒有明確寫出成功、失敗、核准、命中或完成，就必須回答結果無法從來源確認。
不要加入結尾總結句。
來源依據若有列出，必須包含對應的來源編號與章節名稱。
回答前必須逐一檢視每個檢索來源；如果多個來源都直接回答問題，答案必須整合所有相關來源，不要只回答第一個來源。
若「彙整資料」已列出直接 evidence，請優先根據直接 evidence 回答。
若同時出現「程式抽取 evidence」與「Summary Agent 補充整理」，程式抽取 evidence 是最高優先；程式抽取 evidence 的優先級高於 Summary Agent 補充整理；不可因 Summary Agent 漏列而忽略程式抽取 evidence。
若使用者問題詢問名單、身份、欄位值或對照關係，必須逐一檢查並整合所有結構化 evidence，不可只列其中一部分。
若來源是「A / B」、key-value、表格列或列表格式，請保留原始標籤，不要改寫成更粗略的分類。
"""


def render_retrieved_context(chunks: List[Chunk]) -> str:
    if not chunks:
        return "沒有找到相關來源。"

    sources = []
    for index, chunk in enumerate(chunks, start=1):
        key_excerpts = render_key_excerpts(str(chunk["content"]))
        sources.append(
            "\n".join(
                [
                    f"[來源 {index}]",
                    f"文件：{chunk['source']}",
                    f"父層章節：{chunk.get('parent_title', '')}",
                    f"章節：{chunk['title']}",
                    "關鍵摘錄：",
                    key_excerpts,
                    "內容：",
                    str(chunk["content"]),
                ]
            )
        )

    return "\n\n".join(sources)


def render_key_excerpts(content: str, max_excerpts: int = 8) -> str:
    excerpts = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_key_excerpt_line(line):
            excerpts.append(line)
        if len(excerpts) >= max_excerpts:
            break
    if excerpts:
        return "\n".join(f"- {excerpt}" for excerpt in excerpts)
    return "無"


def _is_key_excerpt_line(line: str) -> bool:
    if len(line) > 140:
        return False
    if re.match(r"^[【\[][^】\]]+[】\]]$", line):
        return True
    if re.match(r"^[\-*]\s+\S+", line):
        return True
    if line.startswith("|") and line.endswith("|") and line.count("|") >= 2:
        return True
    if re.match(r"^[^：:]{1,30}[：:]\s*\S+", line):
        return True
    if re.match(r"^#{1,6}\s+\S+", line):
        return True
    return False
