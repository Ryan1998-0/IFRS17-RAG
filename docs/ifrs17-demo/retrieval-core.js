const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "are",
  "as",
  "at",
  "be",
  "by",
  "for",
  "from",
  "how",
  "if",
  "in",
  "is",
  "it",
  "of",
  "on",
  "or",
  "that",
  "the",
  "to",
  "under",
  "what",
  "when",
  "which",
  "why",
  "with",
]);

const GENERIC_HUBS = new Set(["ifrs 17", "insurance contracts"]);

const IFRS4_IFRS17_COMPARISON_ROWS = [
  {
    id: "standard-status",
    aspect: "準則定位",
    oldPolicy: "IFRS 4 是 interim Standard，主要允許保險公司延續既有會計實務。",
    newPolicy: "IFRS 17 取代 IFRS 4，成為保險合約第一套完整且國際一致的 IFRS 準則。",
    impact: "從暫行過渡制度，轉為完整保險合約會計模型。",
    evidenceIds: [
      "ifrs-17-insurance-contracts.txt::1",
      "ifrs-17-effects-analysis.txt::5",
      "ifrs-17-factsheet.txt::2",
      "ifrs-17-project-summary.txt::4",
    ],
  },
  {
    id: "measurement",
    aspect: "衡量模型",
    oldPolicy: "IFRS 4 不規定保險合約的衡量方式，常依 local GAAP 或既有做法衡量。",
    newPolicy: "IFRS 17 使用 current measurement model，核心包含履約現金流與合約服務邊際。",
    impact: "衡量基礎從分散做法，改為以當期估計、折現率、風險調整與 CSM 為核心。",
    evidenceIds: [
      "ifrs-17-effects-analysis.txt::5",
      "ifrs-17-project-summary.txt::17",
      "ifrs-17-project-summary.txt::5",
      "ifrs-17-effects-analysis.txt::10",
      "ifrs-17-effects-analysis.txt::12",
    ],
  },
  {
    id: "comparability",
    aspect: "可比性",
    oldPolicy: "IFRS 4 下，不同國家、甚至同一集團內，類似保險合約可能使用不同會計政策。",
    newPolicy: "IFRS 17 對所有保險合約提供一致原則，提升公司、合約與產業間的可比性。",
    impact: "分析師和投資人更容易比較保險公司結果與合約表現。",
    evidenceIds: [
      "ifrs-17-effects-analysis.txt::28",
      "ifrs-17-effects-analysis.txt::29",
      "ifrs-17-factsheet.txt::3",
      "ifrs-17-factsheet.txt::4",
    ],
  },
  {
    id: "transparency",
    aspect: "透明度與資訊品質",
    oldPolicy: "舊制下部分保險負債資訊可能未即時反映經濟環境、利率與風險變動。",
    newPolicy: "IFRS 17 提供 obligations、risks、performance 的更新資訊，並提高財報透明度。",
    impact: "使用者更能理解保險合約對財務狀況、風險與未來獲利的影響。",
    evidenceIds: [
      "ifrs-17-effects-analysis.txt::7",
      "ifrs-17-effects-analysis.txt::8",
      "ifrs-17-effects-analysis.txt::20",
      "ifrs-17-project-summary.txt::4",
      "ifrs-17-project-summary.txt::21",
    ],
  },
  {
    id: "profit-recognition",
    aspect: "獲利認列",
    oldPolicy: "IFRS 4 下，投資人較難辨識哪些保險合約組是獲利或虧損，也較難分析趨勢。",
    newPolicy: "IFRS 17 透過 CSM 呈現尚未賺得利潤，並隨保險服務提供逐步認列；虧損組需及時反映。",
    impact: "獲利來源和虧損合約更可被拆解與追蹤。",
    evidenceIds: [
      "ifrs-17-project-summary.txt::2",
      "project-summary-amends-to-ifrs17.txt::3",
      "ifrs-17-effects-analysis.txt::10",
      "ifrs-17-effects-analysis.txt::11",
      "ifrs-17-effects-analysis.txt::12",
    ],
  },
  {
    id: "disclosure",
    aspect: "揭露",
    oldPolicy: "IFRS 4 第一階段重點在揭露，但仍允許多種會計實務延續。",
    newPolicy: "IFRS 17 要求揭露可協助使用者理解認列金額、綜合損益與保險風險。",
    impact: "揭露從補充資訊，進一步支援對金額、判斷與風險的分析。",
    evidenceIds: [
      "ifrs-17-effects-analysis.txt::2",
      "ifrs-17-effects-analysis.txt::3",
      "ifrs-17-effects-analysis.txt::12",
      "ifrs-17-effects-analysis.txt::13",
    ],
  },
];

