import {
  buildSearchIndex,
  composeChineseRetrievalAnswer,
  expandQueryWithAliases,
  runRetrieval,
  searchGraph,
} from "../retrieval-core.js?v=variant-architecture-1";
import {
  buildAgentQueryPayload,
  callAgentEndpoint,
  readAgentEndpoint,
  saveAgentEndpoint,
} from "../agent-client.js?v=variant-architecture-1";

const state = {
  data: null,
  index: null,
  query: "IFRS17 的目的是什麼？",
  variant: "bm25_dense",
  agentEndpoint: "",
  latestResult: null,
  agentRequestId: 0,
};

const elements = {
  dataStatus: document.querySelector("#dataStatus"),
  dataMeta: document.querySelector("#dataMeta"),
  form: document.querySelector("#searchForm"),
  input: document.querySelector("#queryInput"),
  chips: document.querySelector("#questionChips"),
  metrics: document.querySelector("#metrics"),
  variantDetails: document.querySelector("#variantDetails"),
  results: document.querySelector("#results"),
  resultTitle: document.querySelector("#resultTitle"),
  confidence: document.querySelector("#confidenceBadge"),
  agentEndpoint: document.querySelector("#agentEndpointInput"),
  saveAgentEndpoint: document.querySelector("#saveAgentEndpoint"),
  askAgent: document.querySelector("#askAgentButton"),
  agentAnswer: document.querySelector("#agentAnswerPanel"),
  answer: document.querySelector("#answerPanel"),
  comparison: document.querySelector("#comparisonPanel"),
  graphPanel: document.querySelector("#graphPanel"),
  pipeline: document.querySelector("#pipeline"),
};

const demoQueries = [
  "IFRS17 的目的是什麼？",
  "IFRS17 適用哪些合約？",
  "保險合約在 IFRS17 中怎麼定義？",
  "合約服務邊際 CSM 代表什麼？",
  "什麼時候可以使用保費分攤法 PAA？",
  "持有的再保險合約要怎麼處理？",
  "舊制 IFRS 4 和新制 IFRS 17 差在哪？",
];

init();

async function init() {
  bindEvents();
  renderChips();
  state.agentEndpoint = readAgentEndpoint();
  elements.agentEndpoint.value = state.agentEndpoint;
  renderAgentIdle();
  const response = await fetch("./data/ifrs17_demo_data.json");
  state.data = await response.json();
  state.index = buildSearchIndex(state.data.chunks);
  elements.dataStatus.textContent = "IFRS17 profile loaded";
  elements.dataMeta.textContent = `${state.data.meta.chunk_count} chunks · ${state.data.meta.alias_count} aliases · ${state.data.meta.graph_relation_count} graph relations`;
  elements.input.value = state.query;
  runSearch({ askAgent: Boolean(state.agentEndpoint) });
}

function bindEvents() {
  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.query = elements.input.value.trim();
    runSearch({ askAgent: true });
  });

  document.querySelectorAll("input[name='variant']").forEach((input) => {
    input.addEventListener("change", () => {
      state.variant = input.value;
      runSearch();
    });
  });

  elements.saveAgentEndpoint.addEventListener("click", () => {
    state.agentEndpoint = saveAgentEndpoint(elements.agentEndpoint.value);
    renderAgentIdle();
  });

  elements.askAgent.addEventListener("click", () => {
    if (state.latestResult) askLiveAgent(state.latestResult);
  });
}

function renderChips() {
  elements.chips.innerHTML = "";
  for (const query of demoQueries) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = query;
    button.addEventListener("click", () => {
      state.query = query;
      elements.input.value = query;
      runSearch({ askAgent: Boolean(state.agentEndpoint) });
    });
    elements.chips.append(button);
  }
}

function runSearch(options = {}) {
  if (!state.data || !state.query) return;
  const result = runRetrieval({
    query: state.query,
    chunks: state.data.chunks,
    aliases: state.data.aliases,
    graph: state.data.graph,
    variant: state.variant,
    topK: 8,
    index: state.index,
  });
  state.latestResult = result;
  const retrievalQuery = result.retrievalQuery || state.query;
  const graphResult = searchGraph(retrievalQuery, state.data.graph, state.data.chunks);
  const expanded = expandQueryWithAliases(retrievalQuery, state.data.aliases);
  const answer = composeChineseRetrievalAnswer(result);

  renderMetrics(result, expanded);
  renderVariantDetails(result.variant);
  renderAgentIdle();
  renderAnswer(answer, result);
  renderComparisonGraph(result.comparisonGraph);
  renderResults(result, expanded);
  renderGraph(graphResult);
  renderPipeline(result);
  if (options.askAgent) askLiveAgent(result);
}

