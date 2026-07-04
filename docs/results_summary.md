# IFRS 17 Retrieval Benchmark Summary

Run ID: `full-ifrs17-20260704`

Benchmark: `IFRS 17 Mixed100`

Scope: retrieval only. The QA agent was not called.

| Variant | Retrieval score | Perfect questions | Avg total time | P95 total time |
| --- | ---: | ---: | ---: | ---: |
| BM25-only | 443/500 = 88.6% | 70/100 | 0.2719s | 0.3612s |
| BM25 + Dense | 448/500 = 89.6% | 70/100 | 0.3659s | 0.3835s |
| BM25 + Dense + Graph | 340/500 = 68.0% | 50/100 | 0.2954s | 0.3776s |
| Full project stack | 245/500 = 49.0% | 31/100 | 0.7298s | 1.2930s |

## Node Timing

| Variant | BM25 | Dense | Graph retrieval | Rerank | Parent expansion | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25-only | 0.2714s | - | - | - | - | 0.2719s |
| BM25 + Dense | 0.2712s | 0.0941s | - | - | - | 0.3659s |
| BM25 + Dense + Graph | 0.2767s | 0.0171s | 0.0010s | - | - | 0.2954s |
| Full project stack | 0.6918s | 0.0300s | 0.0010s | 0.0032s | 0.0016s | 0.7298s |

## Graph Check

- Entities: 96
- Relations: 25
- Support refs: 125
- Missing support refs: 0
- Relations with valid support: 25/25
- Chunk count: 1,190

## Interpretation

BM25 + Dense was the strongest variant in this run. Graph retrieval validated structurally, but hurt ranking because the entity-overlap policy matched broad IFRS 17 entities too aggressively. This is a useful negative result: graph construction alone is not enough; the graph retrieval gate and merge policy need to be selective.
