import {
  buildSearchIndex,
  composeChineseRetrievalAnswer,
  expandQueryWithAliases,
  runRetrieval,
  searchGraph,
} from "../retrieval-core.js?v=kb-model-select-2";
import {
  buildAgentQueryPayload,
  callAgentEndpoint,
  readAgentEndpoint,
  saveAgentEndpoint,
} from "../agent-client.js?v=kb-model-select-2";

const knowledgeBases = {
  ifrs17: {
    label: "IFRS17",
    profile: "ifrs17",
    dataUrl: "./data/ifrs17_demo_data.json",
    staticRetrieval: true,
    defaultQuery: "IFRS17 的目的是什麼？",
    queries: [
      "IFRS17 的目的是什麼？",
      "IFRS17 適用哪些合約？",
      "保險合約在 IFRS17 中怎麼定義？",
      "合約服務邊際 CSM 代表什麼？",
      "什麼時候可以使用保費分攤法 PAA？",
      "持有的再保險合約要怎麼處理？",
      "舊制 IFRS 4 和新制 IFRS 17 差在哪？",
    ],
  },
  three_body_trilogy: {
    label: "三體",
    profile: "three_body_trilogy",
    staticRetrieval: false,
    defaultQuery: "葉文潔和紅岸基地是什麼關係？",
    queries: [
      "葉文潔和紅岸基地是什麼關係？",
      "黑暗森林法則是什麼？",
      "三體人為什麼害怕地球科技爆炸？",
      "羅輯成為執劍人的原因是什麼？",
      "智子在故事中扮演什麼角色？",
    ],
  },
};

const qaModels = {
  "ollama:qwen2.5:7b": { provider: "ollama", name: "qwen2.5:7b", label: "Ollama qwen2.5:7b" },
  "ollama:llama3.1:8b": { provider: "ollama", name: "llama3.1:8b", label: "Ollama llama3.1:8b" },
  "ollama:mistral:7b": { provider: "ollama", name: "mistral:7b", label: "Ollama mistral:7b" },
  "backend:default": { provider: "backend", name: "default", label: "Backend default" },
};

const state = {
  data: null,
  index: null,
  profile: "ifrs17",
  qaModel: "ollama:qwen2.5:7b",
  query: "IFRS17 的目的是什麼？",
  variant: "bm25_dense",
  agentEndpoint: "",
  latestResult: null,
  agentRequestId: 0,
  pendingProfile: "",
};

const elements = {
  dataStatus: document.querySelector("#dataStatus"),
  dataMeta: document.querySelector("#dataMeta"),
  form: document.querySelector("#searchForm"),
  input: document.querySelector("#queryInput"),
  knowledgeBase: document.querySelector("#knowledgeBaseSelect"),
  qaModel: document.querySelector("#qaModelSelect"),
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

init();

async function init() {
  bindEvents();
  elements.knowledgeBase.value = state.profile;
  elements.qaModel.value = state.qaModel;
  renderChips();
  state.agentEndpoint = readAgentEndpoint();
  elements.agentEndpoint.value = state.agentEndpoint;
  renderAgentIdle();
  await loadKnowledgeBase(state.profile, { askAgent: Boolean(state.agentEndpoint) });
  startControlWatcher();
}

function bindEvents() {
  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    state.query = elements.input.value.trim();
    if (currentKnowledgeBase().staticRetrieval) runSearch({ askAgent: true });
    else askLiveAgent();
  });

  const handleKnowledgeBaseChange = async () => {
    await loadKnowledgeBase(elements.knowledgeBase.value);
  };
  elements.knowledgeBase.addEventListener("change", handleKnowledgeBaseChange);
  elements.knowledgeBase.addEventListener("input", handleKnowledgeBaseChange);

  const handleQaModelChange = () => {
    state.qaModel = elements.qaModel.value;
    renderAgentIdle();
    if (currentKnowledgeBase().staticRetrieval) runSearch();
    else renderAgentOnlyProfile();
  };
  elements.qaModel.addEventListener("change", handleQaModelChange);
  elements.qaModel.addEventListener("input", handleQaModelChange);

  document.querySelectorAll("input[name='variant']").forEach((input) => {
    input.addEventListener("change", () => {
      state.variant = input.value;
      if (currentKnowledgeBase().staticRetrieval) runSearch();
      else renderAgentOnlyProfile();
    });
  });

  elements.saveAgentEndpoint.addEventListener("click", () => {
    state.agentEndpoint = saveAgentEndpoint(elements.agentEndpoint.value);
    renderAgentIdle();
  });

  elements.askAgent.addEventListener("click", () => {
    askLiveAgent(state.latestResult);
  });
}

function renderChips() {
  elements.chips.innerHTML = "";
  for (const query of currentKnowledgeBase().queries) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = query;
    button.addEventListener("click", () => {
      state.query = query;
      elements.input.value = query;
      if (currentKnowledgeBase().staticRetrieval) runSearch({ askAgent: Boolean(state.agentEndpoint) });
      else askLiveAgent();
    });
    elements.chips.append(button);
  }
}

