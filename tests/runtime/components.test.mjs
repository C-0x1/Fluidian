// Server-side rendering of every component: correctness, robustness and output escaping.
import assert from "node:assert/strict";
import { test } from "node:test";
import { renderScene } from "../../runtime/static.js";
import { fluidianMark, fmt, icon, markdown, toneOf } from "../../runtime/components.js";
import { FLUIDIAN_MARK } from "../../runtime/brand.js";
import { renderToString } from "../../runtime/core.js";
import { node, readJson, referenceScene, walk } from "./helpers.mjs";

const components = readJson("spec", "components.json").components;
const scene = referenceScene();
const LOGIC = new Set(["State", "Show", "Each"]);
const byType = new Map();
walk(scene, (n) => { if (!byType.has(n.type)) byType.set(n.type, n); });

test("the reference scene contains every registered component", () => {
  assert.equal(components.length, 123);
  for (const spec of components) assert.ok(byType.has(spec.type), `${spec.type} is missing from the reference scene`);
});

test("every component renders to tagged markup", () => {
  for (const spec of components) {
    const html = renderScene(byType.get(spec.type));
    if (LOGIC.has(spec.type)) continue;  // State, Show and Each shape what is rendered; they have no element of their own
    assert.ok(html.includes(`data-fl-type="${spec.type}"`) || html.includes("hidden"), `${spec.type} did not render`);
    assert.ok(!html.includes("[object Object]"), `${spec.type} leaked an object into text`);
    assert.ok(!/>undefined</.test(html) && !/="undefined"/.test(html), `${spec.type} rendered "undefined"`);
    assert.ok(!/>NaN</.test(html), `${spec.type} rendered NaN`);
  }
});

test("the whole reference scene renders", () => {
  const html = renderScene(scene);
  assert.ok(html.length > 20000);
  assert.ok(html.includes("fl-page"));
});

test("components tolerate missing props", () => {
  for (const spec of components) {
    const bare = node(spec.type, {}, spec.container ? [node("Text", { content: "child" }, [], { id: "kid" })] : []);
    assert.doesNotThrow(() => renderScene(bare), `${spec.type} threw with empty props`);
  }
});

test("components tolerate props of the wrong shape", () => {
  const junk = [null, 5, "text", true, [], {}, [null, 3, "x", {}], { a: 1 }, [[1], [null]], [{ children: 5, cards: "x", items: null }], [{ cards: [null, {}], children: [null] }]];
  for (const spec of components) {
    for (const value of junk) {
      const props = {};
      for (const key of Object.keys(spec.props)) props[key] = value;
      assert.doesNotThrow(() => renderScene(node(spec.type, props)), `${spec.type} threw when every prop was ${JSON.stringify(value)}`);
    }
  }
});

test("unknown component types fall back instead of throwing", () => {
  const html = renderScene(node("NotAComponent", { label: "x" }));
  assert.equal(typeof html, "string");
});

test("text content is escaped", () => {
  const attack = '<script>alert(1)</script><img src=x onerror=alert(1)>';
  for (const [type, props] of [["Text", { content: attack }], ["Heading", { text: attack }], ["Button", { label: attack }], ["Badge", { label: attack }],
    ["Callout", { title: attack, body: attack }], ["Code", { source: attack }], ["Stat", { label: attack, value: attack }], ["Input", { name: "n", label: attack, value: attack, placeholder: attack }],
    ["Table", { columns: [{ key: "a", label: attack }], rows: [{ a: attack }] }], ["List", { items: [{ title: attack, detail: attack, badge: attack }] }],
    ["Thread", { messages: [{ author: attack, content: attack }] }], ["Insight", { title: attack, body: attack, bullets: [attack] }], ["Select", { name: "s", options: [attack] }]]) {
    const html = renderScene(node(type, props));
    assert.ok(!html.includes("<script>alert(1)"), `${type} emitted a script tag`);
    assert.ok(!/<img src=x/.test(html), `${type} emitted injected markup`);
  }
});

