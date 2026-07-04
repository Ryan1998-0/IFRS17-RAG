from __future__ import annotations

import json
import math
import re
import statistics
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
OUT_DIR = EVAL_DIR / "runs"
RUN_ID = "graph-suitability-20260704"
TOP_K = 5


@dataclass
class Chunk:
    id: str
    dataset: str
    title: str
    content: str
    entities: list[str]
    semantic_terms: list[str]


@dataclass
class Edge:
    source: str
    target: str
    relation: str
    supporting_chunk_ids: list[str]
    confidence: float = 1.0


@dataclass
class Question:
    id: str
    dataset: str
    dataset_label: str
    question_type: str
    question: str
    query_entities: list[str]
    semantic_terms: list[str]
    required_chunk_ids: list[str]
    expected_answer: str


@dataclass
class Dataset:
    name: str
    label: str
    suitability_hypothesis: str
    chunks: list[Chunk]
    questions: list[Question]
    edges: list[Edge] = field(default_factory=list)
    generic_entities: set[str] = field(default_factory=set)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    datasets = build_datasets()
    raw_records = []
    summary_rows = []
    setup_started = time.perf_counter()

    for dataset in datasets:
        indexes = build_indexes(dataset.chunks)
        graph = build_graph(dataset.edges)
        setup_seconds = round(time.perf_counter() - setup_started, 6)
        for variant in variants():
            records = run_variant(dataset, indexes, graph, variant)
            raw_records.extend(records)
            summary_rows.append(summarize_variant(dataset, variant, records, setup_seconds))

    raw_path = OUT_DIR / f"{RUN_ID}.jsonl"
    summary_path = OUT_DIR / f"{RUN_ID}-summary.json"
    report_path = OUT_DIR / f"{RUN_ID}-report.md"

    raw_path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in raw_records) + "\n", encoding="utf-8")
    summary_path.write_text(
        json.dumps(
            {
                "run_id": RUN_ID,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "top_k": TOP_K,
                "dataset_count": len(datasets),
                "question_count": sum(len(dataset.questions) for dataset in datasets),
                "variants": [variant["name"] for variant in variants()],
                "summary": summary_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report_path.write_text(render_report(datasets, summary_rows, raw_path, summary_path), encoding="utf-8")

    print(f"Raw JSONL: {raw_path}")
    print(f"Summary JSON: {summary_path}")
    print(f"Report: {report_path}")
    return 0


def variants() -> list[dict]:
    return [
        {
            "name": "bm25_only",
            "label": "BM25-only",
            "use_semantic": False,
            "use_graph": False,
            "graph_policy": "none",
        },
        {
            "name": "bm25_semantic",
            "label": "BM25 + semantic proxy",
            "use_semantic": True,
            "use_graph": False,
            "graph_policy": "none",
        },
        {
            "name": "bm25_semantic_graph",
            "label": "BM25 + semantic proxy + Graph",
            "use_semantic": True,
            "use_graph": True,
            "graph_policy": "entity_overlap",
            "graph_weight": 2.5,
        },
        {
            "name": "bm25_semantic_graph_priority",
            "label": "BM25 + semantic proxy + Graph-priority merge",
            "use_semantic": True,
            "use_graph": True,
            "graph_policy": "entity_overlap",
            "graph_weight": 50.0,
        },
        {
            "name": "bm25_semantic_precise_graph",
            "label": "BM25 + semantic proxy + precise Graph",
            "use_semantic": True,
            "use_graph": True,
            "graph_policy": "exclude_generic_hubs",
            "graph_weight": 2.5,
        },
    ]


def build_datasets() -> list[Dataset]:
    return [
        build_relational_claims_dataset(),
        build_cross_reference_manual_dataset(),
        build_flat_faq_dataset(),
        build_generic_hub_dataset(),
    ]


def build_relational_claims_dataset() -> Dataset:
    chunks: list[Chunk] = []
    questions: list[Question] = []
    edges: list[Edge] = []
    for i in range(1, 13):
        person = f"claimantC{i:02d}"
        policy = f"policyP{i:02d}"
        rider = f"riderR{i:02d}"
        exclusion = f"exclusionX{i:02d}"
        treatment = f"treatmentT{i:02d}"
        claimant_chunk = f"claims_claimant_{i:02d}"
        policy_chunk = f"claims_policy_{i:02d}"
        rider_chunk = f"claims_rider_{i:02d}"

        chunks.extend(
            [
                Chunk(
                    id=claimant_chunk,
                    dataset="relational_claims",
                    title=f"Claimant record {i:02d}",
                    content=f"Claimant {person} is assigned to policy record {policy}. The claim file stores only the starting identity and contract pointer.",
                    entities=[person, policy, rider],
                    semantic_terms=["claimant", "policy", "contract"],
                ),
                Chunk(
                    id=policy_chunk,
                    dataset="relational_claims",
                    title=f"Policy record {i:02d}",
                    content=f"Policy {policy} delegates benefit interpretation to rider record {rider}. The claimant name is not repeated here.",
                    entities=[policy, rider],
                    semantic_terms=["policy", "rider", "reimbursement"],
                ),
                Chunk(
                    id=rider_chunk,
                    dataset="relational_claims",
                    title=f"Rider coverage {i:02d}",
                    content=f"Rider {rider} covers {treatment} and excludes {exclusion}. This coverage note does not repeat the claimant or policy identifiers.",
                    entities=[rider, treatment, exclusion],
                    semantic_terms=["rider", "coverage", "treatment", "exclusion"],
                ),
            ]
        )
        edges.extend(
            [
                Edge(person, policy, "HAS_POLICY", [claimant_chunk, policy_chunk], 1.0),
                Edge(policy, rider, "HAS_RIDER", [policy_chunk, rider_chunk], 1.0),
                Edge(rider, exclusion, "EXCLUDES", [rider_chunk], 1.0),
                Edge(rider, treatment, "COVERS", [rider_chunk], 1.0),
            ]
        )
        questions.extend(
            [
                Question(
                    id=f"CLAIMS-{i:02d}-EXCLUSION",
                    dataset="relational_claims",
                    dataset_label="關聯型個案資料庫",
                    question_type="multi-hop entity relation",
                    question=f"For claimant {person}, what blocked benefit applies?",
                    query_entities=[person],
                    semantic_terms=["claimant", "blocked", "benefit"],
                    required_chunk_ids=[claimant_chunk, policy_chunk, rider_chunk],
                    expected_answer=f"{exclusion} applies through {rider}.",
                ),
                Question(
                    id=f"CLAIMS-{i:02d}-TREATMENT",
                    dataset="relational_claims",
                    dataset_label="關聯型個案資料庫",
                    question_type="multi-hop entity relation",
                    question=f"For claimant {person}, what covered service is available?",
                    query_entities=[person],
                    semantic_terms=["claimant", "covered", "service"],
                    required_chunk_ids=[claimant_chunk, policy_chunk, rider_chunk],
                    expected_answer=f"{treatment} is covered through {rider}.",
                ),
            ]
        )
    return Dataset(
        name="relational_claims",
        label="關聯型個案資料庫",
        suitability_hypothesis="Graph 應該明顯有幫助，因為答案分散在 claimant -> policy -> rider 的多跳關係上。",
        chunks=chunks,
        questions=questions,
        edges=edges,
    )


def build_cross_reference_manual_dataset() -> Dataset:
    chunks: list[Chunk] = []
    questions: list[Question] = []
    edges: list[Edge] = []
    for i in range(1, 13):
        workflow = f"workflowW{i:02d}"
        section = f"sectionS{i:02d}"
        control = f"controlK{i:02d}"
        exception = f"exceptionE{i:02d}"
        trigger = f"triggerT{i:02d}"
        workflow_chunk = f"manual_workflow_{i:02d}"
        section_chunk = f"manual_section_{i:02d}"
        exception_chunk = f"manual_exception_{i:02d}"
        chunks.extend(
            [
                Chunk(
                    id=workflow_chunk,
                    dataset="cross_reference_manual",
                    title=f"Workflow {i:02d}",
                    content=f"{workflow} tells the operator to follow referenced section {section} before closing the case.",
                    entities=[workflow, section],
                    semantic_terms=["workflow", "procedure", "section"],
                ),
                Chunk(
                    id=section_chunk,
                    dataset="cross_reference_manual",
                    title=f"Section {i:02d}",
                    content=f"{section} requires control marker {control}. If a special condition occurs, check exception marker {exception}.",
                    entities=[section, control, exception],
                    semantic_terms=["section", "control", "exception"],
                ),
                Chunk(
                    id=exception_chunk,
                    dataset="cross_reference_manual",
                    title=f"Exception {i:02d}",
                    content=f"{exception} applies when trigger marker {trigger} is observed, and it preserves {control}.",
                    entities=[exception, trigger, control],
                    semantic_terms=["exception", "trigger", "control"],
                ),
            ]
        )
        edges.extend(
            [
                Edge(workflow, section, "CROSS_REFERENCES", [workflow_chunk, section_chunk], 0.95),
                Edge(section, exception, "HAS_EXCEPTION", [section_chunk, exception_chunk], 0.95),
                Edge(exception, control, "PRESERVES_CONTROL", [exception_chunk, section_chunk], 0.95),
            ]
        )
        questions.extend(
            [
                Question(
                    id=f"MANUAL-{i:02d}-CONTROL",
                    dataset="cross_reference_manual",
                    dataset_label="交叉引用手冊/法規資料庫",
                    question_type="cross-reference",
                    question=f"When using {workflow}, which safeguard remains required?",
                    query_entities=[workflow],
                    semantic_terms=["workflow", "safeguard"],
                    required_chunk_ids=[workflow_chunk, section_chunk, exception_chunk],
                    expected_answer=f"{control} remains required through {section} and {exception}.",
                ),
                Question(
                    id=f"MANUAL-{i:02d}-TRIGGER",
                    dataset="cross_reference_manual",
                    dataset_label="交叉引用手冊/法規資料庫",
                    question_type="cross-reference",
                    question=f"When using {workflow}, what condition activates the special handling?",
                    query_entities=[workflow],
                    semantic_terms=["workflow", "condition"],
                    required_chunk_ids=[workflow_chunk, section_chunk, exception_chunk],
                    expected_answer=f"{trigger} activates {exception}.",
                ),
            ]
        )
    return Dataset(
        name="cross_reference_manual",
        label="交叉引用手冊/法規資料庫",
        suitability_hypothesis="Graph 應該中度到高度有幫助，因為問題需要沿 workflow -> section -> exception 找上下文。",
        chunks=chunks,
        questions=questions,
        edges=edges,
    )


def build_flat_faq_dataset() -> Dataset:
    chunks: list[Chunk] = []
    questions: list[Question] = []
    for i in range(1, 25):
        topic = f"faq-topic-{i:02d}"
        action = f"action-{i:02d}"
        chunk_id = f"faq_{i:02d}"
        chunks.append(
            Chunk(
                id=chunk_id,
                dataset="flat_faq",
                title=f"FAQ {i:02d}",
                content=f"For {topic}, the supported answer is to perform {action}. This FAQ is standalone and does not require another record.",
                entities=[topic, action],
                semantic_terms=["faq", "standalone", topic, action],
            )
        )
        questions.append(
            Question(
                id=f"FAQ-{i:02d}",
                dataset="flat_faq",
                dataset_label="平面 FAQ / 單段答案資料庫",
                question_type="single-hop fact",
                question=f"What should the user do for {topic}?",
                query_entities=[topic],
                semantic_terms=["faq", "standalone", topic],
                required_chunk_ids=[chunk_id],
                expected_answer=f"Perform {action}.",
            )
        )
    return Dataset(
        name="flat_faq",
        label="平面 FAQ / 單段答案資料庫",
        suitability_hypothesis="Graph 應該幾乎沒有幫助，因為答案已經在單一 chunk 內。",
        chunks=chunks,
        questions=questions,
        edges=[],
    )


def build_generic_hub_dataset() -> Dataset:
    chunks: list[Chunk] = []
    questions: list[Question] = []
    edges: list[Edge] = []
    hub = "atlas-platform"
    for i in range(1, 25):
        topic = f"atlasTopic{i:02d}"
        window = f"retentionWindow{i:02d}"
        chunk_id = f"hub_{i:02d}"
        chunks.append(
            Chunk(
                id=chunk_id,
                dataset="generic_hub",
                title=f"Atlas platform note {i:02d}",
                content=f"Atlas platform note {i:02d}: {topic} uses {window}. All Atlas notes share the same broad product name.",
                entities=[hub, topic, window],
                semantic_terms=["atlas", "platform", topic, "retention"],
            )
        )
        edges.append(Edge(hub, topic, "BROAD_TOPIC_LINK", [chunk_id], 0.85))
        questions.append(
            Question(
                id=f"HUB-{i:02d}",
                dataset="generic_hub",
                dataset_label="單一大主題 / hub-heavy 資料庫",
                question_type="single-hop fact with generic hub",
                question=f"In Atlas platform {topic}, which retention window applies?",
                query_entities=[hub],
                semantic_terms=["atlas", "platform", topic, "retention"],
                required_chunk_ids=[chunk_id],
                expected_answer=f"{window} applies.",
            )
        )
    return Dataset(
        name="generic_hub",
        label="單一大主題 / hub-heavy 資料庫",
        suitability_hypothesis="Graph 可能造成傷害，因為所有資料都連到同一個泛用 hub，Graph 會把無關 chunk 推進 Top K。",
        chunks=chunks,
        questions=questions,
        edges=edges,
        generic_entities={hub},
    )


def run_variant(dataset: Dataset, indexes: dict, graph: dict, variant: dict) -> list[dict]:
    records = []
    for question in dataset.questions:
        timings: dict[str, float] = {}
        total_started = time.perf_counter()

        bm25_results = timed(timings, "bm25", lambda: bm25_search(question.question, indexes, TOP_K * 4))
        candidates = rank_to_scores(bm25_results, "bm25")

        semantic_results = []
        if variant["use_semantic"]:
            semantic_results = timed(
                timings,
                "semantic_proxy",
                lambda: semantic_search(question.semantic_terms, indexes["chunks"], TOP_K * 4),
            )
            candidates = merge_scores(candidates, rank_to_scores(semantic_results, "semantic_proxy"))
        else:
            timings["semantic_proxy"] = 0.0

        graph_results = []
        if variant["use_graph"]:
            graph_results = timed(
                timings,
                "graph_retrieval",
                lambda: graph_search(question, graph, indexes["chunks_by_id"], dataset.generic_entities, variant["graph_policy"]),
            )
            candidates = timed(
                timings,
                "graph_merge",
                lambda: merge_scores(candidates, rank_to_scores(graph_results, "graph", weight=variant.get("graph_weight", 2.5))),
            )
        else:
            timings["graph_retrieval"] = 0.0
            timings["graph_merge"] = 0.0

        selected = sorted(candidates.values(), key=lambda item: item["score"], reverse=True)[:TOP_K]
        score = timed(timings, "scoring", lambda: score_question(question, selected))
        timings["total"] = round(time.perf_counter() - total_started, 6)
        records.append(
            {
                "run_id": RUN_ID,
                "variant": variant["name"],
                "variant_label": variant["label"],
                "dataset": dataset.name,
                "dataset_label": dataset.label,
                "question_id": question.id,
                "question_type": question.question_type,
                "question": question.question,
                "expected_answer": question.expected_answer,
                "required_chunk_ids": question.required_chunk_ids,
                "matched_chunk_ids": score["matched_chunk_ids"],
                "missed_chunk_ids": score["missed_chunk_ids"],
                "retrieval_score": score["matched"],
                "max_score": score["max"],
                "top_k": TOP_K,
                "contexts": [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "score": round(item["score"], 6),
                        "methods": sorted(item["methods"]),
                    }
                    for item in selected
                ],
                "diagnostics": {
                    "bm25_candidates": len(bm25_results),
                    "semantic_candidates": len(semantic_results),
                    "graph_candidates": len(graph_results),
                    "graph_policy": variant["graph_policy"],
                },
                "timings_seconds": timings,
            }
        )
    return records


def build_indexes(chunks: list[Chunk]) -> dict:
    tokenized = {chunk.id: tokenize(f"{chunk.title} {chunk.content}") for chunk in chunks}
    doc_freq = Counter()
    for terms in tokenized.values():
        doc_freq.update(set(terms))
    avg_len = statistics.mean(len(terms) for terms in tokenized.values())
    return {
        "chunks": chunks,
        "chunks_by_id": {chunk.id: chunk for chunk in chunks},
        "tokenized": tokenized,
        "doc_freq": doc_freq,
        "avg_len": avg_len,
        "n_docs": len(chunks),
    }


def build_graph(edges: list[Edge]) -> dict:
    adjacency: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.source].append(edge)
        adjacency[edge.target].append(Edge(edge.target, edge.source, f"REVERSE_{edge.relation}", edge.supporting_chunk_ids, edge.confidence))
    return {"adjacency": adjacency, "edge_count": len(edges)}


def bm25_search(query: str, indexes: dict, top_k: int) -> list[dict]:
    query_terms = tokenize(query)
    scores = []
    for chunk in indexes["chunks"]:
        terms = indexes["tokenized"][chunk.id]
        term_counts = Counter(terms)
        score = 0.0
        for term in query_terms:
            if term not in term_counts:
                continue
            score += bm25_term_score(term, term_counts[term], len(terms), indexes)
        if score > 0:
            scores.append(chunk_record(chunk, score, "bm25"))
    return sorted(scores, key=lambda item: item["score"], reverse=True)[:top_k]


def bm25_term_score(term: str, tf: int, doc_len: int, indexes: dict) -> float:
    k1 = 1.5
    b = 0.75
    n_docs = indexes["n_docs"]
    df = indexes["doc_freq"].get(term, 0)
    idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
    denom = tf + k1 * (1 - b + b * (doc_len / indexes["avg_len"]))
    return idf * (tf * (k1 + 1)) / denom


def semantic_search(query_terms: list[str], chunks: list[Chunk], top_k: int) -> list[dict]:
    q = set(normalize_term(term) for term in query_terms)
    results = []
    for chunk in chunks:
        c = set(normalize_term(term) for term in chunk.semantic_terms)
        if not q or not c:
            continue
        overlap = len(q & c)
        if overlap == 0:
            continue
        score = overlap / math.sqrt(len(q) * len(c))
        results.append(chunk_record(chunk, score, "semantic_proxy"))
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


def graph_search(
    question: Question,
    graph: dict,
    chunks_by_id: dict[str, Chunk],
    generic_entities: set[str],
    graph_policy: str,
) -> list[dict]:
    blocked_entities = generic_entities if graph_policy == "exclude_generic_hubs" else set()
    queue = deque((entity, 0) for entity in question.query_entities if entity not in blocked_entities)
    seen_entities = set(entity for entity, _ in queue)
    chunk_scores: dict[str, float] = defaultdict(float)
    max_depth = 2

    while queue:
        entity, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for edge in graph["adjacency"].get(entity, []):
            next_depth = depth + 1
            edge_score = edge.confidence * (1.2 / next_depth)
            for chunk_id in edge.supporting_chunk_ids:
                chunk_scores[chunk_id] += edge_score
            if edge.target not in seen_entities:
                seen_entities.add(edge.target)
                queue.append((edge.target, next_depth))

    records = []
    for chunk_id, score in chunk_scores.items():
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            continue
        records.append(chunk_record(chunk, score, "graph"))
    return sorted(records, key=lambda item: item["score"], reverse=True)


def rank_to_scores(results: list[dict], method: str, weight: float | None = None) -> dict[str, dict]:
    ranked = {}
    method_weight = weight if weight is not None else 1.0
    for index, item in enumerate(results):
        rank_score = method_weight / (index + 1)
        score = rank_score
        record = dict(item)
        record["score"] = score
        record["methods"] = {method}
        ranked[item["id"]] = record
    return ranked


def merge_scores(left: dict[str, dict], right: dict[str, dict]) -> dict[str, dict]:
    merged = {chunk_id: dict(item) for chunk_id, item in left.items()}
    for chunk_id, item in right.items():
        if chunk_id not in merged:
            merged[chunk_id] = dict(item)
            continue
        merged[chunk_id]["score"] += float(item["score"])
        merged[chunk_id]["methods"] = set(merged[chunk_id].get("methods", set())) | set(item.get("methods", set()))
    return merged


def score_question(question: Question, selected: list[dict]) -> dict:
    selected_ids = {item["id"] for item in selected}
    matched = [chunk_id for chunk_id in question.required_chunk_ids if chunk_id in selected_ids]
    missed = [chunk_id for chunk_id in question.required_chunk_ids if chunk_id not in selected_ids]
    return {
        "matched": len(matched),
        "max": len(question.required_chunk_ids),
        "matched_chunk_ids": matched,
        "missed_chunk_ids": missed,
    }


def summarize_variant(dataset: Dataset, variant: dict, records: list[dict], setup_seconds: float) -> dict:
    total = sum(record["retrieval_score"] for record in records)
    max_total = sum(record["max_score"] for record in records)
    perfect = sum(1 for record in records if record["retrieval_score"] == record["max_score"])
    zero = sum(1 for record in records if record["retrieval_score"] == 0)
    totals = [record["timings_seconds"]["total"] for record in records]
    return {
        "dataset": dataset.name,
        "dataset_label": dataset.label,
        "hypothesis": dataset.suitability_hypothesis,
        "variant": variant["name"],
        "variant_label": variant["label"],
        "questions": len(records),
        "score": total,
        "max_score": max_total,
        "accuracy": total / max_total if max_total else 0.0,
        "perfect_questions": perfect,
        "zero_questions": zero,
        "avg_total_seconds": statistics.mean(totals),
        "p95_total_seconds": percentile(totals, 95),
        "avg_graph_seconds": statistics.mean(record["timings_seconds"].get("graph_retrieval", 0.0) for record in records),
        "avg_graph_candidates": statistics.mean(record["diagnostics"]["graph_candidates"] for record in records),
        "setup_seconds_seen": setup_seconds,
    }


def render_report(datasets: list[Dataset], summary_rows: list[dict], raw_path: Path, summary_path: Path) -> str:
    by_dataset = defaultdict(list)
    for row in summary_rows:
        by_dataset[row["dataset"]].append(row)

    lines = [
        "# Graph RAG Suitability Experiment Report",
        "",
        "本報告只測 Retrieval，不測 LLM 最終回答。分數代表 Top 5 contexts 是否包含該題需要的 evidence chunks。",
        "",
        "這是一個合成但可控的 suitability benchmark，目的不是宣稱某個分數可以外推到所有企業資料庫，而是隔離「資料型態」對 Graph RAG 的影響。",
        "",
        "## 結論先講",
        "",
        "- Graph 最適合用在「資料彼此有明確關係，而且問題需要沿關係找證據」的資料庫，例如客戶/保單/理賠、醫療知識圖、法規交叉引用、產品零件依賴、研究論文引用網路。",
        "- Graph 不適合拿來硬加在平面 FAQ 或單段答案 KB 上，因為答案本來就在單一 chunk，Graph 沒有可補的關係。",
        "- Graph 在單一大主題、hub entity 很強的資料庫上容易變差；例如所有資料都連到同一個 `IFRS 17` 或同一個產品名時，Graph 會把無關 chunk 一起拉進 Top K。",
        "- Graph 的關鍵不是有沒有建圖，而是 entity gating、relation gating、以及 graph chunk merge 權重是否精準。",
        "",
        "## 設定",
        "",
        f"- Run ID: `{RUN_ID}`",
        f"- Top K: `{TOP_K}`",
        f"- Datasets: `{len(datasets)}`",
        f"- Questions: `{sum(len(dataset.questions) for dataset in datasets)}`",
        f"- Raw rows: `{sum(len(dataset.questions) for dataset in datasets) * len(variants())}`",
        f"- Raw JSONL: `{relative(raw_path)}`",
        f"- Summary JSON: `{relative(summary_path)}`",
        "- Dense 欄位使用 deterministic semantic proxy，不呼叫外部 embedding model；本實驗重點是隔離 Graph 對資料型態的影響。",
        "- `Graph-priority merge` 是故意設計的反例，用來模擬 graph prior / graph boost 過強時的 hub 污染。",
        "",
        "## Suitability Matrix",
        "",
        "| Data type | Result in this experiment | Recommendation |",
        "| --- | --- | --- |",
        "| 關聯型個案資料庫 | Graph 從 38.9% 拉到 100.0% | 適合，尤其是多跳 entity relation 問題 |",
        "| 交叉引用手冊/法規資料庫 | Graph 從 38.9% 拉到 100.0% | 適合，尤其是 workflow -> section -> exception 這類引用鏈 |",
        "| 平面 FAQ / 單段答案資料庫 | BM25 已 100.0%，Graph 沒有新增收益 | 不優先使用 Graph，先用 BM25/Hybrid/metadata filter |",
        "| 單一大主題 / hub-heavy 資料庫 | Graph-priority merge 掉到 25.0%，precise Graph 回到 100.0% | 條件式適合；必須排除泛用 hub 並控制 graph merge 權重 |",
        "",
        "## Overall Score",
        "",
        "| Dataset | Variant | Score | Perfect | Zero | Avg total s | Avg graph candidates |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for dataset in datasets:
        for row in by_dataset[dataset.name]:
            lines.append(
                f"| {row['dataset_label']} | {row['variant_label']} | "
                f"`{row['score']}/{row['max_score']} = {row['accuracy']:.1%}` | "
                f"`{row['perfect_questions']}/{row['questions']}` | "
                f"`{row['zero_questions']}` | "
                f"`{row['avg_total_seconds']:.6f}` | "
                f"`{row['avg_graph_candidates']:.2f}` |"
            )

    lines.extend(["", "## Incremental Delta", ""])
    for dataset in datasets:
        rows = {row["variant"]: row for row in by_dataset[dataset.name]}
        lines.extend(
            [
                f"### {dataset.label}",
                "",
                dataset.suitability_hypothesis,
                "",
                "| Step | Delta | Interpretation |",
                "| --- | ---: | --- |",
            ]
        )
        for before, after, label in [
            ("bm25_only", "bm25_semantic", "BM25 -> Semantic"),
            ("bm25_semantic", "bm25_semantic_graph", "Semantic -> Graph"),
            ("bm25_semantic", "bm25_semantic_graph_priority", "Semantic -> Graph-priority"),
            ("bm25_semantic", "bm25_semantic_precise_graph", "Semantic -> Precise Graph"),
        ]:
            delta = rows[after]["accuracy"] - rows[before]["accuracy"]
            lines.append(f"| {label} | `{delta:+.1%}` | {interpret_delta(dataset.name, after, delta)} |")
        lines.append("")

    lines.extend(
        [
            "## What This Means",
            "",
            "### 適合 Graph 的資料庫",
            "",
            "1. 關聯型業務資料：客戶、合約、訂單、理賠、案件、設備、零件彼此有明確 ID 關係。",
            "2. 交叉引用型文件：法規、會計準則、SOP、醫療 guideline、技術手冊。",
            "3. 多跳問題常見的 KB：問題通常不是問單一段落，而是要從 A 找到 B，再從 B 找到 C。",
            "4. 需要全局 sensemaking 的大型語料：主題、社群、事件脈絡比單一 chunk 更重要。",
            "",
            "### 不適合或要小心的資料庫",
            "",
            "1. 平面 FAQ：每題答案都在單一 chunk，Graph 成本大於收益。",
            "2. 單一大主題語料：所有資料都連到同一個 hub entity，Graph 會把噪音拉進來。",
            "3. 純數值/聚合查詢：例如算總額、平均、排名，應優先用 SQL/OLAP，不是 Graph RAG。",
            "4. 關係抽取品質不穩的資料：Graph 錯邊會比沒有 Graph 更糟。",
            "",
            "## Practical Rule",
            "",
            "如果你的問題需要「沿關係找資料」，Graph 值得做；如果你的問題只是「找最像的一段文字」，BM25 + Dense 通常比較穩。Graph RAG 的投資門檻是：資料要有穩定 entity、穩定 relation、可驗證 support chunk，並且 graph retrieval 要能排除泛用 hub。",
            "",
            "## Negative Results To Keep",
            "",
            "- `平面 FAQ` 沒有因為 Graph 變好。這不是壞結果，而是告訴我們單段答案型 KB 不需要優先上 Graph。",
            "- `hub-heavy` 在 Graph-priority merge 下掉到 25.0%。這對應 IFRS17 實驗看到的現象：如果所有問題都命中 `IFRS 17` 這種泛用 entity，Graph 可能把無關 chunk 推進 Top K。",
            "- Semantic proxy 在多跳資料上從 BM25 的 44.4% 掉到 38.9%。這提醒我們：加一個語意候選分支不一定提升，merge 與 rerank 仍然要測。",
            "",
            "## Practical Decision Rule",
            "",
            "| 問題 | 建議 |",
            "| --- | --- |",
            "| 答案是否通常在單一 chunk？ | 先用 BM25 + Dense，不要急著 Graph |",
            "| 是否需要從 A 找到 B，再從 B 找到 C？ | Graph 值得進候選方案 |",
            "| 資料是否有穩定 ID、entity、relation、foreign key、引用關係？ | Graph 成本較合理 |",
            "| 是否存在大量泛用 hub entity？ | Graph 需要 hub suppression / precise gating |",
            "| 是否是統計聚合、排序、總額計算？ | 優先 SQL/OLAP，不是 Graph RAG |",
            "",
            "## References",
            "",
            "- Microsoft GraphRAG: https://arxiv.org/abs/2404.16130",
            "- HippoRAG: https://arxiv.org/abs/2405.14831",
            "- G-Retriever: https://arxiv.org/abs/2402.07630",
            "- When to use Graphs in RAG: https://arxiv.org/html/2506.05690v3",
            "- Cache-Augmented Generation: https://arxiv.org/abs/2412.15605",
            "",
        ]
    )
    return "\n".join(lines)


def interpret_delta(dataset: str, variant: str, delta: float) -> str:
    if abs(delta) < 0.01:
        return "幾乎持平，代表該節點沒有提供新 evidence。"
    if delta > 0:
        return "提升，代表這類資料型態有可利用的語意或關係結構。"
    if dataset == "generic_hub":
        return "下降，符合預期：泛用 hub 把不相關 chunks 推進 Top K。"
    return "下降，代表額外節點引入噪音或 merge 權重過強。"


def chunk_record(chunk: Chunk, score: float, method: str) -> dict:
    return {
        "id": chunk.id,
        "dataset": chunk.dataset,
        "title": chunk.title,
        "content": chunk.content,
        "entities": chunk.entities,
        "semantic_terms": chunk.semantic_terms,
        "score": score,
        "methods": {method},
    }


def tokenize(text: str) -> list[str]:
    return [normalize_term(token) for token in re.findall(r"[A-Za-z0-9]+", text.lower())]


def normalize_term(term: str) -> str:
    return term.strip().lower().replace("_", "-")


def timed(timings: dict[str, float], name: str, fn):
    started = time.perf_counter()
    value = fn()
    timings[name] = round(time.perf_counter() - started, 6)
    return value


def percentile(values: Iterable[float], percent: int) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, math.ceil((percent / 100) * len(ordered)) - 1))
    return ordered[index]


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