async function askLiveAgent(result) {
  if (!state.agentEndpoint) {
    renderAgentMessage({
      status: "offline",
      title: "Live Agent 未連線",
      message: "設定 Agent endpoint 後，這裡會呼叫後端 Agent 重新檢索 IFRS17 KB 並生成回答。",
    });
    return;
  }

  const requestId = ++state.agentRequestId;
  elements.askAgent.disabled = true;
  renderAgentMessage({
    status: "pending",
    title: "Live Agent 正在回答",
    message: "Agent API 正在執行 IFRS17 retrieval，並把 evidence 交給開源模型回答。",
  });

  try {
    const payload = buildAgentQueryPayload({
      question: result.query,
      variant: result.variant,
      topK: result.contexts.length || 8,
    });
    const response = await callAgentEndpoint(state.agentEndpoint, payload);
    if (requestId !== state.agentRequestId) return;
    renderAgentResponse(response);
  } catch (error) {
    if (requestId !== state.agentRequestId) return;
    renderAgentMessage({
      status: "error",
      title: "Live Agent 呼叫失敗",
      message: error instanceof Error ? error.message : String(error),
    });
  } finally {
    if (requestId === state.agentRequestId) elements.askAgent.disabled = false;
  }
}

function renderMetrics(result, expanded) {
  elements.resultTitle.textContent = `Evidence for: ${state.query}`;
  elements.confidence.textContent = `Retrieval confidence: ${titleCase(result.confidence)}`;
  elements.confidence.className = `confidence confidence-${result.confidence}`;
  elements.metrics.innerHTML = "";
  const metrics = [
    ["Variant", labelForVariant(result.variant)],
    ["Contexts", result.contexts.length],
    ["Total time", `${result.timings.totalMs.toFixed(2)} ms`],
    ["Translation", result.translation.detectedLanguage === "zh-TW" ? "中文 -> IFRS17" : "Direct"],
    ["Alias hits", expanded.matchedAliases.length],
  ];
  for (const [label, value] of metrics) {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `<span>${label}</span><strong>${escapeHtml(String(value))}</strong>`;
    elements.metrics.append(item);
  }
}

function renderVariantDetails(variant) {
  const detail = architectureForVariant(variant);
  elements.variantDetails.innerHTML = `
    <div>
      <p class="eyebrow">Architecture</p>
      <h3>${escapeHtml(detail.label)}</h3>
    </div>
    <p>${escapeHtml(detail.summary)}</p>
    <div class="architecture-steps">
      ${detail.steps.map((step) => `<span>${escapeHtml(step)}</span>`).join("")}
    </div>
  `;
}

function renderAnswer(answer, result) {
  const terms = result.translation.addedTerms || [];
  const citations = answer.citations || [];
  elements.answer.innerHTML = `
    <div class="answer-head">
      <div>
        <p class="eyebrow">Translation Agent</p>
        <h3>中文回答</h3>
      </div>
      <span>${escapeHtml(answer.confidence || "medium")}</span>
    </div>
    <p>${escapeHtml(answer.text)}</p>
    ${
      terms.length
        ? `<p class="answer-terms">檢索詞：${terms.slice(0, 10).map(escapeHtml).join("、")}</p>`
        : ""
    }
    ${
      citations.length
        ? `<ul>${citations
            .map(
              (citation) =>
                `<li>來源 ${citation.rank}: ${escapeHtml(formatCitation(citation))}</li>`,
            )
            .join("")}</ul>`
        : ""
    }
  `;
}

function renderAgentIdle() {
  elements.askAgent.disabled = false;
  renderAgentMessage({
    status: state.agentEndpoint ? "ready" : "offline",
    title: state.agentEndpoint ? "Live Agent 已設定" : "Live Agent 未連線",
    message: state.agentEndpoint
      ? "按下 Ask Agent 會呼叫 endpoint，由後端 Agent 重新檢索 IFRS17 KB 並生成中文回答。"
      : "這個區塊只在設定 Agent endpoint 後呼叫模型；未設定時不會用模板回答冒充 Agent。",
  });
}

function renderAgentMessage({ status, title, message }) {
  elements.agentAnswer.className = `agent-answer-panel agent-${status}`;
  elements.agentAnswer.innerHTML = `
    <div class="answer-head">
      <div>
        <p class="eyebrow">Live Agent</p>
        <h3>${escapeHtml(title)}</h3>
      </div>
      <span>${escapeHtml(status)}</span>
    </div>
    <p>${escapeHtml(message)}</p>
  `;
}

