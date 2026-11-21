// Capability presenters: every capability has a surface, and no presenter can crash a page.
import assert from "node:assert/strict";
import { test } from "node:test";
import { buildInput, confidence, presenters, provenance, slotsFor, wordDiff } from "../../runtime/ai.js";
import { renderNode } from "../../runtime/components.js";
import { renderToString } from "../../runtime/core.js";
import { staticContext } from "../../runtime/static.js";
import { node, readJson } from "./helpers.mjs";

const capabilities = readJson("spec", "capabilities.json").capabilities;
const catalog = Object.fromEntries(capabilities.map((c) => [c.id, c]));
const PROV = { provider: "reflex", model: "", latencyMs: 2, traceId: "t1", confidence: 0.8 };
const RESULT = {
  title: "Title", body: "Body", bullets: ["one", "two"], text: "Rewritten text", texts: ["Rewritten text"], answer: "Answer", confidence: 0.7, tone: "info",
  items: [{ label: "First", value: "first", detail: "d", icon: "bolt", action: null, score: 0.9 }], choices: ["A", "B"], question: "Which one?", needed: true,
  ok: false, safe: false, severity: "warning", message: "Check this", suggestion: "Try that", example: "Example", value: "42", display: "42 units", note: "noted",
  changed: true, completion: " completion", fields: [{ name: "email", value: "a@b.co" }], notes: "n", rows: [{ a: 1 }], matched: 1, explanation: "because",
  scene: { type: "Text", id: "s", props: { content: "composed" }, children: [], on: {}, ai: [] }, rationale: "why", score: 72, summary: "Summary",
  findings: [{ severity: "warning", title: "Finding", detail: "Detail", fix: "Fix", target: "x" }], anomalies: [{ label: "Aug", direction: "high", explanation: "spike" }],
  steps: [{ target: "x", title: "Step", body: "Body" }], tokens: [{ name: "--fl-brand", value: "#2a6df4" }], directives: [{ kind: "density", value: "compact" }],
  points: [{ step: 1, value: 3, low: 2, high: 4 }], method: "linear", url: "data:image/svg+xml;utf8,%3Csvg%3E%3C/svg%3E", alt: "alt", entities: [{ kind: "money", text: "$5" }],
  results: [{ text: "hit", score: 0.5 }], detected: "es", redacted: "x", lines: ["a"],
};
const HOSTS = {
  Input: { name: "f", label: "Field", value: "hello" }, TextArea: { name: "t", label: "Text", value: "hello there" }, Select: { name: "s", options: ["A", "B"] },
  Table: { columns: [{ key: "a", label: "A" }], rows: [{ a: 1 }] }, Chart: { kind: "line", data: [{ x: "a", y: 1 }, { x: "b", y: 2 }], x: "x", y: "y" },
  Form: { name: "form" }, Text: { content: "Some text" }, Image: { src: "/a.png" }, Thread: { messages: [{ author: "A", content: "Hi" }] },
  List: { items: [{ title: "One" }] }, Button: { label: "Go" }, Stat: { label: "L", value: "1" }, Card: { title: "Card" }, Suggestions: { items: [] },
  IntentBar: { open: true }, Markdown: { source: "text" }, Code: { source: "x" }, AgentTimeline: { steps: [{ title: "s", status: "done" }] }, Search: { name: "q" },
};

function context(results) {
  const states = new Map();
  const ctx = staticContext({
    catalog, invoke: () => Promise.resolve({ ok: false, error: { message: "offline" } }), formOf: () => ({ values: {}, fields: ["email"] }),
    setField() {}, setFieldByName: () => true, applyTokens() {}, setDensity() {}, startTour() {}, highlight() {}, media() {}, copy() {},
    aiState: (id) => { if (!states.has(id)) states.set(id, { results: Object.assign({}, results), busy: {}, sig: {} }); return states.get(id); },
  });
  ctx.slots = (n) => slotsFor(n, ctx);
  return ctx;
}

test("every capability names a presenter that exists", () => {
  assert.equal(capabilities.length, 185);
  for (const cap of capabilities) assert.equal(typeof presenters[cap.present], "function", `${cap.id} → ${cap.present}`);
  assert.equal(new Set(capabilities.map((c) => c.present)).size, 16);
});

