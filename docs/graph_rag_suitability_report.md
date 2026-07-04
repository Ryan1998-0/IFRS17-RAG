# Graph RAG Suitability Experiment Report

本報告只測 Retrieval，不測 LLM 最終回答。分數代表 Top 5 contexts 是否包含該題需要的 evidence chunks。

這是一個合成但可控的 suitability benchmark，目的不是宣稱某個分數可以外推到所有企業資料庫，而是隔離「資料型態」對 Graph RAG 的影響。

## 結論先講

- Graph 最適合用在「資料彼此有明確關係，而且問題需要沿關係找證據」的資料庫，例如客戶/保單/理賠、醫療知識圖、法規交叉引用、產品零件依賴、研究論文引用網路。
- Graph 不適合拿來硬加在平面 FAQ 或單段答案 KB 上，因為答案本來就在單一 chunk，Graph 沒有可補的關係。
- Graph 在單一大主題、hub entity 很強的資料庫上容易變差；例如所有資料都連到同一個 `IFRS 17` 或同一個產品名時，Graph 會把無關 chunk 一起拉進 Top K。
- Graph 的關鍵不是有沒有建圖，而是 entity gating、relation gating、以及 graph chunk merge 權重是否精準。

## 設定

- Run ID: `graph-suitability-20260704`
- Top K: `5`
- Datasets: `4`
- Questions: `96`
- Raw rows: `480`
- Raw JSONL: generated locally at `evals/graph_suitability/runs/graph-suitability-20260704.jsonl`
- Summary JSON: `evals/graph_suitability/results/graph-suitability-20260704-summary.json`
- Dense 欄位使用 deterministic semantic proxy，不呼叫外部 embedding model；本實驗重點是隔離 Graph 對資料型態的影響。
- `Graph-priority merge` 是故意設計的反例，用來模擬 graph prior / graph boost 過強時的 hub 污染。

## Suitability Matrix

| Data type | Result in this experiment | Recommendation |
| --- | --- | --- |
| 關聯型個案資料庫 | Graph 從 38.9% 拉到 100.0% | 適合，尤其是多跳 entity relation 問題 |
| 交叉引用手冊/法規資料庫 | Graph 從 38.9% 拉到 100.0% | 適合，尤其是 workflow -> section -> exception 這類引用鏈 |
| 平面 FAQ / 單段答案資料庫 | BM25 已 100.0%，Graph 沒有新增收益 | 不優先使用 Graph，先用 BM25/Hybrid/metadata filter |
| 單一大主題 / hub-heavy 資料庫 | Graph-priority merge 掉到 25.0%，precise Graph 回到 100.0% | 條件式適合；必須排除泛用 hub 並控制 graph merge 權重 |

## Overall Score