const CHINESE_RETRIEVAL_CONCEPTS = [
  {
    id: "ifrs4-ifrs17-comparison",
    label: "舊制 IFRS 4 vs 新制 IFRS 17",
    patterns: [
      /舊制/,
      /新制/,
      /IFRS\s*4/i,
      /差異/,
      /比較/,
      /取代/,
      /replaces?\s+IFRS\s*4/i,
    ],
    terms: [
      "IFRS 4",
      "IFRS 17 replaces IFRS 4",
      "interim Standard",
      "comparability",
      "consistent framework",
      "current measurement model",
      "contractual service margin",
      "disclosure",
    ],
    answer:
      "舊制 IFRS 4 是 interim Standard，允許保險公司沿用多種既有會計實務；新制 IFRS 17 取代 IFRS 4，建立一致的保險合約認列、衡量、表達與揭露模型。",
  },
  {
    id: "objective",
    label: "IFRS 17 目的",
    patterns: [/目的/, /目標/, /objective/i],
    terms: [
      "objective",
      "IFRS 17:1",
      "recognition",
      "measurement",
      "presentation",
      "disclosure",
      "insurance contracts",
    ],
    answer:
      "根據檢索到的 IFRS 17 來源，IFRS 17 的目的，是建立保險合約在認列、衡量、表達與揭露上的原則。",
  },
  {
    id: "scope",
    label: "適用範圍",
    patterns: [/範圍/, /適用/, /哪些合約/, /scope/i],
    terms: [
      "scope",
      "IFRS 17:3",
      "insurance contracts issued",
      "reinsurance contracts held",
      "investment contracts with discretionary participation features",
      "DPF",
    ],
    answer:
      "根據檢索到的來源，IFRS 17 的適用範圍包含企業發行的保險合約、持有的再保險合約，以及具有裁量參與特徵的投資合約。",
  },
  {
    id: "definition",
    label: "保險合約定義",
    patterns: [/定義/, /什麼是.*保險合約/, /保險合約.*是什麼/, /insurance contract/i],
    terms: [
      "definition",
      "insurance contract",
      "significant insurance risk",
      "uncertain future event",
      "policyholder",
    ],
    answer:
      "根據檢索到的來源，保險合約的核心是移轉重大保險風險；若不確定的未來事件對保單持有人造成不利影響，發行人需要補償保單持有人。",
  },
  {
    id: "contractual-service-margin",
    label: "合約服務邊際",
    patterns: [/合約服務邊際/, /服務邊際/, /CSM/i, /contractual service margin/i],
    terms: [
      "contractual service margin",
      "CSM",
      "unearned profit",
      "insurance contract group",
      "future service",
    ],
    answer:
      "根據檢索到的來源，合約服務邊際代表保險合約組中尚未賺得的利潤，會隨未來服務提供而逐步認列。",
  },
  {
    id: "premium-allocation-approach",
    label: "保費分攤法",
    patterns: [/保費分攤法/, /PAA/i, /premium allocation/i, /簡化衡量/],
    terms: [
      "premium allocation approach",
      "PAA",
      "coverage period",
      "one year or less",
      "simplification",
    ],
    answer:
      "根據檢索到的來源，保費分攤法是 IFRS 17 的簡化衡量方式，通常用於符合條件的較短期間合約，或衡量結果可合理近似一般模型的情境。",
  },
  {
    id: "reinsurance",
    label: "持有的再保險合約",
    patterns: [/再保險/, /reinsurance/i],
    terms: ["reinsurance contracts held", "IFRS 17:60-70", "reinsurance"],
    answer:
      "根據檢索到的來源，持有的再保險合約在 IFRS 17 下有專門規定，分析時應優先查看 reinsurance contracts held 的相關段落。",
  },
  {
    id: "disclosure",
    label: "揭露",
    patterns: [/揭露/, /disclosure/i],
    terms: ["disclosure", "presentation", "risk", "judgements", "amounts recognized"],
    answer:
      "根據檢索到的來源，IFRS 17 的揭露重點在於讓報表使用者理解保險合約對財務報表認列金額、判斷與風險的影響。",
  },
  {
    id: "measurement",
    label: "衡量",
    patterns: [/衡量/, /measurement/i],
    terms: ["measurement", "fulfilment cash flows", "discount rates", "risk adjustment"],
    answer:
      "根據檢索到的來源，IFRS 17 的衡量會涉及履約現金流、折現率、風險調整與合約服務邊際等要素。",
  },
];

