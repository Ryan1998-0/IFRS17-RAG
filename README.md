# IFRS17 RAG

Retrieval-only RAG benchmark for IFRS 17 materials. The project compares four retrieval stacks on a 100-question mixed benchmark:

- BM25-only
- BM25 + Dense
- BM25 + Dense + Graph
- Full project stack

The purpose is to show a controlled RAG evaluation workflow, not to provide accounting advice or IFRS compliance evidence.

## Public-data note

This repository does not include IFRS Foundation PDFs, extracted full text, embeddings, Qdrant index files, raw JSONL retrieval logs, or reports with long content previews. The scripts download public IFRS Foundation PDFs into your local workspace so you can reproduce the benchmark locally. Check the IFRS Foundation terms before redistributing source documents or extracted text.

## Results

The latest local run used 100 mixed IFRS 17 questions and scored retrieval only. The score is the retrieval upper bound: whether the final top contexts contain the evidence required by each question's scoring criteria.

| Variant | Retrieval score | Perfect questions | Avg total time | P95 total time |
| --- | ---: | ---: | ---: | ---: |
| BM25-only | 443/500 = 88.6% | 70/100 | 0.2719s | 0.3612s |
| BM25 + Dense | 448/500 = 89.6% | 70/100 | 0.3659s | 0.3835s |
| BM25 + Dense + Graph | 340/500 = 68.0% | 50/100 | 0.2954s | 0.3776s |
| Full project stack | 245/500 = 49.0% | 31/100 | 0.7298s | 1.2930s |

Graph validation for the local run:

- 96 entities
- 25 relations
- 125 support refs
- 0 missing support refs
- 1,190 chunks

The important finding is that Graph RAG did not help in this configuration. The graph itself validated cleanly, but the entity-overlap policy matched the generic entity `IFRS 17` too often, so graph retrieval became a broad expansion step and displaced more precise BM25/Dense chunks.

## Interactive demo

Static demo website:

[https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/](https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/)

The demo lets you type Chinese or English IFRS 17 questions, inspect the retrieved evidence chunks, switch retrieval variants, and view the IFRS 4 vs IFRS 17 comparison graph. It runs entirely in the browser from sanitized demo data and does not include the local Agent backend.

## Supplemental study: Graph RAG suitability

This repo also includes a controlled supplemental study on when Graph RAG is useful:

- Report: `docs/graph_rag_suitability_report.md`
- Reproducible script: `evals/graph_suitability/run_graph_suitability_experiment.py`
- Summary JSON: `evals/graph_suitability/results/graph-suitability-20260704-summary.json`

The short result: Graph RAG is most useful when the data has stable entities and relationships and questions need multi-hop evidence. It is not a default upgrade for flat FAQ-style knowledge bases, and it can hurt retrieval when broad hub entities are allowed to dominate graph expansion.

## Reproduce

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

./scripts/download_ifrs17_sources.sh
python3 evals/ifrs17_retrieval/build_ifrs17_benchmark.py
RAG_PROFILE=ifrs17 python3 -m rag_demo.ingest
python3 evals/ifrs17_retrieval/build_ifrs17_benchmark.py --skip-pdf-extraction

RAG_PROFILE=ifrs17 python3 evals/ifrs17_retrieval/run_incremental_retrieval_nodes.py \
  --benchmark-name "IFRS 17 Mixed100" \
  --candidate-k 50 \
  --final-context-k 8 \
  --variants bm25_only,bm25_dense,bm25_dense_graph,full_project_stack \
  --graph-policy entity_overlap \
  --run-id full-ifrs17-local
```

Outputs are written to `evals/ifrs17_retrieval/runs/`, which is ignored by git because the raw records can include source-document previews.

## Repository layout

```text
rag_demo/                         RAG pipeline code
evals/ifrs17_retrieval/           IFRS 17 benchmark builder, runner, questions
evals/graph_suitability/          Supplemental Graph RAG suitability experiment
profiles/ifrs17/                  IFRS 17 profile config, aliases, graph, manifest
scripts/download_ifrs17_sources.sh Local PDF download helper
docs/                             Short result notes
```

## Source documents

The benchmark was built from IFRS Foundation public PDFs listed in `profiles/ifrs17/corpus_manifest.json`, including the IFRS 17 standard, effects analysis, project summaries, fact sheet, and implementation examples.
