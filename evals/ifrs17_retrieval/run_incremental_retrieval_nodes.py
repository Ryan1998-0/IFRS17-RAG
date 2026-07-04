from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("RAG_PROFILE", "ifrs17")

from rag_demo.chunking import load_knowledge_base_chunks
from rag_demo.embeddings import load_embedding_matrix
from rag_demo.event_list_retrieval import find_result_constrained_chunks, merge_event_list_chunks
from rag_demo.graph_entities import extract_query_entities
from rag_demo.graph_retrieval import (
    _graph_entity_records,
    _matched_graph_entity_ids,
    _rank_graph_relations,
)
from rag_demo.graph_store import load_graph
from rag_demo.index_store import load_index
from rag_demo.knowledge_base import active_knowledge_base
from rag_demo.query import (
    PROJECT_ROOT,
    _apply_definition_route_boost,
    _bm25_dense_retrieval_query,
    _definition_route_query,
    _definition_search_results,
    _dense_search_results,
    _effective_rrf_retrieval_query,
    _expand_parent_chunks,
    _merge_graph_and_vector_candidates,
    _metadata_filter_chunk_embedding_pairs,
    _rerank_rrf_candidates,
    _rrf_merge_ranked_results,
)
from rag_demo.query_classifier import classify_query
from rag_demo.retrieval import keyword_search
from rag_demo.vector_store import QdrantVectorStore


EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTION_FILE = EVAL_DIR / "questions_ifrs17_mixed100_v0.1.json"
DEFAULT_GRAPH_FILE = ROOT / "profiles/ifrs17/graph/graph.json"
OUTPUT_DIR = EVAL_DIR / "runs"
COLLECTION_NAME = "ifrs17_incremental_retrieval"