export function tokenize(text = "") {
  return String(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .split(/\s+/)
    .filter((token) => token && !STOP_WORDS.has(token));
}

export function buildSearchIndex(chunks) {
  const documents = chunks.map((chunk) => {
    const text = `${chunk.title || ""} ${chunk.source || ""} ${chunk.page || ""} ${chunk.content || ""}`;
    const tokens = tokenize(text);
    const counts = new Map();
    for (const token of tokens) counts.set(token, (counts.get(token) || 0) + 1);
    return { chunk, tokens, counts, length: tokens.length || 1 };
  });

  const documentFrequency = new Map();
  for (const doc of documents) {
    for (const token of new Set(doc.tokens)) {
      documentFrequency.set(token, (documentFrequency.get(token) || 0) + 1);
    }
  }

  const averageLength =
    documents.reduce((sum, doc) => sum + doc.length, 0) / Math.max(documents.length, 1);

  return { documents, documentFrequency, averageLength, documentCount: documents.length };
}

export function expandQueryWithAliases(query, aliases = []) {
  const queryText = String(query || "");
  const lower = queryText.toLowerCase();
  const queryTokens = new Set(tokenize(queryText));
  const additions = [];
  const matchedAliases = [];

  for (const record of aliases) {
    const primaryTerms = [record.canonical, ...(record.aliases || [])].filter(Boolean);
    const supportTerms = [...(record.related_terms || []), ...(record.triggers || [])].filter(Boolean);

    const matchedPrimary = primaryTerms.some((term) => {
      const termLower = String(term).toLowerCase();
      const termTokens = tokenize(termLower);
      if (lower.includes(termLower)) return true;
      return termTokens.length > 0 && termTokens.every((token) => queryTokens.has(token));
    });

    const matchedSupport = supportTerms.some((term) => {
      const termLower = String(term).toLowerCase();
      return termLower.length > 2 && lower.includes(termLower);
    });

    const matched = matchedPrimary || matchedSupport;
    if (matched) {
      matchedAliases.push(record);
      additions.push(record.canonical, ...(record.aliases || []), ...(record.related_terms || []));
    }
  }

  const uniqueAdditions = [...new Set(additions.filter(Boolean))];
  return {
    originalQuery: queryText,
    expandedQuery: [queryText, ...uniqueAdditions].join(" "),
    matchedAliases,
  };
}

export function normalizeQuestionForRetrieval(query) {
  const originalQuery = String(query || "").trim();
  const detectedLanguage = containsCjk(originalQuery) ? "zh-TW" : "en";
  const matchedConcepts = CHINESE_RETRIEVAL_CONCEPTS.filter((concept) =>
    concept.patterns.some((pattern) => pattern.test(originalQuery)),
  );
  const addedTerms = [
    ...new Set([
      ...ifrs17SpellingTerms(originalQuery),
      ...matchedConcepts.flatMap((concept) => concept.terms),
    ]),
  ];
  const retrievalQuery = [originalQuery, ...addedTerms].filter(Boolean).join(" ");

  return {
    originalQuery,
    detectedLanguage,
    retrievalQuery,
    matchedConcepts: matchedConcepts.map(({ id, label, terms }) => ({ id, label, terms })),
    addedTerms,
  };
}

export function searchBm25(query, chunks, options = {}) {
  const index = options.index || buildSearchIndex(chunks);
  const queryTokens = tokenize(query);
  const k1 = 1.4;
  const b = 0.72;

  const results = index.documents.map((doc) => {
    let score = 0;
    const matchedTerms = [];
    for (const token of queryTokens) {
      const tf = doc.counts.get(token) || 0;
      if (!tf) continue;
      const df = index.documentFrequency.get(token) || 0;
      const idf = Math.log(1 + (index.documentCount - df + 0.5) / (df + 0.5));
      const denominator = tf + k1 * (1 - b + b * (doc.length / index.averageLength));
      score += idf * ((tf * (k1 + 1)) / denominator);
      matchedTerms.push(token);
    }
    score += phraseBoost(query, doc.chunk, queryTokens);
    score *= evidenceQualityMultiplier(doc.chunk);
    return decorateResult(doc.chunk, score, "BM25", matchedTerms);
  });

  return results
    .filter((result) => result.score > 0)
    .sort((a, b) => b.score - a.score || String(a.id).localeCompare(String(b.id)));
}

export function searchDenseProxy(query, chunks, aliases = [], options = {}) {
  const expanded = expandQueryWithAliases(query, aliases);
  return searchBm25(expanded.expandedQuery, chunks, options).map((result) => ({
    ...result,
    branch: "Dense proxy",
    matchedAliases: expanded.matchedAliases.map((item) => item.canonical),
  }));
}

export function searchGraph(query, graph, chunks) {
  const chunkById = new Map(chunks.map((chunk) => [chunk.id, chunk]));
  const queryLower = String(query || "").toLowerCase();
  const queryTokens = new Set(tokenize(query));
  const matchedEntities = [];

  for (const entity of graph?.entities || []) {
    const terms = [entity.name, ...(entity.aliases || [])].filter(Boolean);
    const matched = terms.some((term) => {
      const termLower = String(term).toLowerCase();
      const termTokens = tokenize(termLower);
      if (queryLower.includes(termLower)) return true;
      if (!termTokens.length) return false;
      return termTokens.every((token) => queryTokens.has(token));
    });
    if (matched) matchedEntities.push(entity);
  }

  const matchedIds = new Set(matchedEntities.map((entity) => entity.id));
  const matchedNames = matchedEntities.map((entity) => String(entity.name).toLowerCase());
  const hubWarning = matchedNames.some((name) => GENERIC_HUBS.has(name));
  const onlyGenericHub =
    matchedNames.length > 0 && matchedNames.every((name) => GENERIC_HUBS.has(name));
  const byChunk = new Map();

  for (const relation of graph?.relations || []) {
    if (!matchedIds.has(relation.source) && !matchedIds.has(relation.target)) continue;
    const relationScore = Number(relation.confidence || 0.5) * (onlyGenericHub ? 0.15 : 1);
    for (const chunkId of relation.supporting_chunk_ids || []) {
      const chunk = chunkById.get(chunkId);
      if (!chunk) continue;
      const current = byChunk.get(chunkId) || decorateResult(chunk, 0, "Graph", []);
      current.score += relationScore;
      current.relations = current.relations || [];
      current.relations.push(`${relation.source} ${relation.type} ${relation.target}`);
      byChunk.set(chunkId, current);
    }
  }

  return {
    matchedEntities,
    hubWarning,
    results: [...byChunk.values()].sort(
      (a, b) => b.score - a.score || String(a.id).localeCompare(String(b.id)),
    ),
  };
}

export function buildComparisonGraph(chunks = []) {
  const chunkById = new Map(chunks.map((chunk) => [chunk.id, chunk]));
  const rows = IFRS4_IFRS17_COMPARISON_ROWS.map((row) => ({
    ...row,
    evidence: row.evidenceIds
      .map((id) => chunkById.get(id))
      .filter(Boolean)
      .map((chunk) => ({
        id: chunk.id,
        title: chunk.title || chunk.id,
        source: chunk.source || chunk.source_id || "",
        page: chunk.page || "",
      })),
  }));

  const nodes = [
    { id: "old-ifrs4", label: "舊制 IFRS 4", type: "standard" },
    { id: "new-ifrs17", label: "新制 IFRS 17", type: "standard" },
    ...rows.map((row) => ({ id: `aspect-${row.id}`, label: row.aspect, type: "comparison_aspect" })),
  ];
  const edges = [
    {
      from: "old-ifrs4",
      to: "new-ifrs17",
      type: "REPLACED_BY",
      label: "IFRS 17 replaces IFRS 4",
    },
    ...rows.flatMap((row) => [
      {
        from: "old-ifrs4",
        to: `aspect-${row.id}`,
        type: "OLD_PRACTICE",
        label: row.oldPolicy,
      },
      {
        from: `aspect-${row.id}`,
        to: "new-ifrs17",
        type: "NEW_REQUIREMENT",
        label: row.newPolicy,
      },
    ]),
  ];

  return {
    title: "舊制 IFRS 4 vs 新制 IFRS 17",
    summary:
      "IFRS 17 取代 IFRS 4，重點是把原本分散的保險合約會計實務，改成一致、可比較、以現時衡量為核心的會計模型。",
    nodes,
    edges,
    rows,
  };
}

export function mergeRankings(rankings, weights = {}) {
  const merged = new Map();
  for (const ranking of rankings) {
    const weight = weights[ranking.name] ?? 1;
    ranking.results.forEach((result, index) => {
      const current = merged.get(result.id) || { ...result, score: 0, branches: [] };
      current.score += weight * (1 / (60 + index + 1));
      current.branches.push(result.branch || ranking.name);
      current.matchedTerms = [
        ...new Set([...(current.matchedTerms || []), ...(result.matchedTerms || [])]),
      ];
      current.relations = [...new Set([...(current.relations || []), ...(result.relations || [])])];
      merged.set(result.id, current);
    });
  }

  return [...merged.values()].sort(
    (a, b) => b.score - a.score || String(a.id).localeCompare(String(b.id)),
  );
}

export function runRetrieval({
  query,
  chunks,
  aliases = [],
  graph = { entities: [], relations: [] },
  variant = "full",
  topK = 8,
  index,
}) {
  const started = now();
  const pipeline = [];
  const timings = {};
  const searchIndex = index || buildSearchIndex(chunks);
  const translation = normalizeQuestionForRetrieval(query);
  const retrievalQuery = translation.retrievalQuery;
  const comparisonGraph = isComparisonQuery(translation) ? buildComparisonGraph(chunks) : null;

  if (translation.detectedLanguage === "zh-TW" || translation.addedTerms.length) {
    pipeline.push({
      name: "Translation Agent",
      detail: "Normalize the user question into IFRS17 retrieval terms.",
    });
  }
  if (comparisonGraph) {
    pipeline.push({
      name: "Comparison Graph",
      detail: "Build IFRS 4 old-policy nodes against IFRS 17 new-standard nodes.",
    });
  }

  const bm25Started = now();
  const bm25 = searchBm25(retrievalQuery, chunks, { index: searchIndex });
  timings.bm25Ms = elapsed(bm25Started);

  const denseStarted = now();
  const dense = searchDenseProxy(retrievalQuery, chunks, aliases, { index: searchIndex });
  timings.denseMs = elapsed(denseStarted);

  const graphStarted = now();
  const graphResult = searchGraph(retrievalQuery, graph, chunks);
  timings.graphMs = elapsed(graphStarted);

  let contexts;
  if (variant === "bm25") {
    pipeline.push({ name: "BM25", detail: "Original IFRS17 question only." });
    contexts = bm25;
  } else if (variant === "dense") {
    pipeline.push({ name: "Dense proxy", detail: "Browser-safe alias expansion proxy." });
    contexts = dense;
  } else if (variant === "graph") {
    pipeline.push({ name: "Graph Retrieval", detail: "IFRS17 entity relation support chunks." });
    contexts = graphResult.results;
  } else if (variant === "bm25_dense") {
    pipeline.push({ name: "BM25", detail: "Original question." });
    pipeline.push({ name: "Dense proxy", detail: "Alias-expanded semantic proxy." });
    pipeline.push({ name: "RRF Merge", detail: "Merge lexical and semantic candidates." });
    contexts = mergeRankings([
      { name: "bm25", results: bm25 },
      { name: "dense", results: dense },
    ]);
  } else {
    pipeline.push({ name: "Metadata Filter", detail: "Static demo uses IFRS17 profile only." });
    pipeline.push({ name: "BM25", detail: "Original question." });
    pipeline.push({ name: "Dense proxy", detail: "Alias-expanded semantic proxy." });
    pipeline.push({ name: "Graph Retrieval", detail: "IFRS17 entity relation support chunks." });
    pipeline.push({ name: "RRF Merge", detail: "Merge candidates and deduplicate chunks." });
    contexts = mergeRankings(
      [
        { name: "bm25", results: bm25 },
        { name: "dense", results: dense },
        { name: "graph", results: graphResult.results },
      ],
      { graph: graphResult.hubWarning ? 0.35 : 1 },
    );
  }

  timings.totalMs = elapsed(started);
  const trimmed = contexts.slice(0, topK).map((result, rank) => ({
    ...result,
    rank: rank + 1,
    score: Number(result.score.toFixed(4)),
  }));

  return {
    variant,
    query,
    retrievalQuery,
    translation,
    comparisonGraph,
    contexts: trimmed,
    pipeline,
    timings,
    diagnostics: {
      matchedEntities: graphResult.matchedEntities.map((entity) => entity.name),
      hubWarning: graphResult.hubWarning,
      denseMatchedAliases: expandQueryWithAliases(retrievalQuery, aliases).matchedAliases.map(
        (item) => item.canonical,
      ),
    },
    confidence: estimateConfidence(trimmed, graphResult.hubWarning),
  };
}

export function composeChineseRetrievalAnswer(result) {
  const contexts = result?.contexts || [];
  const translation = result?.translation || normalizeQuestionForRetrieval(result?.query || "");
  const citations = contexts.slice(0, 3).map((context) => ({
    rank: context.rank,
    title: context.title,
    page: context.page,
    source: context.source,
  }));

  if (!contexts.length) {
    return {
      language: "zh-TW",
      text: "我沒有在目前的 IFRS17 知識庫中找到足夠相關的來源。建議換成更明確的 IFRS17 名詞後再檢索；這裡不使用模型自身知識補答案。",
      citations,
      confidence: "low",
    };
  }

  const concept = selectAnswerConcept(translation, contexts);
  if (result?.comparisonGraph) {
    const aspects = result.comparisonGraph.rows
      .slice(0, 4)
      .map((row) => row.aspect)
      .join("、");
    return {
      language: "zh-TW",
      text: `舊制 IFRS 4 和新制 IFRS 17 的核心差異是：舊制 IFRS 4 是 interim Standard，允許不同既有保險會計實務延續；新制 IFRS 17 取代 IFRS 4，建立一致的保險合約認列、衡量、表達與揭露模型。比較 Graph 目前整理的重點包含：${aspects}。請搭配下方 Graph 表與 evidence chunks 看每個面向的來源。`,
      citations,
      confidence: result.confidence,
      concept: "舊制 IFRS 4 vs 新制 IFRS 17",
    };
  }
  const confidenceLabel = { high: "高", medium: "中", low: "低" }[result.confidence] || "中";
  const citationText = citations
    .map((citation) => `來源 ${citation.rank}: ${formatCitation(citation)}`)
    .join("；");
  const retrievalText =
    translation.detectedLanguage === "zh-TW" && translation.addedTerms?.length
      ? `翻譯 Agent 將問題轉成檢索詞：${translation.addedTerms.slice(0, 8).join("、")}。`
      : "檢索器直接使用原始問題與 IFRS17 詞表進行比對。";

  return {
    language: "zh-TW",
    text: `${concept.answer} 目前檢索信心為${confidenceLabel}。${retrievalText} ${citationText}。`,
    citations,
    confidence: result.confidence,
    concept: concept.label,
  };
}

function decorateResult(chunk, score, branch, matchedTerms) {
  return {
    id: chunk.id,
    title: chunk.title || chunk.id,
    source: chunk.source || chunk.source_id || "",
    page: chunk.page || "",
    content: chunk.content || "",
    branch,
    matchedTerms,
    score,
  };
}

function phraseBoost(query, chunk, queryTokens) {
  const text = `${chunk.title || ""} ${chunk.content || ""}`.toLowerCase();
  const queryLower = String(query || "").toLowerCase().replace(/\s+/g, " ").trim();
  const usefulTokens = [...queryTokens].filter((token) => token.length > 2);
  let boost = 0;
  if (queryLower.length > 8 && text.includes(queryLower)) boost += 8;
  if (usefulTokens.length && usefulTokens.every((token) => text.slice(0, 500).includes(token))) {
    boost += 2.5;
  }
  if (queryLower.includes("objective") && /objective\s+ifrs\s+17/.test(text)) boost += 6;
  if (queryLower.includes("scope") && /scope\s+of\s+ifrs\s+17|within\s+the\s+scope/.test(text)) boost += 4;
  if (
    queryLower.includes("significant insurance risk") &&
    /accepts\s+significant\s+insurance\s+risk|compensate\s+the\s+policyholder|specified\s+uncertain\s+future\s+event/.test(
      text,
    )
  ) {
    boost += 7;
  }
  if (
    queryLower.includes("definition") &&
    /one\s+party.*accepts\s+significant\s+insurance\s+risk/.test(text)
  ) {
    boost += 4;
  }
  return boost;
}

function evidenceQualityMultiplier(chunk) {
  const title = String(chunk.title || "").toLowerCase();
  const content = String(chunk.content || "").trim().toLowerCase();
  const source = String(chunk.source || chunk.source_id || "").toLowerCase();
  let multiplier = 1;
  if (title.includes("contents") || content.startsWith("contents")) multiplier *= 0.18;
  if (source.includes("ifrs-17-insurance-contracts")) multiplier *= 1.08;
  return multiplier;
}

function formatCitation(citation) {
  const title = citation.title || "Untitled source";
  if (!citation.page || title.toLowerCase().includes(String(citation.page).toLowerCase())) {
    return title;
  }
  return `${title} / ${citation.page}`;
}

function estimateConfidence(contexts, hubWarning) {
  if (!contexts.length) return "low";
  if (hubWarning && contexts.length < 3) return "low";
  if (contexts[0].score >= 0.05 || contexts.length >= 3) return hubWarning ? "medium" : "high";
  return "medium";
}

function containsCjk(value) {
  return /[\u3400-\u9fff]/.test(String(value || ""));
}

function ifrs17SpellingTerms(query) {
  return /ifrs\s*17/i.test(String(query || "")) ? ["IFRS 17", "insurance contracts"] : [];
}

function selectAnswerConcept(translation, contexts) {
  const matched = translation.matchedConcepts || [];
  if (matched.length) {
    const concept = CHINESE_RETRIEVAL_CONCEPTS.find((item) => item.id === matched[0].id);
    if (concept) return concept;
  }

  const contextText = contexts
    .slice(0, 2)
    .map((context) => `${context.title || ""} ${context.content || ""}`)
    .join(" ")
    .toLowerCase();
  const inferred = CHINESE_RETRIEVAL_CONCEPTS.find((concept) =>
    concept.terms.some((term) => contextText.includes(String(term).toLowerCase())),
  );

  return (
    inferred || {
      id: "generic",
      label: "IFRS17 證據摘要",
      answer:
        "根據檢索到的 IFRS17 來源，我先提供與問題最相關的證據摘要；請以列出的來源內容作為最終判斷依據。",
    }
  );
}

function isComparisonQuery(translation) {
  return (translation.matchedConcepts || []).some((item) => item.id === "ifrs4-ifrs17-comparison");
}

function now() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

function elapsed(started) {
  return Math.max(0, Math.round((now() - started) * 100) / 100);
}
