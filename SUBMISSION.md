# Interview Code Submission

## 選擇題目

我選擇提交「問答 AI Agent 實作」。

題目要求是試想一個商業情境，建立一個 Agent（配合 RAG）服務，使用 Python，建立小型文件庫，並自由選擇進階能力。

## 商業情境

本專案的情境是「專業文件問答 Agent」。

使用者可以針對 IFRS 17 相關文件提出中文或英文問題，系統會先從 knowledge base 檢索 evidence，再根據檢索結果提供 grounded answer 或展示可支撐答案的來源片段。

這類情境可對應到保險、會計、金融、法遵或企業內部知識庫客服。

## 為什麼適合作為程式題提交

這個專案適合提交，原因如下：

- 使用 Python 建立 RAG pipeline。
- 建立 IFRS 17 profile 作為小型文件庫。
- 支援 BM25-only、BM25 + Dense、BM25 + Dense + Graph、Full stack lab 的 retrieval variant。
- 包含 Query Rewrite / Translation、Metadata Filter、BM25、Dense Retrieval、Graph Retrieval、RRF Merge、Reranker、Parent Chunk Expansion、Evidence Quality Gate / Verifier、QA Agent。
- 有可重現的 retrieval benchmark 與 100 題混合題。
- 有 GitHub Pages 互動 Demo，可以直接測試 browser-side retrieval。
- 有本機 Agent endpoint / QA Agent 相關程式碼，可接本機 LLM。

## 對應題目要求

| 題目要求 | 本專案對應 |
| --- | --- |
| 使用 Python | `rag_demo/`、`evals/`、`scripts/` 使用 Python 實作 RAG pipeline 與 benchmark。 |
| 建立小型文件庫 | `profiles/ifrs17/` 保存 IFRS 17 profile、manifest、alias、graph schema。 |
| Agent 配合 RAG | `rag_demo/query.py`、`rag_demo/qa_agent.py`、`rag_demo/retrieval_verifier.py` 串接 retrieval、verifier、QA Agent。 |
| 進階 RAG | 支援 Hybrid RAG、Graph Retrieval、RRF Merge、Reranker、Parent Chunk Expansion、Evidence Quality Gate。 |
| 可互動展示 | `docs/ifrs17-demo/` 提供 GitHub Pages Demo。 |
| 評估與實驗 | `evals/ifrs17_retrieval/` 提供 100 題 mixed benchmark 與 incremental retrieval evaluation。 |

## Demo 與 Repo

- GitHub Repo: <https://github.com/Ryan1998-0/IFRS17-RAG>
- Online Demo: <https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/>
- 中文專案整理: [README.zh-TW.md](README.zh-TW.md)
- 完整專案說明: [docs/project_overview_zh.md](docs/project_overview_zh.md)

## 使用資源方式

本作業使用以下資源輔助完成：

- LLM / Codex：協助整理題目需求、檢查程式架構、補充提交說明與文件。
- GitHub：保存程式碼、文件與 Demo。
- GitHub Pages：部署互動式 Demo。
- 公開 IFRS 17 文件：作為 RAG knowledge base 的資料來源。
- 本機 Python 環境：執行 retrieval benchmark、資料處理與測試。

## 目前限制

- 公開 Demo 使用 browser-side retrieval 與 sanitized demo data，不打包 IFRS Foundation PDF 原文、完整抽取文字、embedding index 或 raw logs。
- 公開 Demo 可以展示 retrieval pipeline 與 evidence，但不是雲端付費 LLM 生成服務。
- 若要實際呼叫本機 LLM QA Agent，需要在本機啟動 Agent endpoint，並設定對應模型，例如 Ollama。
- 本專案不提供會計、保險、法遵或 IFRS 合規建議，只作為 RAG 架構與檢索評估展示。

## 建議提交說明

```text
我選擇第二部分的「問答 AI Agent 實作」。

我實作的是 IFRS17 RAG 問答 Agent，情境是專業文件問答服務。專案使用 Python 建立 RAG pipeline，並建立 IFRS17 小型 knowledge base。架構包含 BM25、Dense Retrieval、Graph Retrieval、RRF Merge、Reranker、Parent Chunk Expansion、Evidence Quality Gate / Verifier 與 QA Agent。

GitHub:
https://github.com/Ryan1998-0/IFRS17-RAG

Demo:
https://ryan1998-0.github.io/IFRS17-RAG/ifrs17-demo/
```