function renderAgentResponse(response) {
  const model = `${response.model.provider || "model"}:${response.model.name || "unknown"}`;
  const citations = response.citations || [];
  const warnings = response.groundingWarnings || [];
  const totalMs = response.timings?.total_ms || response.timings?.totalMs;
  elements.agentAnswer.className = "agent-answer-panel agent-success";
  elements.agentAnswer.innerHTML = `
    <div class="answer-head">
      <div>
        <p class="eyebrow">Live Agent</p>
        <h3>Agent 回答</h3>
      </div>
      <span>${escapeHtml(model)}</span>
    </div>
    <p>${escapeHtml(response.answer)}</p>
    ${
      citations.length
        ? `<ul>${citations
            .map((citation) => `<li>來源 ${citation.rank}: ${escapeHtml(formatCitation(citation))}</li>`)
            .join("")}</ul>`
        : ""
    }
    <p class="answer-terms">
      ${totalMs != null ? `Agent total ${Number(totalMs).toFixed(0)} ms` : "Agent timing unavailable"}
      ${warnings.length ? ` · warnings: ${warnings.map(escapeHtml).join(", ")}` : ""}
    </p>
  `;
}

function renderResults(result, expanded) {
  elements.results.innerHTML = "";
  if (!result.contexts.length) {
    elements.results.innerHTML =
      '<div class="empty">No evidence found. Try a more specific IFRS17 term.</div>';
    return;
  }

  for (const context of result.contexts) {
    const card = document.createElement("article");
    card.className = "result-card";
    const source = sourceFor(context.source);
    const terms = [
      ...new Set([
        ...(result.translation.addedTerms || []),
        ...expanded.matchedAliases.flatMap((item) => [item.canonical, ...(item.aliases || [])]),
        ...(context.matchedTerms || []),
      ]),
    ].slice(0, 8);
    const excerpt = evidenceSnippet(context.content, terms);
    card.innerHTML = `
      <header>
        <span class="rank">#${context.rank}</span>
        <div>
          <h3>${escapeHtml(context.title)}</h3>
          <p>${escapeHtml(source?.name || context.source)} · ${escapeHtml(context.page || "chunk")}</p>
        </div>
      </header>
      <div class="tags">
        <span>${escapeHtml(context.branch || "merged")}</span>
        <span>score ${context.score}</span>
        ${source?.source_type ? `<span>${escapeHtml(source.source_type)}</span>` : ""}
      </div>
      <p class="excerpt">${highlight(escapeHtml(excerpt), terms)}</p>
      ${terms.length ? `<p class="terms">Matched: ${terms.map(escapeHtml).join(", ")}</p>` : ""}
    `;
    elements.results.append(card);
  }
}

function renderComparisonGraph(comparisonGraph) {
  if (!comparisonGraph) {
    elements.comparison.hidden = true;
    elements.comparison.innerHTML = "";
    return;
  }

  elements.comparison.hidden = false;
  elements.comparison.innerHTML = `
    <div class="comparison-head">
      <div>
        <p class="eyebrow">Graph table</p>
        <h3>${escapeHtml(comparisonGraph.title)}</h3>
      </div>
      <span>${comparisonGraph.nodes.length} nodes · ${comparisonGraph.edges.length} edges</span>
    </div>
    <p class="comparison-summary">${escapeHtml(comparisonGraph.summary)}</p>
    <div class="comparison-table-wrap">
      <table class="comparison-table">
        <thead>
          <tr>
            <th>比較面向</th>
            <th>舊制 IFRS 4</th>
            <th>新制 IFRS 17</th>
            <th>影響</th>
            <th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          ${comparisonGraph.rows.map(renderComparisonRow).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderComparisonRow(row) {
  const evidence = row.evidence
    .slice(0, 2)
    .map((item) => formatCitation(item))
    .join("；");
  return `
    <tr>
      <th scope="row">${escapeHtml(row.aspect)}</th>
      <td>${escapeHtml(row.oldPolicy)}</td>
      <td>${escapeHtml(row.newPolicy)}</td>
      <td>${escapeHtml(row.impact)}</td>
      <td>${escapeHtml(evidence || "No linked chunk")}</td>
    </tr>
  `;
}

function renderGraph(graphResult) {
  const names = graphResult.matchedEntities.map((entity) => entity.name).slice(0, 12);
  const relations = graphResult.results
    .flatMap((item) => item.relations || [])
    .slice(0, 8);
  elements.graphPanel.innerHTML = "";
  if (graphResult.hubWarning) {
    const warning = document.createElement("div");
    warning.className = "warning";
    warning.textContent =
      "Broad graph match detected. IFRS17 hub entities can pull unrelated chunks, so use ranked text evidence first.";
    elements.graphPanel.append(warning);
  }
  const entityBlock = document.createElement("div");
  entityBlock.className = "graph-block";
  entityBlock.innerHTML = `
    <h3>Matched entities</h3>
    <p>${names.length ? names.map(escapeHtml).join(", ") : "No graph entity match."}</p>
  `;
  elements.graphPanel.append(entityBlock);

  const relationBlock = document.createElement("div");
  relationBlock.className = "graph-block";
  relationBlock.innerHTML = `
    <h3>Relation support</h3>
    <ul>${relations.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>No relation support found.</li>"}</ul>
  `;
  elements.graphPanel.append(relationBlock);
}

function renderPipeline(result) {
  elements.pipeline.innerHTML = "";
  for (const step of result.pipeline) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${escapeHtml(step.name)}</strong><span>${escapeHtml(step.detail)}</span>`;
    elements.pipeline.append(li);
  }
}