test("no presenter throws, with or without a result, on any plausible host", () => {
  let rendered = 0;
  for (const cap of capabilities) {
    const hosts = (cap.binds && cap.binds.length ? cap.binds : ["Text", "Input", "Table", "Chart", "Form"]).filter((type) => HOSTS[type]);
    for (const type of hosts.length ? hosts : ["Text"]) {
      for (const results of [{}, { [cap.id]: { ok: true, data: RESULT, provenance: PROV } }, { [cap.id]: { ok: false, error: { message: "nope" } } }]) {
        const host = node(type, HOSTS[type], [], { id: "host", ai: [{ capability: cap.id, options: {} }] });
        assert.doesNotThrow(() => renderToString(renderNode(host, context(results))), `${cap.id} on ${type}`);
        rendered++;
      }
    }
  }
  assert.ok(rendered > 500);
});

test("results reach the page", () => {
  const host = node("Text", { content: "Twelve months of revenue" }, [], { id: "host", ai: [{ capability: "data.insights", options: { data: [{ m: "a", v: 1 }] } }] });
  const html = renderToString(renderNode(host, context({ "data.insights": { ok: true, data: { title: "Revenue is rising", body: "Up 12%", bullets: ["Highest: Aug"], confidence: 0.71, tone: "success" }, provenance: PROV } })));
  assert.ok(html.includes("Revenue is rising"));
  assert.ok(html.includes("Highest: Aug"));
  assert.ok(html.includes("fl-prov"), "generated content carries a provenance chip");
});

test("model output is escaped like any other content", () => {
  const evil = '<img src=x onerror=alert(1)>';
  const host = node("Text", { content: "x" }, [], { id: "host", ai: [{ capability: "content.summarize", options: {} }] });
  const html = renderToString(renderNode(host, context({ "content.summarize": { ok: true, data: { title: evil, body: evil, bullets: [evil], confidence: 0.5, tone: "info" }, provenance: PROV } })));
  assert.ok(!html.includes("<img src=x"));
});

test("inputs are assembled from the node and the binding", () => {
  const ctx = context({});
  const chart = node("Chart", HOSTS.Chart);
  assert.deepEqual(buildInput(catalog["data.forecast"], chart, ctx, { horizon: 3 }), { values: [1, 2], horizon: 3 });
  assert.equal(buildInput(catalog["input.natural_date"], node("Input", { name: "when" }), ctx, {}), null, "a required input that is empty blocks the call");
  assert.deepEqual(buildInput(catalog["input.natural_date"], node("Input", { name: "when", value: "tomorrow" }), ctx, {}), { text: "tomorrow" });
  assert.equal(buildInput(catalog["input.format_heal"], node("Input", { name: "e", value: "a@b.co" }), ctx, { kind: "email" }).kind, "email");
});

test("word diff groups a rewritten phrase", () => {
  const diff = wordDiff("We was unable to process you're request.", "We could not process your request.");
  assert.deepEqual(diff.map((s) => s.op), ["same", "del", "add", "same", "del", "add", "same"]);
  assert.equal(diff.filter((s) => s.op !== "add").map((s) => s.text).join(""), "We was unable to process you're request.");
  assert.equal(diff.filter((s) => s.op !== "del").map((s) => s.text).join(""), "We could not process your request.");
  assert.deepEqual(wordDiff("same text", "same text"), [{ op: "same", text: "same text" }]);
  assert.deepEqual(wordDiff("", "new").map((s) => s.op), ["add"]);
});

test("provenance and confidence render in every variant", () => {
  assert.ok(renderToString(provenance(PROV)).includes("reflex"));
  assert.ok(renderToString(provenance({ provider: "openai", model: "gpt-6-luna", latencyMs: 400, traceId: "t" })).includes("gpt-6-luna"));
  assert.equal(provenance(null), null);
  for (const variant of ["bar", "dots", "ring"]) {
    for (const value of [0, 0.5, 1, -3, 9, "x", null]) assert.doesNotThrow(() => renderToString(confidence(value, variant)));
  }
  assert.ok(renderToString(confidence(0.93)).includes("93%"));
});
