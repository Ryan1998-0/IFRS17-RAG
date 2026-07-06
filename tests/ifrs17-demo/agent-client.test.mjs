import assert from "node:assert/strict";
import test from "node:test";

import { buildAgentQueryPayload } from "../../docs/ifrs17-demo/agent-client.js";

test("Agent query payload carries the selected knowledge base and QA model", () => {
  const payload = buildAgentQueryPayload({
    question: "葉文潔和紅岸基地是什麼關係？",
    profile: "three_body_trilogy",
    model: {
      provider: "ollama",
      name: "qwen2.5:7b",
    },
    variant: "full",
    topK: 5,
  });

  assert.equal(payload.profile, "three_body_trilogy");
  assert.deepEqual(payload.model, {
    provider: "ollama",
    name: "qwen2.5:7b",
  });
  assert.equal(payload.question, "葉文潔和紅岸基地是什麼關係？");
  assert.equal(payload.variant, "full");
  assert.equal(payload.top_k, 5);
});