test("attribute values are escaped", () => {
  const html = renderScene(node("Input", { name: 'x" autofocus onfocus="alert(1)', placeholder: '"><script>alert(1)</script>' }));
  assert.ok(!html.includes('onfocus="alert(1)"'));
  assert.ok(!html.includes("<script>"));
});

test("dangerous URLs are neutralised", () => {
  const link = renderScene(node("Link", { label: "go", href: "javascript:alert(1)" }));
  assert.ok(!link.toLowerCase().includes("javascript:"));
  const image = renderScene(node("Image", { src: "javascript:alert(1)", alt: "x" }));
  assert.ok(!image.toLowerCase().includes("javascript:"));
  const data = renderScene(node("Image", { src: "data:text/html,<script>alert(1)</script>", alt: "x" }));
  assert.ok(!data.includes("data:text/html"));
  const ok = renderScene(node("Image", { src: "data:image/svg+xml;utf8,%3Csvg%3E%3C/svg%3E", alt: "x" }));
  assert.ok(ok.includes("data:image/svg+xml"));
});

test("markdown renders structure and refuses raw HTML and script links", () => {
  const html = renderToString({ tag: "div", attrs: {}, children: markdown("# Title\n\nSome **bold**, `code` and [a link](https://example.com).\n\n- one\n- two\n\n<script>alert(1)</script>\n\n[bad](javascript:alert(1))") });
  assert.ok(html.includes("<strong>bold</strong>"));
  assert.ok(html.includes('href="https://example.com"'));
  assert.ok(html.includes("<li>one</li>"));
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.toLowerCase().includes('href="javascript:'));
});

test("number, currency, percent and date formatting", () => {
  assert.equal(fmt(12400, "currency"), "$12,400");
  assert.equal(fmt(12.5, "currency"), "$12.50");
  assert.equal(fmt(42, "percent"), "42%");
  assert.equal(fmt(1740000, "compact"), "1.7M");
  assert.equal(fmt("2026-11-27", "date"), "Nov 27, 2026");
  assert.equal(fmt(null), "");
  assert.equal(fmt("not a number", "currency"), "not a number");
});

test("status words map to tones", () => {
  assert.equal(toneOf("Paid"), "success");
  assert.equal(toneOf("Overdue"), "danger");
  assert.equal(toneOf("Pending"), "warning");
  assert.equal(toneOf("Banana"), "neutral");
});

test("icons fall back for unknown names", () => {
  assert.doesNotThrow(() => renderToString(icon("definitely-not-an-icon")));
  assert.ok(renderToString(icon("sparkles")).includes("<svg"));
});

test("the Fluidian mark is drawn for Fluidian and never handed to another brand", () => {
  const mark = renderToString(fluidianMark(28));
  assert.ok(mark.includes('class="fl-fluidian-mark"') && mark.includes(FLUIDIAN_MARK.stem) && mark.includes(FLUIDIAN_MARK.wave));
  for (const [, colour] of [...FLUIDIAN_MARK.tile, ...FLUIDIAN_MARK.ribbon]) assert.ok(mark.includes(colour));
  const nav = (props) => renderScene(node("NavBar", props));
  assert.ok(nav({ brand: "Fluidian", logo: "fluidian" }).includes("fl-fluidian-mark"));
  assert.ok(nav({ brand: "Fluidian" }).includes("fl-fluidian-mark"), "a page whose brand is Fluidian gets the mark by default");
  assert.ok(renderScene(node("Footer", { brand: "Fluidian", columns: [] })).includes("fl-fluidian-mark"));
  assert.ok(!renderScene(node("Footer", { brand: "Lumen", columns: [] })).includes("fl-fluidian-mark"));
  assert.ok(!nav({ brand: "Lumen" }).includes("fl-fluidian-mark"));
  for (const logo of ["orb", "wave", "anything-else", "f"]) assert.ok(!nav({ brand: "Lumen", logo }).includes("fl-fluidian-mark"), logo);
  const shell = (brand) => renderScene(node("Shell", { brand, nav: [] }));
  assert.ok(shell("Fluidian").includes("fl-fluidian-mark"));
  assert.ok(!shell("Northwind").includes("fl-fluidian-mark") && shell("Northwind").includes("fl-brand-mark"));
});