def main(argv=None) -> int:
    args = parse_args(argv)
    output_dir = resolve_path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = output_dir / f"incremental_retrieval_raw_{run_id}.jsonl"
    report_path = output_dir / f"incremental_retrieval_report_{run_id}.md"
    graph_validation_path = output_dir / f"incremental_graph_validation_{run_id}.json"
    setup_timings = {}

    question_file = resolve_path(args.question_file)
    graph_file = resolve_path(args.graph_file)

    questions = timed(setup_timings, "load_questions", lambda: load_questions(question_file, limit=args.limit))
    knowledge_base = active_knowledge_base(project_root=ROOT)
    chunks = timed(setup_timings, "load_index", lambda: load_chunks(knowledge_base))
    embeddings = timed(
        setup_timings,
        "load_embeddings",
        lambda: load_embedding_matrix(knowledge_base.index_dir / "embeddings.npy"),
    )
    vector_store = timed(
        setup_timings,
        "build_in_memory_qdrant",
        lambda: QdrantVectorStore.in_memory(
            chunks,
            embeddings,
            collection_name=f"{COLLECTION_NAME}_{run_id.replace('-', '_')}",
        ),
    )

    selected_graph_path = graph_file
    selected_graph = timed(setup_timings, "load_selected_graph", lambda: load_graph(path=selected_graph_path))
    active_graph_path = knowledge_base.graph_path
    active_graph = timed(setup_timings, "load_active_graph", lambda: load_graph(path=active_graph_path))
    graph_validation = timed(
        setup_timings,
        "validate_graph",
        lambda: validate_graph(
            active_graph_path=active_graph_path,
            active_graph=active_graph,
            selected_graph_path=selected_graph_path,
            selected_graph=selected_graph,
            chunks=chunks,
            question_file=question_file,
        ),
    )
    graph_validation["setup_timings_seconds"] = setup_timings
    graph_validation_path.write_text(
        json.dumps(graph_validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    variants = build_variants()
    if args.variants:
        wanted = {item.strip() for item in args.variants.split(",") if item.strip()}
        variants = [variant for variant in variants if variant["name"] in wanted]

    records = []
    started = time.perf_counter()
    with raw_path.open("w", encoding="utf-8") as raw_file:
        for variant in variants:
            for index, item in enumerate(questions, start=1):
                record_started = time.perf_counter()
                results, timings, diagnostics = variant["runner"](
                    question=item["question"],
                    chunks=chunks,
                    embeddings=embeddings,
                    vector_store=vector_store,
                    graph=selected_graph,
                    candidate_k=args.candidate_k,
                    final_context_k=args.final_context_k,
                    graph_policy=args.graph_policy,
                )
                scoring = timed(timings, "scoring", lambda: score_retrieved_context(results, item))
                timings["total"] = round(time.perf_counter() - record_started, 6)
                record = {
                    "run_id": run_id,
                    "variant": variant["name"],
                    "variant_label": variant["label"],
                    "question_file": relative_path(question_file),
                    "question_sha256": hash_file(question_file),
                    "selected_graph_file": relative_path(selected_graph_path),
                    "selected_graph_sha256": hash_file(selected_graph_path),
                    **{
                        key: item.get(key, "")
                        for key in (
                            "id",
                            "fact_id",
                            "book",
                            "answer_style",
                            "prompt_style",
                            "length_style",
                            "phrasing",
                            "user_level",
                        )
                    },
                    "question": item["question"],
                    "standard_answer": item.get("standard_answer", ""),
                    "retrieval_upper_bound_score": scoring["score"],
                    "max_score": scoring["max_score"],
                    "matched": scoring["matched"],
                    "missed": scoring["missed"],
                    "contexts": [context_record(chunk) for chunk in results],
                    "diagnostics": diagnostics,
                    "timings_seconds": timings,
                }
                records.append(record)
                raw_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                raw_file.flush()
                print(
                    f"{variant['name']} {index}/{len(questions)} {record['id']} "
                    f"retrieval={record['retrieval_upper_bound_score']}/{record['max_score']} "
                    f"total={timings['total']:.3f}s graph_hits={diagnostics.get('graph_results', 0)}",
                    flush=True,
                )

    write_report(
        report_path=report_path,
        raw_path=raw_path,
        graph_validation_path=graph_validation_path,
        questions_path=question_file,
        graph_validation=graph_validation,
        records=records,
        elapsed_seconds=round(time.perf_counter() - started, 3),
        candidate_k=args.candidate_k,
        final_context_k=args.final_context_k,
        setup_timings=setup_timings,
        benchmark_name=args.benchmark_name,
        graph_policy=args.graph_policy,
    )
    print(f"Raw JSONL: {raw_path}")
    print(f"Graph validation: {graph_validation_path}")
    print(f"Report: {report_path}")
    return 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run Three Body Mixed200 incremental retrieval-only eval.")
    parser.add_argument("--question-file", type=Path, default=DEFAULT_QUESTION_FILE)
    parser.add_argument("--graph-file", type=Path, default=DEFAULT_GRAPH_FILE)
    parser.add_argument("--candidate-k", type=int, default=50)
    parser.add_argument("--final-context-k", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--variants", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--benchmark-name", default="三體 Mixed200")
    parser.add_argument("--graph-policy", choices=("classified", "entity_overlap"), default="classified")
    return parser.parse_args(argv)


def build_variants():
    return [
        {
            "name": "bm25_only",
            "label": "BM25-only",
            "runner": run_bm25_only,
        },
        {
            "name": "bm25_dense",
            "label": "BM25 + Dense",
            "runner": run_bm25_dense,
        },
        {
            "name": "bm25_dense_graph",
            "label": "BM25 + Dense + Graph",
            "runner": run_bm25_dense_graph,
        },
        {
            "name": "full_project_stack",
            "label": "Full project stack",
            "runner": run_full_project_stack,
        },
    ]


def run_bm25_only(
    question: str,
    chunks,
    embeddings,
    vector_store,
    graph,
    candidate_k: int,
    final_context_k: int,
    graph_policy: str,
):
    timings = {}
    diagnostics = {}
    results = timed(timings, "bm25", lambda: keyword_search(question, chunks, top_k=final_context_k))
    diagnostics["candidate_count"] = len(results)
    diagnostics["graph_results"] = 0
    return results, timings, diagnostics


def run_bm25_dense(
    question: str,
    chunks,
    embeddings,
    vector_store,
    graph,
    candidate_k: int,
    final_context_k: int,
    graph_policy: str,
):
    timings = {}
    diagnostics = {}
    merged, parts = bm25_dense_candidates(
        question=question,
        chunks=chunks,
        embeddings=embeddings,
        vector_store=vector_store,
        candidate_k=candidate_k,
        timings=timings,
    )
    diagnostics.update(parts)
    diagnostics["graph_results"] = 0
    return merged[:final_context_k], timings, diagnostics


def run_bm25_dense_graph(
    question: str,
    chunks,
    embeddings,
    vector_store,
    graph,
    candidate_k: int,
    final_context_k: int,
    graph_policy: str,
):
    timings = {}
    diagnostics = {}
    merged, parts = bm25_dense_candidates(
        question=question,
        chunks=chunks,
        embeddings=embeddings,
        vector_store=vector_store,
        candidate_k=candidate_k,
        timings=timings,
    )
    diagnostics.update(parts)
    graph_results, graph_diagnostics = timed(
        timings,
        "graph_retrieval",
        lambda: retrieve_graph_context_with_diagnostics(
            question,
            chunks,
            graph=graph,
            max_results=final_context_k,
            graph_policy=graph_policy,
        ),
    )
    diagnostics.update(graph_diagnostics)
    if graph_results:
        merged = timed(
            timings,
            "graph_merge",
            lambda: _merge_graph_and_vector_candidates(graph_results, merged, top_k=candidate_k),
        )
    else:
        timings["graph_merge"] = 0.0
    return merged[:final_context_k], timings, diagnostics


def run_full_project_stack(
    question: str,
    chunks,
    embeddings,
    vector_store,
    graph,
    candidate_k: int,
    final_context_k: int,
    graph_policy: str,
):
    timings = {}
    diagnostics = {}
    final_context_k = max(1, min(8, int(final_context_k or 8)))
    candidate_k = max(final_context_k, int(candidate_k or final_context_k))

    query = timed(timings, "alias_expansion", lambda: _bm25_dense_retrieval_query(question, question))
    metadata_query = timed(timings, "metadata_query", lambda: _effective_rrf_retrieval_query(question, question))
    filtered_chunks, filtered_embeddings = timed(
        timings,
        "metadata_filter",
        lambda: _metadata_filter_chunk_embedding_pairs(metadata_query, chunks, embeddings),
    )
    diagnostics["metadata_filtered_chunks"] = len(filtered_chunks)
    diagnostics["metadata_removed_chunks"] = len(chunks) - len(filtered_chunks)

    bm25_results = timed(timings, "bm25", lambda: keyword_search(query, filtered_chunks, top_k=candidate_k))
    ranked_lists = [("bm25", bm25_results)]
    diagnostics["bm25_candidates"] = len(bm25_results)

    allowed_chunk_ids = None
    if len(filtered_chunks) < len(chunks):
        allowed_chunk_ids = {chunk["id"] for chunk in filtered_chunks}
    dense_results = timed(
        timings,
        "dense",
        lambda: _dense_search_results(
            query,
            chunks=filtered_chunks,
            embeddings=filtered_embeddings,
            vector_store=vector_store,
            top_k=candidate_k,
            allowed_chunk_ids=allowed_chunk_ids,
        ),
    )
    ranked_lists.append(("qdrant_dense" if vector_store is not None else "dense", dense_results))
    diagnostics["dense_candidates"] = len(dense_results)

    definition_query = timed(timings, "definition_route", lambda: _definition_route_query(question))
    diagnostics["definition_query"] = definition_query
    if definition_query:
        definition_bm25_results = timed(
            timings,
            "definition_bm25",
            lambda: _definition_search_results(definition_query, filtered_chunks, top_k=candidate_k),
        )
        ranked_lists.append(("definition_bm25", definition_bm25_results))
        definition_dense_results = timed(
            timings,
            "definition_dense",
            lambda: _dense_search_results(
                definition_query,
                chunks=filtered_chunks,
                embeddings=filtered_embeddings,
                vector_store=vector_store,
                top_k=candidate_k,
                allowed_chunk_ids=allowed_chunk_ids,
            ),
        )
        ranked_lists.append(("definition_qdrant_dense" if vector_store is not None else "definition_dense", definition_dense_results))
        diagnostics["definition_bm25_candidates"] = len(definition_bm25_results)
        diagnostics["definition_dense_candidates"] = len(definition_dense_results)
    else:
        timings["definition_bm25"] = 0.0
        timings["definition_dense"] = 0.0
        diagnostics["definition_bm25_candidates"] = 0
        diagnostics["definition_dense_candidates"] = 0

    merged = timed(timings, "rrf_merge", lambda: _rrf_merge_ranked_results(ranked_lists, top_k=candidate_k))
    graph_results, graph_diagnostics = timed(
        timings,
        "graph_retrieval",
        lambda: retrieve_graph_context_with_diagnostics(
            question,
            chunks,
            graph=graph,
            max_results=final_context_k,
            graph_policy=graph_policy,
        ),
    )
    diagnostics.update(graph_diagnostics)
    if graph_results:
        merged = timed(
            timings,
            "graph_merge",
            lambda: _merge_graph_and_vector_candidates(graph_results, merged, top_k=candidate_k),
        )
    else:
        timings["graph_merge"] = 0.0

    timed(timings, "definition_boost", lambda: _apply_definition_route_boost(merged, definition_query))
    timed(timings, "rerank", lambda: _rerank_rrf_candidates(merged, question=question, rewritten_query=" ".join([query, definition_query])))
    reranked = sorted(merged, key=lambda item: item["score"], reverse=True)[:final_context_k]
    expanded = timed(
        timings,
        "parent_chunk_expansion",
        lambda: _expand_parent_chunks(reranked, chunks, max_contexts=final_context_k),
    )
    structured_results = timed(
        timings,
        "structured_result_retrieval",
        lambda: find_result_constrained_chunks(question, chunks, max_results=final_context_k),
    )
    diagnostics["structured_results"] = len(structured_results)
    if structured_results:
        expanded = timed(
            timings,
            "structured_result_merge",
            lambda: merge_event_list_chunks(structured_results, expanded)[:final_context_k],
        )
    else:
        timings["structured_result_merge"] = 0.0

    results = []
    for chunk in expanded:
        result = dict(chunk)
        result["retrieval_method"] = merge_retrieval_method(result.get("retrieval_method", ""), "rrf_parent_context")
        result.setdefault("rerank_trace", "")
        results.append(result)
    diagnostics["candidate_count"] = len(merged)
    return results, timings, diagnostics


def bm25_dense_candidates(
    question: str,
    chunks,
    embeddings,
    vector_store,
    candidate_k: int,
    timings: dict,
):
    bm25_results = timed(timings, "bm25", lambda: keyword_search(question, chunks, top_k=candidate_k))
    dense_results = timed(
        timings,
        "dense",
        lambda: _dense_search_results(
            question,
            chunks=chunks,
            embeddings=embeddings,
            vector_store=vector_store,
            top_k=candidate_k,
        ),
    )
    merged = timed(
        timings,
        "rrf_merge",
        lambda: _rrf_merge_ranked_results(
            [("bm25", bm25_results), ("qdrant_dense" if vector_store is not None else "dense", dense_results)],
            top_k=candidate_k,
        ),
    )
    return merged, {
        "bm25_candidates": len(bm25_results),
        "dense_candidates": len(dense_results),
        "candidate_count": len(merged),
    }


def retrieve_graph_context_with_diagnostics(
    question: str,
    chunks,
    graph,
    max_results: int = 8,
    graph_policy: str = "classified",
):
    classification = classify_query(question)
    diagnostics = {
        "query_classification": classification,
        "matched_graph_entities": [],
        "matched_graph_entity_ids": [],
        "graph_relation_candidates": 0,
        "graph_relation_candidate_examples": [],
        "graph_results": 0,
        "graph_context_ids": [],
    }
    entities = _graph_entity_records(graph)
    query_entities = extract_query_entities(question, alias_records=entities, project_root=PROJECT_ROOT)
    query_entity_ids = _matched_graph_entity_ids(query_entities, entities)
    diagnostics.update(
        {
            "matched_graph_entities": query_entities,
            "matched_graph_entity_ids": sorted(query_entity_ids),
            "graph_policy": graph_policy,
        }
    )
    if graph_policy == "classified" and classification["type"] == "content":
        diagnostics["graph_skip_reason"] = "classified_as_content"
        return [], diagnostics
    if graph_policy == "entity_overlap" and not query_entity_ids:
        diagnostics["graph_skip_reason"] = "no_matched_entities"
        return [], diagnostics

    relation_candidates = _rank_graph_relations(question, graph, query_entity_ids)
    diagnostics.update(
        {
            "graph_relation_candidates": len(relation_candidates),
            "graph_relation_candidate_examples": [
                relation_trace(relation, graph)
                for relation, _score in relation_candidates[:5]
            ],
        }
    )
    if not relation_candidates:
        diagnostics["graph_skip_reason"] = "no_relation_candidates"
        return [], diagnostics

    chunks_by_id = {chunk.get("id"): chunk for chunk in chunks}
    results = []
    seen = set()
    for relation, score in relation_candidates:
        for chunk_id in relation.get("supporting_chunk_ids", []) or []:
            if chunk_id in seen:
                continue
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                continue
            result = dict(chunk)
            result["score"] = max(float(result.get("score", 0.0)), score)
            result["retrieval_method"] = "graph"
            result["graph_trace"] = relation_trace(relation, graph)
            results.append(result)
            seen.add(chunk_id)
            if len(results) >= max_results:
                diagnostics["graph_results"] = len(results)
                diagnostics["graph_context_ids"] = [item.get("id", "") for item in results]
                diagnostics["graph_skip_reason"] = ""
                return results, diagnostics

    diagnostics["graph_results"] = len(results)
    diagnostics["graph_context_ids"] = [item.get("id", "") for item in results]
    diagnostics["graph_skip_reason"] = "" if results else "no_supported_chunks"
    return results, diagnostics


def relation_trace(relation, graph):
    names = {
        entity.get("id"): entity.get("name", entity.get("id", ""))
        for entity in graph.get("entities", []) or []
        if isinstance(entity, dict)
    }
    source = names.get(relation.get("source"), relation.get("source", ""))
    target = names.get(relation.get("target"), relation.get("target", ""))
    return f"{source} -{relation.get('type', '')}-> {target}"


def timed(timings: dict, name: str, fn: Callable):
    started = time.perf_counter()
    result = fn()
    timings[name] = round(time.perf_counter() - started, 6)
    return result


def load_questions(path: Path, limit: int | None):
    questions = json.loads(path.read_text(encoding="utf-8"))
    if limit is not None:
        questions = questions[:limit]
    return questions


def load_chunks(knowledge_base):
    index_path = knowledge_base.index_dir / "chunks.json"
    if index_path.exists():
        return load_index(index_path)
    return load_knowledge_base_chunks(knowledge_base.raw_dir)


def validate_graph(
    active_graph_path: Path,
    active_graph: dict,
    selected_graph_path: Path,
    selected_graph: dict,
    chunks,
    question_file: Path,
) -> dict:
    chunk_ids = {chunk.get("id") for chunk in chunks}
    selected_relations = [relation for relation in selected_graph.get("relations", []) if isinstance(relation, dict)]
    support_refs = [
        chunk_id
        for relation in selected_relations
        for chunk_id in (relation.get("supporting_chunk_ids", []) or [])
    ]
    missing_support_refs = [chunk_id for chunk_id in support_refs if chunk_id not in chunk_ids]
    relation_type_counts = Counter(str(relation.get("type", "")) for relation in selected_relations)
    relations_with_support = sum(1 for relation in selected_relations if relation.get("supporting_chunk_ids"))
    relations_with_valid_support = sum(
        1
        for relation in selected_relations
        if any(chunk_id in chunk_ids for chunk_id in (relation.get("supporting_chunk_ids", []) or []))
    )
    return {
        "question_file": str(question_file),
        "question_sha256": hash_file(question_file),
        "active_profile_graph_path": str(active_graph_path),
        "active_profile_graph_exists": active_graph_path.exists(),
        "active_profile_graph_sha256": hash_file(active_graph_path),
        "active_profile_graph_entities": len(active_graph.get("entities", []) or []),
        "active_profile_graph_relations": len(active_graph.get("relations", []) or []),
        "selected_graph_path": str(selected_graph_path),
        "selected_graph_exists": selected_graph_path.exists(),
        "selected_graph_sha256": hash_file(selected_graph_path),
        "selected_graph_entities": len(selected_graph.get("entities", []) or []),
        "selected_graph_relations": len(selected_relations),
        "selected_relation_type_counts": dict(sorted(relation_type_counts.items())),
        "selected_support_refs": len(support_refs),
        "selected_missing_support_refs": len(missing_support_refs),
        "selected_missing_support_ref_examples": missing_support_refs[:20],
        "selected_relations_with_support": relations_with_support,
        "selected_relations_with_valid_support": relations_with_valid_support,
        "chunk_count": len(chunks),
    }


def score_retrieved_context(chunks, item: dict) -> dict:
    context_text = normalize_text(
        "\n".join(
            f"{chunk.get('parent_title', '')}\n{chunk.get('title', '')}\n{chunk.get('content', '')}"
            for chunk in chunks
        )
    )
    score = 0
    matched = []
    missed = []
    for criterion in item.get("criteria", []):
        aliases = [normalize_text(alias) for alias in criterion.get("aliases", [])]
        matched_alias = next((alias for alias in aliases if alias and alias in context_text), "")
        if matched_alias:
            weight = int(criterion.get("weight", 1))
            score += weight
            matched.append({"label": criterion.get("label", ""), "weight": weight, "matched_alias": matched_alias})
        else:
            missed.append(criterion.get("label", ""))
    max_total = max_score(item)
    return {"score": min(score, max_total), "max_score": max_total, "matched": matched, "missed": missed}


def context_record(chunk) -> dict:
    return {
        "id": chunk.get("id", ""),
        "source": str(chunk.get("source", "")),
        "parent_title": chunk.get("parent_title", ""),
        "title": chunk.get("title", ""),
        "score": round(float(chunk.get("score", 0.0)), 6),
        "retrieval_method": chunk.get("retrieval_method", ""),
        "rerank_trace": chunk.get("rerank_trace", ""),
        "graph_trace": chunk.get("graph_trace", ""),
        "content_preview": re.sub(r"\s+", " ", str(chunk.get("content", ""))).strip()[:360],
    }


def write_report(
    report_path: Path,
    raw_path: Path,
    graph_validation_path: Path,
    questions_path: Path,
    graph_validation: dict,
    records,
    elapsed_seconds: float,
    candidate_k: int,
    final_context_k: int,
    setup_timings: dict,
    benchmark_name: str,
    graph_policy: str,
) -> None:
    by_variant = defaultdict(list)
    for record in records:
        by_variant[record["variant"]].append(record)

    lines = [
        f"# {benchmark_name} Incremental Retrieval Nodes",
        "",
        "本報告只測 Retrieval：檢查 Top Context 是否包含評分規準需要的 evidence，不呼叫 QA Agent。",
        "",
        "## 設定",
        "",
        f"- Questions: `{relative_path(questions_path)}`",
        f"- Questions SHA256: `{graph_validation['question_sha256']}`",
        f"- Raw JSONL: `{relative_path(raw_path)}`",
        f"- Graph Validation JSON: `{relative_path(graph_validation_path)}`",
        f"- Candidate K: `{candidate_k}`",
        f"- Final Context K: `{final_context_k}`",
        f"- Graph Policy: `{graph_policy}`",
        f"- Elapsed Seconds: `{elapsed_seconds}`",
        "",
        "## Graph 嚴謹檢查",
        "",
        f"- Active profile graph: `{graph_validation['active_profile_graph_path']}`",
        f"- Active profile graph exists: `{graph_validation['active_profile_graph_exists']}`",
        f"- Active profile graph SHA256: `{graph_validation['active_profile_graph_sha256']}`",
        f"- Active profile graph size: `{graph_validation['active_profile_graph_entities']}` entities / `{graph_validation['active_profile_graph_relations']}` relations",
        f"- Selected graph for Graph variants: `{graph_validation['selected_graph_path']}`",
        f"- Selected graph exists: `{graph_validation['selected_graph_exists']}`",
        f"- Selected graph SHA256: `{graph_validation['selected_graph_sha256']}`",
        f"- Selected graph size: `{graph_validation['selected_graph_entities']}` entities / `{graph_validation['selected_graph_relations']}` relations",
        f"- Relation support refs: `{graph_validation['selected_support_refs']}` total / `{graph_validation['selected_missing_support_refs']}` missing",
        f"- Relations with support: `{graph_validation['selected_relations_with_support']}` / `{graph_validation['selected_relations_with_valid_support']}` valid",
        "",
        "## Variant Definitions",
        "",
        "- `BM25-only`: project lexical/BM25 branch only, no Dense, no Graph, no alias expansion, no rerank, no parent expansion.",
        "- `BM25 + Dense`: same question text, project lexical/BM25 branch + Qdrant Dense, then RRF merge.",
        "- `BM25 + Dense + Graph`: previous stage + generated Graph retrieval branch and graph/vector merge.",
        "- `Full project stack`: alias expansion, metadata filter, BM25, Dense, RRF, Graph, definition route, rerank, parent chunk expansion, structured result retrieval.",
        "",
        "## Setup Timing",
        "",
        "| Node | Seconds |",
        "| --- | ---: |",
        *[f"| {key} | `{value:.4f}` |" for key, value in setup_timings.items()],
        "",
        "## Summary",
        "",
        "| Variant | Questions | Retrieval Upper Bound | Perfect Questions | Avg Total s | P95 Total s | Graph-hit Questions | Avg Graph s |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    summaries = {}
    for variant_name in [variant["name"] for variant in build_variants() if variant["name"] in by_variant]:
        summary = summarize_records(by_variant[variant_name])
        summaries[variant_name] = summary
        lines.append(
            f"| {by_variant[variant_name][0]['variant_label']} | {summary['count']} | "
            f"`{summary['score']}/{summary['max_score']} = {summary['percent']:.1f}%` | "
            f"`{summary['perfect']}/{summary['count']}` | "
            f"`{summary['avg_total']:.3f}` | `{summary['p95_total']:.3f}` | "
            f"`{summary['graph_hit_questions']}` | `{summary['avg_graph']:.3f}` |"
        )

    lines.extend(["", "## Incremental Delta", "", "| Step | Retrieval Delta | Avg Total Time Delta |", "| --- | ---: | ---: |"])
    for previous, current in (
        ("bm25_only", "bm25_dense"),
        ("bm25_dense", "bm25_dense_graph"),
        ("bm25_dense_graph", "full_project_stack"),
    ):
        if previous not in summaries or current not in summaries:
            continue
        prev_summary = summaries[previous]
        current_summary = summaries[current]
        lines.append(
            f"| {variant_label(previous)} -> {variant_label(current)} | "
            f"`{current_summary['percent'] - prev_summary['percent']:+.1f} pp` | "
            f"`{current_summary['avg_total'] - prev_summary['avg_total']:+.3f}s` |"
        )

    lines.extend(["", "## Node Timing By Variant", ""])
    timing_keys = sorted({key for record in records for key in record.get("timings_seconds", {})})
    lines.extend([
        "| Variant | " + " | ".join(timing_keys) + " |",
        "| --- | " + " | ".join("---:" for _ in timing_keys) + " |",
    ])
    for variant_name in [variant["name"] for variant in build_variants() if variant["name"] in by_variant]:
        timing_summary = summarize_timings(by_variant[variant_name], timing_keys)
        lines.append(
            f"| {variant_label(variant_name)} | "
            + " | ".join(f"`{timing_summary[key]:.4f}`" for key in timing_keys)
            + " |"
        )

    lines.extend(["", "## Graph Contribution", "", "| Variant | Graph Retrieval Fired | Final Contexts With Graph | Avg Graph Results |", "| --- | ---: | ---: | ---: |"])
    for variant_name in [variant["name"] for variant in build_variants() if variant["name"] in by_variant]:
        grouped = by_variant[variant_name]
        fired = sum(1 for record in grouped if int(record.get("diagnostics", {}).get("graph_results", 0)) > 0)
        final_graph_contexts = sum(
            1
            for record in grouped
            for context in record.get("contexts", [])
            if "graph" in str(context.get("retrieval_method", ""))
        )
        avg_graph_results = statistics.mean(
            int(record.get("diagnostics", {}).get("graph_results", 0))
            for record in grouped
        )
        lines.append(f"| {variant_label(variant_name)} | `{fired}` | `{final_graph_contexts}` | `{avg_graph_results:.2f}` |")

    lines.extend(["", "## Graph Diagnostics", "", "| Variant | Classification Counts | Skip Reasons | Avg Relation Candidates |", "| --- | --- | --- | ---: |"])
    for variant_name in [variant["name"] for variant in build_variants() if variant["name"] in by_variant]:
        grouped = by_variant[variant_name]
        classification_counts = Counter(
            str(record.get("diagnostics", {}).get("query_classification", {}).get("type", "n/a"))
            for record in grouped
        )
        skip_counts = Counter(str(record.get("diagnostics", {}).get("graph_skip_reason", "n/a")) for record in grouped)
        avg_relation_candidates = statistics.mean(
            int(record.get("diagnostics", {}).get("graph_relation_candidates", 0))
            for record in grouped
        )
        lines.append(
            f"| {variant_label(variant_name)} | `{dict(classification_counts)}` | "
            f"`{dict(skip_counts)}` | `{avg_relation_candidates:.2f}` |"
        )

    lines.extend(["", "## Missed / Partial", ""])
    for variant_name in [variant["name"] for variant in build_variants() if variant["name"] in by_variant]:
        missed_records = [
            record
            for record in by_variant[variant_name]
            if record["retrieval_upper_bound_score"] < record["max_score"]
        ]
        lines.extend([
            f"### {variant_label(variant_name)}",
            "",
            "| ID | Score | Missed | Question | Top Contexts |",
            "| --- | ---: | --- | --- | --- |",
        ])
        if not missed_records:
            lines.append("| - | - | - | - | - |")
            lines.append("")
            continue
        for record in missed_records[:60]:
            contexts = "<br>".join(
                f"{index + 1}. {Path(context['source']).name} / {context['title']}"
                for index, context in enumerate(record["contexts"][:final_context_k])
            )
            lines.append(
                f"| {record['id']} | `{record['retrieval_upper_bound_score']}/{record['max_score']}` | "
                f"{', '.join(record.get('missed', [])) or '-'} | {record['question']} | {contexts or '-'} |"
            )
        if len(missed_records) > 60:
            lines.append(f"| ... | ... | ... | omitted `{len(missed_records) - 60}` more rows; see raw JSONL | ... |")
        lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_records(records):
    score = sum(record["retrieval_upper_bound_score"] for record in records)
    max_total = sum(record["max_score"] for record in records)
    totals = [float(record["timings_seconds"].get("total", 0.0)) for record in records]
    graph_times = [float(record["timings_seconds"].get("graph_retrieval", 0.0)) for record in records]
    return {
        "count": len(records),
        "score": score,
        "max_score": max_total,
        "percent": score / max_total * 100 if max_total else 0.0,
        "perfect": sum(1 for record in records if record["retrieval_upper_bound_score"] == record["max_score"]),
        "avg_total": statistics.mean(totals) if totals else 0.0,
        "p95_total": percentile(totals, 95),
        "avg_graph": statistics.mean(graph_times) if graph_times else 0.0,
        "graph_hit_questions": sum(1 for record in records if int(record.get("diagnostics", {}).get("graph_results", 0)) > 0),
    }


def summarize_timings(records, timing_keys):
    return {
        key: statistics.mean(float(record.get("timings_seconds", {}).get(key, 0.0)) for record in records)
        for key in timing_keys
    }


def percentile(values, percent: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percent / 100))
    return ordered[index]


def max_score(item: dict) -> int:
    return sum(int(criterion.get("weight", 1)) for criterion in item.get("criteria", []))


def normalize_text(text: str) -> str:
    table = str.maketrans({"臺": "台", "裡": "裏", "妳": "你"})
    return re.sub(r"\s+", "", str(text).translate(table)).lower()


def merge_retrieval_method(left: str, right: str) -> str:
    methods = [method for method in (str(left), str(right)) if method]
    return "+".join(dict.fromkeys(methods))


def relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_path(path: Path) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_absolute():
        return expanded
    return (ROOT / expanded).resolve(strict=False)


def hash_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def variant_label(name: str) -> str:
    labels = {variant["name"]: variant["label"] for variant in build_variants()}
    return labels.get(name, name)


if __name__ == "__main__":
    raise SystemExit(main())