| Dataset | Variant | Score | Perfect | Zero | Avg total s | Avg graph candidates |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 關聯型個案資料庫 | BM25-only | `32/72 = 44.4%` | `0/24` | `0` | `0.000078` | `0.00` |
| 關聯型個案資料庫 | BM25 + semantic proxy | `28/72 = 38.9%` | `0/24` | `0` | `0.000120` | `0.00` |
| 關聯型個案資料庫 | BM25 + semantic proxy + Graph | `72/72 = 100.0%` | `24/24` | `0` | `0.000136` | `3.00` |
| 關聯型個案資料庫 | BM25 + semantic proxy + Graph-priority merge | `72/72 = 100.0%` | `24/24` | `0` | `0.000121` | `3.00` |
| 關聯型個案資料庫 | BM25 + semantic proxy + precise Graph | `72/72 = 100.0%` | `24/24` | `0` | `0.000121` | `3.00` |
| 交叉引用手冊/法規資料庫 | BM25-only | `32/72 = 44.4%` | `0/24` | `0` | `0.000068` | `0.00` |
| 交叉引用手冊/法規資料庫 | BM25 + semantic proxy | `28/72 = 38.9%` | `0/24` | `0` | `0.000096` | `0.00` |
| 交叉引用手冊/法規資料庫 | BM25 + semantic proxy + Graph | `72/72 = 100.0%` | `24/24` | `0` | `0.000111` | `3.00` |
| 交叉引用手冊/法規資料庫 | BM25 + semantic proxy + Graph-priority merge | `72/72 = 100.0%` | `24/24` | `0` | `0.000110` | `3.00` |
| 交叉引用手冊/法規資料庫 | BM25 + semantic proxy + precise Graph | `72/72 = 100.0%` | `24/24` | `0` | `0.000110` | `3.00` |
| 平面 FAQ / 單段答案資料庫 | BM25-only | `24/24 = 100.0%` | `24/24` | `0` | `0.000073` | `0.00` |
| 平面 FAQ / 單段答案資料庫 | BM25 + semantic proxy | `24/24 = 100.0%` | `24/24` | `0` | `0.000123` | `0.00` |
| 平面 FAQ / 單段答案資料庫 | BM25 + semantic proxy + Graph | `24/24 = 100.0%` | `24/24` | `0` | `0.000118` | `0.00` |
| 平面 FAQ / 單段答案資料庫 | BM25 + semantic proxy + Graph-priority merge | `24/24 = 100.0%` | `24/24` | `0` | `0.000123` | `0.00` |
| 平面 FAQ / 單段答案資料庫 | BM25 + semantic proxy + precise Graph | `24/24 = 100.0%` | `24/24` | `0` | `0.000123` | `0.00` |
| 單一大主題 / hub-heavy 資料庫 | BM25-only | `24/24 = 100.0%` | `24/24` | `0` | `0.000058` | `0.00` |
| 單一大主題 / hub-heavy 資料庫 | BM25 + semantic proxy | `24/24 = 100.0%` | `24/24` | `0` | `0.000096` | `0.00` |
| 單一大主題 / hub-heavy 資料庫 | BM25 + semantic proxy + Graph | `24/24 = 100.0%` | `24/24` | `0` | `0.000131` | `24.00` |
| 單一大主題 / hub-heavy 資料庫 | BM25 + semantic proxy + Graph-priority merge | `6/24 = 25.0%` | `6/24` | `18` | `0.000131` | `24.00` |
| 單一大主題 / hub-heavy 資料庫 | BM25 + semantic proxy + precise Graph | `24/24 = 100.0%` | `24/24` | `0` | `0.000101` | `0.00` |

## Incremental Delta

### 關聯型個案資料庫

Graph 應該明顯有幫助，因為答案分散在 claimant -> policy -> rider 的多跳關係上。

| Step | Delta | Interpretation |
| --- | ---: | --- |
| BM25 -> Semantic | `-5.6%` | 下降，代表額外節點引入噪音或 merge 權重過強。 |
| Semantic -> Graph | `+61.1%` | 提升，代表這類資料型態有可利用的語意或關係結構。 |
| Semantic -> Graph-priority | `+61.1%` | 提升，代表這類資料型態有可利用的語意或關係結構。 |
| Semantic -> Precise Graph | `+61.1%` | 提升，代表這類資料型態有可利用的語意或關係結構。 |

### 交叉引用手冊/法規資料庫

Graph 應該中度到高度有幫助，因為問題需要沿 workflow -> section -> exception 找上下文。

| Step | Delta | Interpretation |
| --- | ---: | --- |
| BM25 -> Semantic | `-5.6%` | 下降，代表額外節點引入噪音或 merge 權重過強。 |
| Semantic -> Graph | `+61.1%` | 提升，代表這類資料型態有可利用的語意或關係結構。 |
| Semantic -> Graph-priority | `+61.1%` | 提升，代表這類資料型態有可利用的語意或關係結構。 |
| Semantic -> Precise Graph | `+61.1%` | 提升，代表這類資料型態有可利用的語意或關係結構。 |