function startControlWatcher() {
  setInterval(() => {
    const selectedProfile = elements.knowledgeBase?.value;
    if (
      selectedProfile &&
      selectedProfile !== state.profile &&
      selectedProfile !== state.pendingProfile
    ) {
      state.pendingProfile = selectedProfile;
      loadKnowledgeBase(selectedProfile).finally(() => {
        state.pendingProfile = "";
      });
      return;
    }

    const selectedQaModel = elements.qaModel?.value;
    if (selectedQaModel && selectedQaModel !== state.qaModel) {
      state.qaModel = selectedQaModel;
      renderAgentIdle();
      if (currentKnowledgeBase().staticRetrieval) runSearch();
      else renderAgentOnlyProfile();
    }
  }, 300);
}

async function loadKnowledgeBase(profile, options = {}) {
  const config = knowledgeBases[profile] || knowledgeBases.ifrs17;
  state.profile = config.profile;
  state.query = config.defaultQuery;
  state.latestResult = null;
  elements.knowledgeBase.value = state.profile;
  elements.input.value = state.query;
  renderChips();
  renderAgentIdle();

  if (!config.staticRetrieval) {
    state.data = null;
    state.index = null;
    renderAgentOnlyProfile();
    if (options.askAgent) askLiveAgent();
    return;
  }

  elements.dataStatus.textContent = `${config.label} profile loading...`;
  elements.dataMeta.textContent = "Static GitHub Pages build";
  const response = await fetch(config.dataUrl);
  state.data = await response.json();
  state.index = buildSearchIndex(state.data.chunks);
  elements.dataStatus.textContent = `${config.label} profile loaded`;
  elements.dataMeta.textContent = `${state.data.meta.chunk_count} chunks · ${state.data.meta.alias_count} aliases · ${state.data.meta.graph_relation_count} graph relations`;
  runSearch({ askAgent: options.askAgent });
}

function currentKnowledgeBase() {
  return knowledgeBases[state.profile] || knowledgeBases.ifrs17;
}

function selectedModel() {
  state.qaModel = elements.qaModel?.value || state.qaModel;
  return qaModels[state.qaModel] || qaModels["ollama:qwen2.5:7b"];
}

function renderAgentOnlyProfile() {
  const config = currentKnowledgeBase();
  elements.dataStatus.textContent = `${config.label} profile selected`;
  elements.dataMeta.textContent = "Agent endpoint required · static public corpus not bundled";
  elements.resultTitle.textContent = `${config.label} requires an Agent endpoint`;
  elements.confidence.textContent = "Agent-only";
  elements.confidence.className = "confidence confidence-medium";
  elements.metrics.innerHTML = "";
  for (const [label, value] of [
    ["Knowledge base", config.label],
    ["QA LLM", selectedModel().label],
    ["Static retrieval", "Unavailable in public demo"],
    ["Agent payload profile", config.profile],
  ]) {
    const item = document.createElement("div");
    item.className = "metric";
    item.innerHTML = `<span>${label}</span><strong>${escapeHtml(String(value))}</strong>`;
    elements.metrics.append(item);
  }
  renderVariantDetails(state.variant);
  elements.answer.innerHTML = `
    <div class="answer-head">
      <div>
        <p class="eyebrow">Knowledge base</p>
        <h3>${escapeHtml(config.label)} Agent profile</h3>
      </div>
      <span>agent-only</span>
    </div>
    <p>${escapeHtml("公開 GitHub Pages 不打包三體全文。設定 Agent endpoint 後，前端會把 profile 和 QA LLM 一起送到後端，由後端檢索對應 KB 並回答。")}</p>
  `;
  elements.comparison.hidden = true;
  elements.comparison.innerHTML = "";
  elements.results.innerHTML =
    '<div class="empty">This knowledge base is available through the Agent endpoint. Static browser-side retrieval is disabled for this profile.</div>';
  elements.graphPanel.innerHTML = `
    <div class="graph-block">
      <h3>Agent profile</h3>
      <p>${escapeHtml(config.profile)}</p>
    </div>
  `;
  renderPipeline({
    pipeline: [
      { name: "Knowledge Base", detail: `${config.label} selected by the user.` },
      { name: "QA Agent LLM", detail: selectedModel().label },
      { name: "Agent Endpoint", detail: "Backend performs retrieval and generation for this profile." },
    ],
  });
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
      message: `設定 Agent endpoint 後，會用 ${currentKnowledgeBase().label} KB 和 ${selectedModel().label} 重新檢索並回答。`,
    });
    return;
  }

  const requestId = ++state.agentRequestId;
  elements.askAgent.disabled = true;
  renderAgentMessage({
    status: "pending",
    title: "Live Agent 正在回答",
    message: `Agent API 正在執行 ${currentKnowledgeBase().label} retrieval，並把 evidence 交給 ${selectedModel().label} 回答。`,
  });

  try {
    const payload = buildAgentQueryPayload({
      question: result?.query || state.query,
      profile: state.profile,
      model: selectedModel(),
      variant: result?.variant || state.variant,
      topK: result?.contexts?.length || 8,
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
    ["Knowledge base", currentKnowledgeBase().label],
    ["QA LLM", selectedModel().label],
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
      ? `按下 Ask Agent 會呼叫 endpoint，由後端 Agent 檢索 ${currentKnowledgeBase().label} KB，並使用 ${selectedModel().label} 生成中文回答。`
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
        "The complete static lab path. It keeps the IFRS17 profile filter, merges lexical/dense/graph evidence, exposes the rerank phase, suppresses broad hub graph matches, and applies evidence quality rules.",
      steps: [
        "Translation Agent",
        "Metadata Filter",
        "BM25",
        "Dense proxy / Alias expansion",
        "Graph Retrieval",
        "RRF Merge",
        "Reranker",
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
