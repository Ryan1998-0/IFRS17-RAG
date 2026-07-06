import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { runRetrieval } from "../../docs/ifrs17-demo/retrieval-core.js";

const demoData = JSON.parse(
  readFileSync(
    new URL("../../docs/ifrs17-demo/data/ifrs17_demo_data.json", import.meta.url),
    "utf8",
  ),
);

test("BM25 plus Dense plus Graph variant exposes the graph stage", () => {
  const result = runRetrieval({
    query: "IFRS17 的目的是什麼？",
    chunks: demoData.chunks,
    aliases: demoData.aliases,
    graph: demoData.graph,
    variant: "bm25_dense_graph",
    topK: 8,
  });

  const names = result.pipeline.map((step) => step.name);
  assert.equal(result.variant, "bm25_dense_graph");
  assert.ok(names.includes("BM25"));
  assert.ok(names.includes("Dense proxy"));
  assert.ok(names.includes("Graph Retrieval"));
  assert.ok(names.includes("RRF Merge"));
  assert.ok(!names.includes("Metadata Filter"));
  assert.ok(!names.includes("Evidence Quality Gate"));
});

test("Full stack lab labels every architecture component it applies", () => {
  const result = runRetrieval({
    query: "舊制 IFRS 4 和新制 IFRS 17 差在哪？",
    chunks: demoData.chunks,
    aliases: demoData.aliases,
    graph: demoData.graph,
    variant: "full",
    topK: 8,
  });

  const names = result.pipeline.map((step) => step.name);
  assert.ok(names.includes("Translation Agent"));
  assert.ok(names.includes("Comparison Graph"));
  assert.ok(names.includes("Metadata Filter"));
  assert.ok(names.includes("BM25"));
  assert.ok(names.includes("Dense proxy"));
  assert.ok(names.includes("Graph Retrieval"));
  assert.ok(names.includes("RRF Merge"));
  assert.ok(names.includes("Reranker"));
  assert.ok(names.includes("Graph Hub Guard"));
  assert.ok(names.includes("Evidence Quality Gate"));
  assert.ok(names.indexOf("RRF Merge") < names.indexOf("Reranker"));
  assert.ok(names.indexOf("Reranker") < names.indexOf("Graph Hub Guard"));
});