### 平面 FAQ / 單段答案資料庫

Graph 應該幾乎沒有幫助，因為答案已經在單一 chunk 內。

| Step | Delta | Interpretation |
| --- | ---: | --- |
| BM25 -> Semantic | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |
| Semantic -> Graph | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |
| Semantic -> Graph-priority | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |
| Semantic -> Precise Graph | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |

### 單一大主題 / hub-heavy 資料庫

Graph 可能造成傷害，因為所有資料都連到同一個泛用 hub，Graph 會把無關 chunk 推進 Top K。

| Step | Delta | Interpretation |
| --- | ---: | --- |
| BM25 -> Semantic | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |
| Semantic -> Graph | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |
| Semantic -> Graph-priority | `-75.0%` | 下降，符合預期：泛用 hub 把不相關 chunks 推進 Top K。 |
| Semantic -> Precise Graph | `+0.0%` | 幾乎持平，代表該節點沒有提供新 evidence。 |

## What This Means

### 適合 Graph 的資料庫

1. 關聯型業務資料：客戶、合約、訂單、理賠、案件、設備、零件彼此有明確 ID 關係。
2. 交叉引用型文件：法規、會計準則、SOP、醫療 guideline、技術手冊。
3. 多跳問題常見的 KB：問題通常不是問單一段落，而是要從 A 找到 B，再從 B 找到 C。
4. 需要全局 sensemaking 的大型語料：主題、社群、事件脈絡比單一 chunk 更重要。

### 不適合或要小心的資料庫

1. 平面 FAQ：每題答案都在單一 chunk，Graph 成本大於收益。
2. 單一大主題語料：所有資料都連到同一個 hub entity，Graph 會把噪音拉進來。
3. 純數值/聚合查詢：例如算總額、平均、排名，應優先用 SQL/OLAP，不是 Graph RAG。
4. 關係抽取品質不穩的資料：Graph 錯邊會比沒有 Graph 更糟。

## Practical Rule

如果你的問題需要「沿關係找資料」，Graph 值得做；如果你的問題只是「找最像的一段文字」，BM25 + Dense 通常比較穩。Graph RAG 的投資門檻是：資料要有穩定 entity、穩定 relation、可驗證 support chunk，並且 graph retrieval 要能排除泛用 hub。

## Negative Results To Keep

- `平面 FAQ` 沒有因為 Graph 變好。這不是壞結果，而是告訴我們單段答案型 KB 不需要優先上 Graph。
- `hub-heavy` 在 Graph-priority merge 下掉到 25.0%。這對應 IFRS17 實驗看到的現象：如果所有問題都命中 `IFRS 17` 這種泛用 entity，Graph 可能把無關 chunk 推進 Top K。
- Semantic proxy 在多跳資料上從 BM25 的 44.4% 掉到 38.9%。這提醒我們：加一個語意候選分支不一定提升，merge 與 rerank 仍然要測。

## Practical Decision Rule

| 問題 | 建議 |
| --- | --- |
| 答案是否通常在單一 chunk？ | 先用 BM25 + Dense，不要急著 Graph |
| 是否需要從 A 找到 B，再從 B 找到 C？ | Graph 值得進候選方案 |
| 資料是否有穩定 ID、entity、relation、foreign key、引用關係？ | Graph 成本較合理 |
| 是否存在大量泛用 hub entity？ | Graph 需要 hub suppression / precise gating |
| 是否是統計聚合、排序、總額計算？ | 優先 SQL/OLAP，不是 Graph RAG |

## References

- Microsoft GraphRAG: https://arxiv.org/abs/2404.16130
- HippoRAG: https://arxiv.org/abs/2405.14831
- G-Retriever: https://arxiv.org/abs/2402.07630
- When to use Graphs in RAG: https://arxiv.org/html/2506.05690v3
- Cache-Augmented Generation: https://arxiv.org/abs/2412.15605
