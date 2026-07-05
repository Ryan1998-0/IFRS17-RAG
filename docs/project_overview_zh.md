# IFRS17 RAG 中文專案整理

## 一句話定位

這個專案以 IFRS17 專業文件為主 knowledge base，展示一套 retrieval-first 的 Hybrid RAG / Graph RAG 評估架構；Graph suitability 研究和三體 RAG 實驗則作為補充案例，用來說明不同資料型態下，RAG 架構不應該一套到底。

## 專案為什麼這樣設計

RAG 最常見的問題是：答案錯了以後，很難知道錯在哪裡。可能是檢索沒有找到資料，也可能是資料找到了但 QA Agent 沒有用好，也可能是 Graph 或 reranker 把錯誤 evidence 推到前面。

所以這個專案先把 Retrieval 從 QA Agent 裡拆出來，只測 Top contexts 是否包含答案需要的 evidence。這樣可以直接比較每一個 retrieval node 對正確率與時間的影響。

## 主架構：IFRS17 Retrieval-first RAG

```text
User Question
↓
Translation Agent / Query Normalization
↓
Metadata Filter
↓
BM25 + Dense + Graph Retrieval
↓
RRF Merge
↓
Graph Hub Guard / Evidence Quality Gate
↓
Top Evidence Chunks
↓
QA Agent or Browser-side Grounded Answer
```

### 架構節點說明

| 節點 | 作用 | 在 IFRS17 的觀察 |
| --- | --- | --- |
| Translation Agent / Query Normalization | 讓中文、英文、口語化問題能對齊 IFRS17 詞彙。 | Demo 支援中文問題，並保留英文 IFRS17 term。 |
| Metadata Filter | 先縮小文件或資料類型範圍。 | 專業文件常有封面、目錄、effects analysis、implementation example 等不同內容，需要過濾。 |
| BM25 | 保留條文號、專有名詞、精確詞。 | IFRS17 這類專業文件 lexical signal 很強，BM25-only 已有 `88.6%`。 |
| Dense | 補語意相似與非原文措辭問題。 | BM25 + Dense 提升到 `89.6%`，是本次 IFRS17 最佳結果。 |
| Graph Retrieval | 用 entity / relation 補關係型或多跳問題。 | IFRS17 因 `IFRS 17` hub entity 太強，Graph 反而下降到 `68.0%`。 |
| RRF Merge | 合併多個 retrieval branch 的候選。 | merge 權重要測，否則 graph noise 會被放大。 |
| Graph Hub Guard | 壓低泛用 hub entity 造成的噪音。 | IFRS17 demo 中把這個做成 Full stack lab 的明確節點。 |
| Evidence Quality Gate | 降低目錄頁、封面頁或弱 evidence chunk。 | 專業文件中 evidence quality 比單純相似度更重要。 |

## IFRS17 實驗結果

Run ID: `full-ifrs17-20260704`

Benchmark: `IFRS 17 Mixed100`

Scope: retrieval only，不呼叫 QA Agent。

| Variant | Retrieval score | Perfect questions | Avg total time | P95 total time |
| --- | ---: | ---: | ---: | ---: |
| BM25-only | `443/500 = 88.6%` | `70/100` | `0.2719s` | `0.3612s` |
| BM25 + Dense | `448/500 = 89.6%` | `70/100` | `0.3659s` | `0.3835s` |
| BM25 + Dense + Graph | `340/500 = 68.0%` | `50/100` | `0.2954s` | `0.3776s` |
| Full project stack | `245/500 = 49.0%` | `31/100` | `0.7298s` | `1.2930s` |

### IFRS17 的重要結論

1. IFRS17 專業文件的 BM25 baseline 很強，因為問題常命中特定專業詞、準則名、會計概念。
2. Dense 有小幅提升，但不是壓倒性提升。
3. Graph 在這個設定下變差，不是因為 graph 建置壞掉，而是 retrieval policy 太容易命中 `IFRS 17` 這種泛用 hub entity。
4. Full stack 不是從三體直接搬過來就會更好。跨資料庫時，需要重新調 metadata、graph gating、merge weight、evidence quality。

Graph validation 結果：

- Entities: `96`
- Relations: `25`
- Support refs: `125`
- Missing support refs: `0`
- Relations with valid support: `25/25`
- Chunk count: `1,190`

也就是說，這是一個很有價值的 negative result：Graph 表本身可以是乾淨的，但 Graph Retrieval 仍然可能因為 gating / merge 設計不精準而傷害結果。

這也代表問題不在 latency。IFRS17 run 裡 Graph retrieval 平均約 `0.001s`，速度很快，但正確率仍從 BM25 + Dense 的 `89.6%` 降到 `68.0%`。所以 Graph 的關鍵不是「查得快不快」，而是「什麼 entity 可以觸發 graph expansion」、「哪些 relation 可以進 Top K」、「graph candidate 要不要被 boost」。

## Graph suitability 研究

IFRS17 告訴我們 Graph 可能變差，但不能因此說 Graph 沒用。因此專案另外做了一組合成但可控的 benchmark，專門隔離「資料型態」這個因素。

完整報告：[graph_rag_suitability_report.md](graph_rag_suitability_report.md)

| Data type | Graph 效果 | 建議 |
| --- | --- | --- |
| 關聯型個案資料庫 | `38.9% -> 100.0%` | 適合 Graph，尤其是 claimant -> policy -> rider 這類多跳 entity relation 問題。 |
| 交叉引用手冊/法規資料庫 | `38.9% -> 100.0%` | 適合 Graph，尤其是 workflow -> section -> exception 這類引用鏈。 |
| 平面 FAQ / 單段答案資料庫 | BM25 已 `100.0%` | 不優先 Graph，先用 BM25 / Dense / metadata filter。 |
| 單一大主題 / hub-heavy 資料庫 | Graph-priority merge 掉到 `25.0%` | 條件式適合，必須排除泛用 hub 並控制 graph merge 權重。 |

