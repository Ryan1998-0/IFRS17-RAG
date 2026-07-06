from typing import Callable, List

from rag_demo.chunking import Chunk
from rag_demo.model_providers import ask_model
from rag_demo.prompting import render_retrieved_context


QA_AGENT_SYSTEM_PROMPT = """你是一位專業的 RAG 問答 Agent。
請只根據使用者提供的檢索資料回答問題，直接提供精簡並準確的解答，避免與問題無關的內容。
如果檢索資料不足以支撐答案，請明確說明資料不足，不要憑空補充。
"""


def build_qa_prompt(
    original_question: str,
    refined_question: str,
    keywords: List[str],
    chunks: List[Chunk],
    extracted_evidence: str = "",
) -> str:
    return f"""### 問題
{refined_question}

### 檢索資料片段
{render_retrieved_context(chunks)}
"""


def answer_with_qa_agent(
    original_question: str,
    refined_question: str,
    keywords: List[str],
    chunks: List[Chunk],
    extracted_evidence: str = "",
    model: str = "qwen2.5:7b",
    ask_model_fn: Callable[..., str] = ask_model,
) -> str:
    return ask_model_fn(
        build_qa_prompt(
            original_question=original_question,
            refined_question=refined_question,
            keywords=keywords,
            chunks=chunks,
            extracted_evidence=extracted_evidence,
        ),
        model=model,
        system=QA_AGENT_SYSTEM_PROMPT,
    ).strip()
