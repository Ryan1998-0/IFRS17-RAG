# IFRS17 RAG 中文專案說明

這個專案以 IFRS 17 專業文件為主要 knowledge base，目標不是做會計建議，而是展示一套可以被評估、比較、重現的 RAG 架構。

專案主軸是：先把 Retrieval 拆開測，再比較 BM25、Dense、Graph、Full stack 這幾種架構的效果。Graph RAG 研究和三體 RAG 專案則作為補充證據，用來回答一個更實際的問題：什麼資料庫適合加 Graph，什麼資料庫不適合。

## 線上 Demo

- GitHub Pages 首頁：[https://ryan1998-0.github.io/IFRS17-RAG/](https://ryan1998-0.github.io/IFRS17-RAG/)
- IFRS17 互動 Demo：[https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/](https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/)
- 完整中文專案整理：[docs/project_overview_zh.md](docs/project_overview_zh.md)

Demo 可以輸入中文或英文 IFRS17 問題，檢查檢索到的 evidence chunks，並切換四種 retrieval 架構：

Demo 也可以手動選擇 QA Agent LLM，以及選擇 knowledge base profile。公開靜態版目前只有 IFRS17 會在 browser-side 執行檢索；三體作為 Agent profile 傳給後端 endpoint，不把完整小說語料打包進 GitHub Pages。

| 架構 | 說明 |
| --- | --- |
| BM25-only | 只用關鍵字與詞頻訊號，適合條文號、專有名詞、精確詞查詢。 |
| BM25 + Dense | 加入語意相似度分支，補強口語化或與原文措辭不同的問題。 |
| BM25 + Dense + Graph | 再加入 Graph Retrieval，用 entity/relation 補多跳或關係型問題。 |
| Full stack lab | Translation Agent、Metadata Filter、BM25、Dense proxy / Alias expansion、Graph Retrieval、RRF Merge、Reranker、Graph Hub Guard、Evidence Quality Gate、Comparison Graph。 |

## IFRS17 主架構

本專案的核心流程是 retrieval-first：

```text
User Question
↓
Translation / Query Normalization
↓
Metadata Filter
↓
BM25 + Dense + Graph Retrieval
↓
RRF Merge
↓
Reranker
↓
Graph Hub Guard / Evidence Quality Gate
↓
Top Evidence Chunks
↓
QA Agent or Browser-side Grounded Answer
```

這個設計刻意把 Retrieval 和 QA Agent 拆開。因為如果答案錯了，需要先知道是「資料沒有找對」，還是「資料找到了但模型沒有用好」。

## IFRS17 Retrieval 實驗結果

最新本地實驗使用 `IFRS 17 Mixed100`，只測 Retrieval，不測 LLM 最終回答。分數代表 Top contexts 是否包含題目需要的 evidence。

| Variant | Retrieval score | Perfect questions | Avg total time | P95 total time |
| --- | ---: | ---: | ---: | ---: |
| BM25-only | `443/500 = 88.6%` | `70/100` | `0.2719s` | `0.3612s` |
| BM25 + Dense | `448/500 = 89.6%` | `70/100` | `0.3659s` | `0.3835s` |
| BM25 + Dense + Graph | `340/500 = 68.0%` | `50/100` | `0.2954s` | `0.3776s` |
| Full project stack | `245/500 = 49.0%` | `31/100` | `0.7298s` | `1.2930s` |

關鍵結論：IFRS17 這組資料裡，BM25 + Dense 最穩。Graph 本身建置是乾淨的，graph validation 沒有缺 support refs，但 entity-overlap policy 太容易命中 `IFRS 17` 這種泛用 hub entity，導致 Graph 把不相關 chunks 拉進 Top K。

## Graph RAG 適用性研究

為了避免只從 IFRS17 這個反例下結論，本專案另外做了一組合成但可控的 Graph suitability benchmark。完整報告在 [docs/graph_rag_suitability_report.md](docs/graph_rag_suitability_report.md)。

| Data type | Graph 效果 | 建議 |
| --- | --- | --- |
| 關聯型個案資料庫 | `38.9% -> 100.0%` | 適合 Graph，尤其是多跳 entity relation 問題。 |
| 交叉引用手冊/法規資料庫 | `38.9% -> 100.0%` | 適合 Graph，尤其是 workflow -> section -> exception 這類引用鏈。 |
| 平面 FAQ / 單段答案資料庫 | BM25 已 `100.0%` | 不優先 Graph，先用 BM25 / Dense / metadata filter。 |
| 單一大主題 / hub-heavy 資料庫 | Graph-priority merge 掉到 `25.0%` | 條件式適合，必須做 hub suppression / precise gating。 |

實務規則很簡單：如果問題需要沿關係找資料，Graph 值得做；如果只是找最像的一段文字，BM25 + Dense 通常比較穩。

這裡要特別注意：Graph 變差不一定是因為速度慢。IFRS17 實驗中 Graph retrieval 平均只約 `0.001s`，真正問題是 hub entity、relation gating、merge 權重把不相關 chunks 推進 Top K。

## 三體 RAG 專案如何補充這個專案

三體 RAG 是另一個資料型態的驗證案例。它不是 IFRS17 的主專案，但可以補充兩個觀察：

1. 對小說、人物、事件這種自然語言問題，Hybrid retrieval 確實有幫助。
2. Graph 不是越加越好，如果 graph relation 或 merge policy 不夠精準，也會把錯誤關係 chunk 推進 Top K。

三體 Mixed200 retrieval-only 實驗：

| Stage | Retrieval Upper Bound | Avg Total s | 結論 |
| --- | ---: | ---: | --- |
| BM25-only | `71.1%` | `0.160s` | lexical baseline 可用，但對自然語言混合題不足。 |
| BM25 + Dense | `82.7%` | `0.227s` | Dense 對改寫題、長句題有明確幫助。 |
| BM25 + Dense + Graph | `79.3%` | `0.183s` | Graph 有觸發，但錯誤關係 chunk 會傷害 Top K。 |
| Full project stack | `82.6%` | `0.315s` | 詞表、rerank、parent expansion 等技術補回分數。 |

三體檢索詞表實驗也顯示，KB-aware vocabulary alignment 可以把使用者口語說法對齊到知識庫中真正出現的詞：

| Dataset | Retrieval Upper Bound |
| --- | ---: |
| Mixed 200 原版 | `73.6%` |
| Mixed 200 附檢索詞表 | `87.6%` |

## 專案價值

這個專案的價值不是「Graph 一定比較強」，而是展示一個比較成熟的 RAG 評估方式：

- 先測 Retrieval，再測 QA Agent。
- 每個 retrieval node 都要有可比較的分數與時間。
- Graph 要看資料型態，不是預設打開。
- 專業文件型 KB 需要特別處理 hub entity、metadata filter、evidence quality。
- Graph 更適合當條件式 candidate branch，不應該無條件當成 ranking boost。
- Demo 可以互動展示，但研究結論要回到可重現的 eval artifacts。

## 主要檔案

| Path | 用途 |
| --- | --- |
| [docs/project_overview_zh.md](docs/project_overview_zh.md) | 中文完整專案整理。 |
| [docs/results_summary.md](docs/results_summary.md) | IFRS17 retrieval-only 結果摘要。 |
| [docs/graph_rag_suitability_report.md](docs/graph_rag_suitability_report.md) | Graph 適用性研究報告。 |
| [docs/ifrs17-demo/](docs/ifrs17-demo/) | GitHub Pages 靜態互動 Demo。 |
| [evals/ifrs17_retrieval/](evals/ifrs17_retrieval/) | IFRS17 題庫、benchmark builder、retrieval runner。 |
| [evals/graph_suitability/](evals/graph_suitability/) | Graph suitability benchmark。 |
| [profiles/ifrs17/](profiles/ifrs17/) | IFRS17 profile、aliases、graph、manifest。 |
| [rag_demo/](rag_demo/) | RAG pipeline 程式碼。 |

## 免責說明

本專案是 RAG 架構與檢索評估展示，不提供會計、保險、法遵或 IFRS 合規建議。公開 repo 不包含 IFRS Foundation PDF 原文、完整抽取文字、embedding index、Qdrant index 或含長文本 preview 的 raw logs。