### Graph 的實務判斷規則

| 問題 | 建議 |
| --- | --- |
| 答案是否通常在單一 chunk？ | 先用 BM25 + Dense，不要急著 Graph。 |
| 是否需要從 A 找到 B，再從 B 找到 C？ | Graph 值得進候選方案。 |
| 資料是否有穩定 ID、entity、relation、foreign key、引用關係？ | Graph 成本較合理。 |
| 是否存在大量泛用 hub entity？ | Graph 需要 hub suppression / precise gating。 |
| 是否是統計聚合、排序、總額計算？ | 優先 SQL / OLAP，不是 Graph RAG。 |

## 三體 RAG 作為補充案例

三體 RAG 不是這個 repo 的主體，但它提供另一個資料型態的證據：小說文本、人物、事件、專名、遠離原文措辭的自然語言問題。

三體 Mixed200 retrieval-only incremental test：

| Stage | Retrieval Upper Bound | Avg Total s | 結論 |
| --- | ---: | ---: | --- |
| BM25-only | `71.1%` | `0.160s` | lexical baseline 已可用，但對自然語言混合題不足。 |
| BM25 + Dense | `82.7%` | `0.227s` | Dense 對改寫題、長句題有明確幫助。 |
| BM25 + Dense + Graph | `79.3%` | `0.183s` | Graph 有觸發，但 merge 把錯誤關係 chunk 推進 Top 8。 |
| Full project stack | `82.6%` | `0.315s` | 詞表、rerank、parent expansion 等技術補回分數。 |

三體檢索詞表實驗：

| Dataset | Retrieval Upper Bound |
| --- | ---: |
| Mixed 200 原版 | `73.6%` |
| Mixed 200 附檢索詞表 | `87.6%` |

這組結果可以補充 IFRS17 的觀察：

1. Hybrid retrieval 對自然語言問題有幫助。
2. KB-aware 詞表能補足「使用者說法」與「KB 原文詞彙」之間的落差。
3. Graph 不是必然加分；如果關係抽取或 merge policy 不精準，Graph 會把錯誤上下文推進 Top K。

## 三個實驗放在一起看

| 資料型態 | 最重要觀察 | 對 RAG 架構的啟示 |
| --- | --- | --- |
| IFRS17 專業文件 | BM25 + Dense 最穩，Graph 被 hub entity 污染。 | 專業文件要重視 metadata、evidence quality、hub suppression。 |
| Graph suitability benchmark | 關聯型與交叉引用資料 Graph 從 `38.9%` 拉到 `100.0%`。 | Graph 適合多跳關係，不適合平面 FAQ。 |
| 三體小說文本 | Dense 與詞表很有幫助，Graph 不一定加分。 | 自然語言 KB 要處理詞彙落差，Graph merge 要保守。 |

## Graph RAG 不是預設升級

這個專案刻意保留 Graph 變差的結果，因為它比只展示成功案例更有工程價值。

Graph 比較適合當條件式 candidate branch：當問題真的需要 entity relation、多跳關係或交叉引用時才啟用；如果只是因為問題裡出現 `IFRS 17` 這種泛用 entity 就擴展整張圖，Graph 會變成噪音放大器。

比較安全的方向是：

1. hub suppression：降低 `IFRS 17`、產品名、公司名這類泛用 hub 的權重。
2. relation gating：只有特定 relation type 可以把 chunk 帶進候選集合。
3. Graph as candidate, not boost：Graph 可以補 recall，但不應該無條件提高排名。
4. per-domain benchmark：三體調好的 stack 不能直接套到 IFRS17，每個 KB 都要重測。

## 專案展示重點

如果要拿這個專案做面試或作品集，我會把重點放在這幾點：

1. 我沒有只做一個聊天機器人，而是把 RAG 拆成可測的 retrieval pipeline。
2. 我用 `BM25-only -> BM25 + Dense -> BM25 + Dense + Graph -> Full stack` 做 incremental evaluation。
3. 我保留了 Graph 變差的結果，因為 negative result 能說明架構限制。
4. 我另外設計 Graph suitability benchmark，回答 Graph 到底適合什麼資料庫。
5. 我用三體 RAG 當跨資料型態案例，證明同一套 RAG 技術在不同 KB 上效果不同。
6. 我做了 GitHub Pages demo，讓別人可以直接互動看 evidence retrieval，而不是只看報告。

## Demo 與文件入口

- GitHub Pages 首頁：[https://ryan1998-0.github.io/IFRS17-RAG/](https://ryan1998-0.github.io/IFRS17-RAG/)
- IFRS17 互動 Demo：[https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/](https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/)
- 中文 README：[README.zh-TW.md](https://github.com/Ryan1998-0/IFRS17-RAG/blob/main/README.zh-TW.md)
- IFRS17 結果摘要：[results_summary.md](results_summary.md)
- Graph suitability 報告：[graph_rag_suitability_report.md](graph_rag_suitability_report.md)

## 限制

- 公開 GitHub Pages demo 是靜態版本，不包含本地 Ollama Agent backend。
- Demo 的 Dense branch 是 browser-side dense proxy / alias expansion，不是雲端 embedding service。
- 本 repo 不提供會計建議，也不應被視為 IFRS 合規依據。
- Graph suitability benchmark 是合成但可控的 benchmark，目的是隔離資料型態，不代表所有企業資料庫都會得到相同分數。
