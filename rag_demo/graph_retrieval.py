import re

from rag_demo.graph_entities import extract_query_entities
from rag_demo.graph_store import load_graph
from rag_demo.query_classifier import classify_query


def retrieve_graph_context(question: str, chunks, graph=None, project_root=None, max_results: int = 8):
    classification = classify_query(question)
    if classification["type"] == "content":
        return []

    graph_data = graph if graph is not None else load_graph(project_root=project_root)
    entities = _graph_entity_records(graph_data)
    query_entities = extract_query_entities(question, alias_records=entities, project_root=project_root)
    query_entity_ids = _matched_graph_entity_ids(query_entities, entities)
    relation_candidates = _rank_graph_relations(question, graph_data, query_entity_ids)
    if not relation_candidates:
        return []

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
            result["graph_trace"] = _relation_trace(relation, graph_data)
            results.append(result)
            seen.add(chunk_id)
            if len(results) >= max_results:
                return results
    return results


def _graph_entity_records(graph):
    records = []
    for entity in graph.get("entities", []) or []:
        if not isinstance(entity, dict):
            continue
        records.append(
            {
                "canonical": entity.get("name", entity.get("id", "")),
                "type": entity.get("type", "entity"),
                "aliases": entity.get("aliases", []) or [],
                "id": entity.get("id", ""),
            }
        )
    return records


def _matched_graph_entity_ids(query_entities, graph_entity_records):
    ids = set()
    for query_entity in query_entities:
        name = _compact(query_entity.get("name", ""))
        entity_type = str(query_entity.get("type", "")).lower()
        for record in graph_entity_records:
            if _compact(record.get("canonical", "")) != name:
                continue
            if str(record.get("type", "")).lower() != entity_type:
                continue
            if record.get("id"):
                ids.add(record["id"])
    return ids


def _rank_graph_relations(question: str, graph, query_entity_ids):
    compact_question = _compact(question)
    ranked = []
    for relation in graph.get("relations", []) or []:
        if not isinstance(relation, dict):
            continue
        endpoints = {relation.get("source"), relation.get("target")}
        score = 0.0
        overlap = len(query_entity_ids.intersection(endpoints))
        if overlap:
            score += 2.0 * overlap
        relation_type = str(relation.get("type", ""))
        if _relation_type_matches_question(relation_type, compact_question):
            score += 1.5
        score += float(relation.get("confidence", 0.0)) * 0.5
        if score > 0:
            ranked.append((relation, score))
    return sorted(ranked, key=lambda item: item[1], reverse=True)


def _relation_type_matches_question(relation_type: str, compact_question: str) -> bool:
    relation_type = relation_type.upper()
    relation_terms = {
        "MEMBER_OF": ("屬於", "属于", "哪一派", "成員", "成员", "組織", "组织"),
        "LEADS": ("領導", "领导", "統帥", "统帅", "建立"),
        "PARTICIPATED_IN": ("參與", "参与", "涉及", "事件"),
        "LOCATED_IN": ("哪裡", "哪里", "地點", "地点", "基地"),
        "USES": ("使用", "用", "材料", "工具"),
        "HAS_GOAL": ("目的", "希望", "主張", "主张", "目標", "目标"),
    }
    return any(_compact(term) in compact_question for term in relation_terms.get(relation_type, ()))


def _relation_trace(relation, graph):
    names = _entity_names_by_id(graph)
    source = names.get(relation.get("source"), relation.get("source", ""))
    target = names.get(relation.get("target"), relation.get("target", ""))
    return f"{source} -{relation.get('type', '')}-> {target}"


def _entity_names_by_id(graph):
    return {
        entity.get("id"): entity.get("name", entity.get("id", ""))
        for entity in graph.get("entities", []) or []
        if isinstance(entity, dict)
    }


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).lower()