function sourceFor(sourceId) {
  return state.data.sources.find((source) => source.source_id === sourceId);
}

function labelForVariant(variant) {
  return {
    bm25: "BM25-only",
    dense: "Dense proxy",
    bm25_dense: "BM25 + Dense",
    bm25_dense_graph: "BM25 + Dense + Graph",
    full: "Full stack lab",
  }[variant] || variant;
}

function architectureForVariant(variant) {
  const architectures = {
    bm25: {
      label: "BM25-only",
      summary: "Lexical baseline. It ranks chunks by keyword/token overlap with the IFRS17 question.",
      steps: ["BM25", "Top K evidence"],
    },
    bm25_dense: {
      label: "BM25 + Dense",
      summary:
        "Hybrid retrieval. The public static demo uses an alias-expanded dense proxy because no embedding model runs in GitHub Pages.",
      steps: ["BM25", "Dense proxy / Alias expansion", "RRF Merge", "Top K evidence"],
    },
    bm25_dense_graph: {
      label: "BM25 + Dense + Graph",
      summary:
        "Adds graph relation support to the BM25 + Dense candidates, then merges the three retrieval branches.",
      steps: ["BM25", "Dense proxy / Alias expansion", "Graph Retrieval", "RRF Merge", "Top K evidence"],
    },
    full: {
      label: "Full stack lab",
      summary:
        "The complete static lab path. It keeps the IFRS17 profile filter, merges lexical/dense/graph evidence, suppresses broad hub graph matches, and applies evidence quality rules.",
      steps: [
        "Translation Agent",
        "Metadata Filter",
        "BM25",
        "Dense proxy / Alias expansion",
        "Graph Retrieval",
        "RRF Merge",
        "Graph Hub Guard",
        "Evidence Quality Gate",
        "Comparison Graph when relevant",
      ],
    },
  };

  return architectures[variant] || architectures.full;
}

function titleCase(value) {
  return value.slice(0, 1).toUpperCase() + value.slice(1);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char],
  );
}

function highlight(html, terms) {
  let output = html;
  const safeTerms = terms
    .filter((term) => String(term).length > 2)
    .sort((a, b) => String(b).length - String(a).length)
    .slice(0, 8);
  for (const term of safeTerms) {
    const pattern = new RegExp(`(${escapeRegex(escapeHtml(term))})`, "ig");
    output = output.replace(pattern, "<mark>$1</mark>");
  }
  return output;
}

function escapeRegex(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function evidenceSnippet(content, terms, maxLength = 760) {
  const text = String(content || "").replace(/\s+/g, " ").trim();
  const lower = text.toLowerCase();
  const strongTerms = terms
    .map((term) => String(term).toLowerCase())
    .filter(
      (term) =>
        term.length >= 8 &&
        !["ifrs 17", "insurance contract", "insurance contracts"].includes(term),
    )
    .sort((a, b) => b.length - a.length);
  const firstHit = strongTerms
    .map((term) => lower.indexOf(term))
    .filter((index) => index >= 0)
    .sort((a, b) => a - b)[0];
  if (firstHit == null || firstHit <= 140) return text.slice(0, maxLength);

  const start = Math.max(0, firstHit - 120);
  const cleanStart = text.indexOf(" ", start);
  return `...${text.slice(cleanStart > 0 ? cleanStart + 1 : start, cleanStart + maxLength)}`;
}

function formatCitation(citation) {
  const title = citation.title || "Untitled source";
  if (!citation.page || title.toLowerCase().includes(String(citation.page).toLowerCase())) {
    return title;
  }
  return `${title} / ${citation.page}`;
}
