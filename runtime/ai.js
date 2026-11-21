// Fluidian runtime — AI-native components and capability presenters.
// A capability attached to a node (`node.ai`) is rendered by the presenter its
// registry entry names, so any of the capabilities can decorate any component
// whose data satisfies the capability's input schema.
import { h, cx } from "./core.js";
import { R, renderNode, icon, fmt, primaryText, toneOf } from "./components.js";

const arr = (v) => (Array.isArray(v) ? v : []);
const str = (v) => (v === null || v === undefined ? "" : String(v));
const TONES = ["friendly", "formal", "concise", "confident", "empathetic"];
const FIELDS = new Set(["Input", "TextArea", "Search", "Select", "RadioGroup", "Segmented", "TagInput", "Slider", "Rating", "Checkbox", "Toggle", "FileDrop", "Mic"]);
const pct = (v) => Math.round(Math.max(0, Math.min(1, Number(v) || 0)) * 100);

// ---------------------------------------------------------------- input mapping
/** Candidate values a node can offer to a capability; filtered by the capability's input schema. */
export function candidates(node, ctx) {
  const p = node.props || {}, v = ctx.values.get(node.id), form = ctx.formOf ? ctx.formOf(node) : { values: {}, fields: [] };
  // A field's text is what the person typed; its label must never be sent in place of an empty value.
  const text = typeof v === "string" ? v : typeof p.value === "string" ? p.value : FIELDS.has(node.type) ? "" : primaryText(node) || str(p.body || p.source || p.text);
  const ys = Array.isArray(p.y) ? p.y : [p.y];
  const series = arr(p.data).map((r) => Number(r[ys[0]])).filter(isFinite);
  const opts = arr(p.options).map((o) => (o && typeof o === "object" ? str(o.label ?? o.value) : str(o)));
  return { text, value: v ?? p.value ?? text, label: p.label || p.title || p.name, field: p.name, kind: p.kind || node.type.toLowerCase(), name: p.name,
    data: arr(p.data).length ? p.data : p.rows, rows: arr(p.rows).length ? p.rows : p.data, x: p.x, y: ys[0], values: arr(p.spark).length ? p.spark : series.length ? series : form.values,
    options: opts, items: arr(p.items).map((i) => str(i.title || i.label || i)), messages: p.messages, known: form.values, fields: form.fields,
    targets: form.fields.filter((f) => f !== p.name), context: p.label || p.title || p.placeholder, title: p.title, error: p.error, intent: p.intent,
    prompt: p.prompt || text, schema: p.schema, steps: p.steps, columns: arr(p.columns).map((col) => col.key), description: p.description || text,
    question: text, query: text, utterance: text, message: text, transcript: text, target: node.id, task: text, goal: text, filename: str(p.src).split("/").pop(), seed: p.seed, sketch: text, html: text };
}
export function buildInput(cap, node, ctx, options, extra) {
  const props = (cap.inputSchema && cap.inputSchema.properties) || {}, required = (cap.inputSchema && cap.inputSchema.required) || [];
  const source = Object.assign(candidates(node, ctx), options || {}, extra || {}), out = {};
  for (const key in props) if (source[key] !== undefined && source[key] !== null && source[key] !== "") out[key] = source[key];
  for (const key of required) if (out[key] === undefined || (typeof out[key] === "string" && !out[key].trim()) || (Array.isArray(out[key]) && !out[key].length && key !== "fields")) return null;
  return out;
}
function run(node, binding, cap, ctx, extra, opts = {}) {
  const st = ctx.aiState(node.id), input = buildInput(cap, node, ctx, binding.options, extra);
  if (!input) return Promise.resolve(null);
  const sig = JSON.stringify(input);
  if (!opts.force && st.sig[cap.id] === sig && (st.results[cap.id] || st.busy[cap.id])) return Promise.resolve(st.results[cap.id]);
  st.sig[cap.id] = sig; st.busy[cap.id] = true; ctx.rerender();
  return ctx.invoke(cap.id, input, opts).then((res) => { st.busy[cap.id] = false; st.results[cap.id] = res; ctx.rerender(); return res; });
}
const auto = (node, binding, cap, ctx, extra) => { const st = ctx.aiState(node.id); if (!st.results[cap.id] && !st.busy[cap.id]) queueMicrotask(() => run(node, binding, cap, ctx, extra)); };
const ok = (res) => (res && res.ok ? res.data : null);

// ---------------------------------------------------------------- shared views
export function provenance(prov, compact = true) {
  if (!prov) return null;
  const who = prov.provider === "openai" ? prov.model : prov.provider === "cache" ? "cached" : prov.provider === "replay" ? "replayed" : "reflex";
  return h("span", { class: cx("fl-prov", compact && "is-compact"), title: `Generated content · ${prov.provider}${prov.model ? " · " + prov.model : ""} · ${prov.latencyMs} ms · trace ${prov.traceId}` },
    icon("sparkles", 12), h("span", null, "AI"), h("span", { class: "fl-prov-who" }, who), prov.confidence !== null && prov.confidence !== undefined ? h("span", { class: "fl-prov-conf" }, pct(prov.confidence) + "%") : null);
}
export function confidence(value, variant = "bar", label) {
  const v = Math.max(0, Math.min(1, Number(value) || 0)), band = v >= 0.8 ? "high" : v >= 0.5 ? "medium" : "low";
  const text = label || { high: "Confident", medium: "Likely", low: "Uncertain" }[band];
  if (variant === "dots") return h("span", { class: `fl-conf is-dots is-${band}`, title: `${pct(v)}% confidence` }, [0, 1, 2, 3, 4].map((i) => h("i", { class: i < Math.round(v * 5) ? "on" : "" })), h("span", null, text));
  if (variant === "ring") {
    const r = 15, circ = 2 * Math.PI * r;
    return h("span", { class: `fl-conf is-ring is-${band}` }, h("svg", { width: 40, height: 40, viewBox: "0 0 40 40" }, h("circle", { cx: 20, cy: 20, r, class: "track" }),
      h("circle", { cx: 20, cy: 20, r, class: "value", "stroke-dasharray": `${(circ * v).toFixed(1)} ${circ.toFixed(1)}`, transform: "rotate(-90 20 20)" }), h("text", { x: 20, y: 24, "text-anchor": "middle" }, String(pct(v)))), h("span", null, text));
  }
  return h("span", { class: `fl-conf is-bar is-${band}`, role: "meter", "aria-valuenow": pct(v), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Confidence" },
    h("span", { class: "fl-conf-track" }, h("span", { style: { width: pct(v) + "%" } })), h("span", null, `${text} · ${pct(v)}%`));
}
function insight(d, prov, extra) {
  return h("div", { class: `fl-insight fl-tone-${d.tone || "ai"}` }, h("div", { class: "fl-insight-head" }, h("span", { class: "fl-insight-icon" }, icon(d.icon || "sparkles", 15)),
    h("span", { class: "fl-insight-title" }, d.title), prov ? provenance(prov) : d.source ? h("span", { class: "fl-prov is-compact" }, icon("sparkles", 12), h("span", null, "AI"), h("span", { class: "fl-prov-who" }, d.source)) : null),
    d.body && h("p", { class: "fl-insight-body" }, d.body), arr(d.bullets).length ? h("ul", { class: "fl-insight-list" }, arr(d.bullets).map((b) => h("li", null, str(b)))) : null,
    d.confidence !== undefined && d.confidence !== null ? confidence(d.confidence) : null, extra);
}
function generic(data, prov, heading) {
  if (!data || typeof data !== "object") return null;
  if (data.title !== undefined && data.body !== undefined) return insight(data, prov);
  if (typeof data.text === "string") return insight({ title: heading || "Result", body: data.text, bullets: [] }, prov);
  if (typeof data.answer === "string") return insight({ title: "Answer", body: data.answer, bullets: data.nextSteps || [], confidence: data.confidence }, prov);
  const key = Object.keys(data).find((k) => Array.isArray(data[k]) && data[k].length);
  const rows = key ? data[key].map((it) => (typeof it === "object" ? [it.label, it.title, it.text, it.decision, it.kind].find((x) => x) + (it.explanation || it.body || it.detail ? " — " + (it.explanation || it.body || it.detail) : "") : str(it))) : [];
  return insight({ title: data.summary || data.rationale || heading || (key ? key[0].toUpperCase() + key.slice(1) : "Result"), body: "", bullets: rows.slice(0, 6) }, prov);
}
function report(d, prov, ctx) {
  return h("div", { class: "fl-report" }, h("div", { class: "fl-report-head" }, h("span", { class: cx("fl-score", d.score >= 85 ? "is-good" : d.score >= 60 ? "is-mid" : "is-bad") }, String(Math.round(d.score))),
    h("span", { class: "fl-report-sum" }, d.summary), provenance(prov)), arr(d.findings).map((f) => h("button", { class: `fl-finding is-${f.severity}`, type: "button", onclick: () => f.target && ctx.highlight && ctx.highlight(f.target) },
    icon(f.severity === "info" ? "info" : "alert", 14), h("span", { class: "fl-finding-main" }, h("b", null, f.title), h("span", null, f.detail), f.fix && h("em", null, f.fix)))));
}
const chip = (label, onclick, ic, cls) => h("button", { class: cx("fl-chip", cls), type: "button", onclick }, ic && icon(ic, 12), label);
const spinner = (text) => h("span", { class: "fl-ai-busy" }, h("span", { class: "fl-spinner" }), text || "Thinking…");

// ---------------------------------------------------------------- presenters
const P = {};
P.ghost = (n, b, cap, ctx, slots, st) => { if (st.ghost && st.ghost.typed === str(ctx.values.get(n.id)) && st.ghost.rest) slots.ghost = st.ghost; slots.attrs["data-fl-ghost"] = cap.id; };
P.rewrite = (n, b, cap, ctx, slots, st) => {
  const tones = cap.inputSchema.properties.tone && !(b.options || {}).tone ? TONES : null;
  const go = (extra) => { st.menu = null; run(n, b, cap, ctx, extra, { force: true }).then((res) => { if (ok(res)) st.preview = { cap: cap.id, before: str(ctx.values.get(n.id) ?? n.props.value), after: ok(res).text, prov: res.provenance }; ctx.rerender(); }); };
  slots.inline.push(h("button", { class: "fl-iconbtn is-ai", type: "button", title: cap.title, "aria-label": cap.title, onclick: () => (tones ? ((st.menu = st.menu === cap.id ? null : cap.id), ctx.rerender()) : go()) }, icon("wand", 15)));
  if (st.menu === cap.id) slots.below.push(h("div", { class: "fl-ai-menu" }, h("span", { class: "fl-ai-menu-title" }, cap.title), tones.map((t) => chip(t, () => go({ tone: t }), null, "is-ai"))));
  if (st.busy[cap.id]) slots.below.push(spinner("Rewriting…"));
  if (st.preview && st.preview.cap === cap.id) slots.below.push(h("div", { class: "fl-ai-preview" }, diffView(st.preview.before, st.preview.after), h("div", { class: "fl-ai-preview-foot" }, provenance(st.preview.prov),
    h("span", { class: "fl-grow" }), chip("Dismiss", () => { st.preview = null; ctx.rerender(); }), chip("Accept", () => { ctx.setField(n, st.preview.after); st.preview = null; ctx.rerender(); }, "check", "is-primary"))));
};
P.validate = (n, b, cap, ctx, slots, st) => {
  slots.attrs["data-fl-blur"] = "1";
  if (n.props.error && cap.inputSchema.properties.error) auto(n, b, cap, ctx);
  const res = st.results[cap.id], d = ok(res);
  if (st.busy[cap.id] && !d) return void slots.below.push(spinner("Checking…"));
  if (!d) return;
  if (d.needed !== undefined) { if (d.needed) slots.below.push(h("div", { class: "fl-ai-msg is-info" }, icon("help", 13), h("span", null, d.question), arr(d.choices).map((ch) => chip(ch, () => { ctx.setField(n, ch); st.results[cap.id] = null; ctx.rerender(); })))); return; }
  const good = d.ok !== undefined ? d.ok : d.safe !== undefined ? d.safe : !d.suggestion;
  if (good && !(b.options || {}).showOk) return;
  const tone = good ? "success" : d.severity === "error" ? "danger" : d.severity === "info" ? "info" : "warning";
  slots.below.push(h("div", { class: `fl-ai-msg is-${tone}` }, icon(good ? "check" : "sparkles", 13), h("span", null, d.message, d.suggestion && !/[.?!]$/.test(d.message) ? ". " : " ", d.example ? h("code", { class: "fl-code-inline" }, d.example) : null),
    d.suggestion && d.suggestion.length > 40 ? chip("Use calmer version", () => { ctx.setField(n, d.suggestion); st.results[cap.id] = null; ctx.rerender(); }, "wand") : d.suggestion ? h("em", null, d.suggestion) : null, provenance(res.provenance)));
};
P.fill = (n, b, cap, ctx, slots, st) => {
  const res = st.results[cap.id], d = ok(res);
  if (n.type === "Table") {
    slots.top = h("form", { class: "fl-nlq", onsubmit: (e) => { e.preventDefault(); const q = e.target.elements.q.value.trim(); if (!q) return ctx.set(n.id, { rows: null, note: "" });
      run(n, b, cap, ctx, { question: q, rows: n.props.rows }, { force: true }).then((r) => { if (ok(r)) ctx.set(n.id, { rows: ok(r).rows, note: `${ok(r).matched} of ${arr(n.props.rows).length} rows · ${ok(r).explanation}`, page: 0 }); }); } },
      icon("sparkles", 14), h("input", { name: "q", class: "fl-nlq-input", placeholder: (b.options || {}).placeholder || "Filter in plain language — “overdue over 5000, largest first”", "aria-label": "Filter in plain language" }), st.busy[cap.id] ? h("span", { class: "fl-spinner" }) : h("kbd", { class: "fl-kbd" }, "↵"));
    return;
  }
  if (n.type === "Form" || n.type === "SmartForm" || cap.inputSchema.properties.fields) {
    const apply = (text) => run(n, b, cap, ctx, { text, message: text }, { force: true }).then((r) => { const f = ok(r); if (!f) return; let count = 0; arr(f.fields).forEach((x) => { if (ctx.setFieldByName(n, x.name, x.value)) count++; }); st.filled = count; ctx.rerender(); });
    if (n.type === "Form" || n.type === "SmartForm") {
      slots.below.unshift(h("div", { class: "fl-smartpaste" }, icon("sparkles", 14), h("input", { class: "fl-smartpaste-input", placeholder: (b.options || {}).placeholder || "Paste a signature, email or note here to fill this form", "aria-label": "Smart paste",
        onpaste: (e) => { const t = (e.clipboardData || window.clipboardData).getData("text"); if (t) { e.preventDefault(); e.target.value = t.split("\n")[0].slice(0, 60) + "…"; apply(t); } }, onkeydown: (e) => { if (e.key === "Enter") { e.preventDefault(); apply(e.target.value); } } }),
        st.busy[cap.id] ? h("span", { class: "fl-spinner" }) : st.filled ? h("span", { class: "fl-ai-note" }, `Filled ${st.filled} field${st.filled === 1 ? "" : "s"}`) : null, d ? provenance(res.provenance) : null));
      return;
    }
    slots.attrs["data-fl-blur"] = "1";
    if (d && st.filled) slots.below.push(h("div", { class: "fl-ai-msg is-success" }, icon("sparkles", 13), `Filled ${st.filled} related field${st.filled === 1 ? "" : "s"}`, provenance(res.provenance)));
    return;
  }
  slots.attrs["data-fl-blur"] = "1";
  if (st.busy[cap.id] && !d) return void slots.below.push(spinner("Reading…"));
  if (!d) return;
  if (d.note !== undefined && d.changed === false) return;
  const shown = d.display || d.note || d.value || d.text;
  if (shown && (d.confidence === undefined || d.confidence >= 0.5)) slots.below.push(h("div", { class: "fl-ai-msg is-ai" }, icon("sparkles", 13), h("span", null, d.changed ? `Corrected to ${d.value}. ${d.note || ""}` : d.detected && d.detected !== "en" ? `Detected ${d.detected}: ${d.text}` : `Understood as ${shown}`), provenance(res.provenance)));
};
P.suggest = (n, b, cap, ctx, slots, st) => {
  const inputish = ["Input", "TextArea", "Search", "Select", "RadioGroup", "Segmented", "IntentBar"].includes(n.type);
  if (!inputish || (b.options || {}).auto) auto(n, b, cap, ctx); else slots.attrs["data-fl-blur"] = "1";
  const res = st.results[cap.id], d = ok(res);
  if (st.busy[cap.id] && !d) return void slots.below.push(spinner());
  if (!d) return;
  const list = arr(d.items).length ? d.items : arr(d.results).length ? d.results.map((r) => ({ label: r.text, score: r.score })) : arr(d.choices).map((ch) => (typeof ch === "string" ? { label: ch } : ch));
  if (n.type === "Select" || n.type === "RadioGroup" || n.type === "Segmented") { if (!st.ordered) { st.ordered = true; queueMicrotask(() => ctx.set(n.id, { order: list.map((i) => i.value || i.label) })); } slots.below.push(h("div", { class: "fl-ai-note" }, icon("sparkles", 12), "Options ordered by relevance")); return; }
  if (d.question && list.length) slots.below.push(h("div", { class: "fl-ai-note" }, d.question));
  if (list.length) slots.below.push(h("div", { class: "fl-suggest-row" }, list.slice(0, 6).map((it) => chip(it.label, () => (it.action && it.action !== "none" ? ctx.event(it.action, { value: it.value }, n) : inputish ? ctx.setField(n, it.value || it.label) : ctx.emit(n, "select", { value: it.value || it.label })), it.icon, "is-ai")), provenance(res.provenance)));
};
P.annotate = (n, b, cap, ctx, slots, st) => {
  auto(n, b, cap, ctx);
  const res = st.results[cap.id], d = ok(res);
  if (st.busy[cap.id] && !d) return void slots.below.push(h("div", { class: "fl-insight is-loading" }, spinner("Analysing…")));
  if (!d) return;
  if (arr(d.anomalies).length && n.type === "Chart") slots.props = Object.assign(slots.props || {}, { annotations: arr(n.props.annotations).concat(d.anomalies.map((a) => ({ x: a.label, label: a.direction === "high" ? "Spike" : "Dip", tone: "danger" }))) });
  if (arr(d.steps).length && d.steps[0].target !== undefined) { slots.below.push(h("div", { class: "fl-ai-note" }, icon("sparkles", 12), `Tour ready · ${d.steps.length} step${d.steps.length === 1 ? "" : "s"}`, chip("Start", () => ctx.startTour(d.steps), "play", "is-ai"))); return; }
  slots.below.push(generic(arr(d.anomalies).length ? { title: d.summary, body: "", bullets: d.anomalies.map((a) => a.explanation), tone: "warning" } : d, res.provenance, cap.title));
};
P.transform = (n, b, cap, ctx, slots, st) => {
  const key = ["content", "text", "label", "title", "body"].find((k) => typeof n.props[k] === "string");
  if (!key) return;
  if ((b.options || {}).auto) auto(n, b, cap, ctx, { texts: [n.props[key]] });
  const res = st.results[cap.id], d = ok(res), next = d && (d.text || arr(d.texts)[0] || arr(d.steps).join(" · ") || d.alt);
  if (next && !st.reverted) { slots.props = Object.assign(slots.props || {}, { [key]: next }); slots.below.push(h("div", { class: "fl-ai-note" }, h("button", { class: "fl-prov is-compact is-action", type: "button", title: "Show the original text", onclick: () => { st.reverted = true; ctx.rerender(); } }, icon("sparkles", 12), "Rewritten by AI · show original"))); return; }
  slots.inline.push(h("button", { class: "fl-iconbtn is-ai", type: "button", title: cap.title, "aria-label": cap.title, onclick: () => { st.reverted = false; run(n, b, cap, ctx, { texts: [n.props[key]] }, { force: true }); } }, st.busy[cap.id] ? h("span", { class: "fl-spinner" }) : icon("wand", 14)));
};
P.compose = (n, b, cap, ctx, slots, st) => {
  if (n.type === "Generative" || n.type === "SmartForm") return;
  const empty = (n.type === "Table" && !arr(n.props.rows).length) || (n.type === "List" && !arr(n.props.items).length) || (n.type === "Board" && !arr(n.props.columns).length);
  if (cap.id === "compose.empty_state" && !empty) return;
  auto(n, b, cap, ctx);
  const d = ok(st.results[cap.id]);
  if (d && d.scene) slots.below.push(h("div", { class: "fl-composed" }, renderNode(scoped(d.scene, n.id + "/" + cap.id), ctx)));
};
P.ask = (n, b, cap, ctx, slots, st) => {
  slots.inline.push(h("button", { class: "fl-iconbtn is-ai", type: "button", title: cap.title, "aria-label": cap.title, onclick: () => (st.results[cap.id] ? ((st.results[cap.id] = null), ctx.rerender()) : run(n, b, cap, ctx, null, { force: true })) }, st.busy[cap.id] ? h("span", { class: "fl-spinner" }) : icon("help", 14)));
  const res = st.results[cap.id];
  if (ok(res)) slots.below.push(generic(ok(res), res.provenance, cap.title));
};
P.audit = (n, b, cap, ctx, slots, st) => {
  slots.inline.push(chip(cap.title, () => run(n, b, cap, ctx, null, { force: true }), "shield", "is-ai"));
  const res = st.results[cap.id], d = ok(res);
  if (st.busy[cap.id] && !d) slots.below.push(spinner("Reviewing…"));
  if (d && d.findings) slots.below.push(report(d, res.provenance, ctx)); else if (d) slots.below.push(generic(d, res.provenance, cap.title));
};
P.theme = (n, b, cap, ctx, slots, st) => {
  auto(n, b, cap, ctx);
  const d = ok(st.results[cap.id]);
  if (d && !st.themed) { st.themed = true; queueMicrotask(() => { if (d.tokens) ctx.applyTokens(d.tokens); arr(d.directives).forEach((x) => x.kind === "density" && ctx.setDensity(x.value)); }); }
};
P.media = (n, b, cap, ctx, slots, st) => {
  if (cap.id === "design.illustrate" || cap.id === "access.alt_text") { auto(n, b, cap, ctx); const d = ok(st.results[cap.id]); if (d) slots.props = Object.assign(slots.props || {}, d.url ? { src: d.url, alt: n.props.alt || d.alt } : d.alt ? { alt: d.alt } : {}); return; }
  const ic = cap.id === "modal.dictate" ? "mic" : cap.id === "modal.sonify" ? "play" : "volume";
  slots.inline.push(h("button", { class: cx("fl-iconbtn is-ai", st.busy[cap.id] && "is-busy"), type: "button", title: cap.title, "aria-label": cap.title, onclick: () => ctx.media(n, b, cap) }, st.busy[cap.id] ? h("span", { class: "fl-spinner" }) : icon(ic, 15)));
};
P.service = (n, b, cap, ctx, slots, st) => {
  if (cap.id !== "data.forecast" || n.type !== "Chart") return;
  auto(n, b, cap, ctx);
  const d = ok(st.results[cap.id]);
  if (d) { slots.props = Object.assign(slots.props || {}, { forecast: d.points }); slots.below.push(h("div", { class: "fl-ai-note" }, icon("sparkles", 12), `Forecast · ${d.method}`)); }
};
P.observe = P.command = P.chat = () => {};

/** Build AI slots for a node from its capability bindings. */
export function slotsFor(node, ctx) {
  if (!arr(node.ai).length || !ctx.catalog) return null;
  const slots = { inline: [], below: [], attrs: {}, ghost: null, top: null, used: false, props: null }, st = ctx.aiState(node.id);
  for (const b of node.ai) { const cap = ctx.catalog[b.capability]; if (cap && P[cap.present]) P[cap.present](node, b, cap, ctx, slots, st); }
  return slots;
}
function scoped(scene, prefix) {
  const copy = JSON.parse(JSON.stringify(scene));
  (function walk(n) { n.id = prefix + ":" + n.id; arr(n.children).forEach(walk); })(copy);
  return copy;
}

// ---------------------------------------------------------------- diff
export function wordDiff(a, b) {
  const x = str(a).split(/(\s+)/), y = str(b).split(/(\s+)/), n = x.length, m = y.length;
  if (n * m > 250000) return [{ op: "del", text: str(a) }, { op: "add", text: str(b) }];
  const t = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) t[i][j] = x[i] === y[j] ? t[i + 1][j + 1] + 1 : Math.max(t[i + 1][j], t[i][j + 1]);
  const out = [];
  const push = (op, text) => { const last = out[out.length - 1]; if (last && last.op === op) last.text += text; else out.push({ op, text }); };
  let i = 0, j = 0;
  while (i < n && j < m) { if (x[i] === y[j]) { push("same", x[i]); i++; j++; } else if (t[i + 1][j] >= t[i][j + 1]) push("del", x[i++]); else push("add", y[j++]); }
  while (i < n) push("del", x[i++]);
  while (j < m) push("add", y[j++]);
  // Group changes separated only by whitespace, so a rewritten phrase reads as one deletion and one insertion.
  const merged = [];
  let run = null;
  const flush = () => { if (!run) return; if (run.del.trim()) merged.push({ op: "del", text: run.del }); if (run.add.trim()) merged.push({ op: "add", text: run.add }); if (run.tail) merged.push({ op: "same", text: run.tail }); run = null; };
  out.forEach((seg, k) => {
    if (seg.op !== "same") { run = run || { del: "", add: "", tail: "" }; if (run.tail) { run.del += run.tail; run.add += run.tail; run.tail = ""; } run[seg.op] += seg.text; return; }
    const next = out[k + 1];
    if (run && !seg.text.trim() && next && next.op !== "same") { run.tail = seg.text; return; }
    flush();
    merged.push(seg);
  });
  flush();
  return merged;
}
const diffView = (a, b) => h("div", { class: "fl-diff-text" }, wordDiff(a, b).map((s) => (s.op === "same" ? s.text : h(s.op === "add" ? "ins" : "del", null, s.text))));

// ---------------------------------------------------------------- AI-native components
R.Insight = (n, c) => insight(n.props, null, arr(n.children).length ? h("div", { class: "fl-insight-actions" }, arr(n.children).map((k) => renderNode(k, c))) : null);
R.Provenance = (n) => {
  const p = n.props;
  if (p.compact) return provenance({ provider: p.provider || "reflex", model: p.model, confidence: p.confidence, latencyMs: "–", traceId: "–" });
  return h("div", { class: "fl-provenance" }, h("span", { class: "fl-prov-mark" }, icon("sparkles", 14)), h("div", null, h("div", { class: "fl-prov-line" }, "Generated content"),
    h("div", { class: "fl-prov-meta" }, [p.provider || "reflex", p.model, p.generatedAt, p.note].filter(Boolean).join(" · "))), p.confidence !== undefined && p.confidence !== null ? confidence(p.confidence, "ring") : null);
};
R.Confidence = (n) => confidence(n.props.value, n.props.variant || "bar", n.props.label);
R.Diff = (n) => h("div", { class: `fl-diff is-${n.props.mode || "inline"}` }, n.props.title && h("div", { class: "fl-diff-title" }, icon("wand", 13), n.props.title),
  n.props.mode === "split" ? h("div", { class: "fl-diff-split" }, h("div", { class: "fl-diff-text is-before" }, n.props.before), h("div", { class: "fl-diff-text is-after" }, n.props.after)) : diffView(n.props.before, n.props.after));
R.Thinking = (n) => {
  const cur = Number(n.props.current) || 0;
  return h("div", { class: "fl-thinking", role: "status" }, h("div", { class: "fl-thinking-head" }, h("span", { class: "fl-orb" }), h("span", null, n.props.label)),
    arr(n.props.steps).length ? h("ol", { class: "fl-thinking-steps" }, arr(n.props.steps).map((s, i) => h("li", { class: cx(i < cur && "is-done", i === cur && "is-current") }, i < cur ? icon("check", 12) : i === cur ? h("span", { class: "fl-spinner" }) : h("span", { class: "fl-step-dotmini" }), str(s)))) : null);
};
R.StreamText = (n) => h("p", { class: cx("fl-stream", n.props.streaming && "is-streaming") }, str(n.props.text), n.props.streaming && h("span", { class: "fl-caret" }));
R.Suggestions = (n, c, slots) => {
  const p = n.props, st = c.aiState ? c.aiState(n.id) : { results: {} }, extra = Object.values(st.results || {}).flatMap((r) => arr(ok(r) && ok(r).items));
  if (slots) slots.used = true;
  const items = arr(p.items).concat(extra);
  return h("div", { class: `fl-suggestions is-${p.variant || "chips"}` }, p.title && h("div", { class: "fl-suggest-title" }, icon("sparkles", 13), p.title),
    h("div", { class: "fl-suggest-row" }, items.map((it) => h("button", { class: "fl-chip is-ai", type: "button", onclick: () => (it.action && it.action !== "none" ? c.event(it.action, { value: it.value }, n) : c.emit(n, "select", { value: it.value ?? it.label })) },
      it.icon && icon(it.icon, 13), h("span", null, it.label), it.detail && p.variant === "list" ? h("span", { class: "fl-chip-detail" }, it.detail) : null))));
};
R.Approval = (n, c) => {
  const p = n.props, st = c.state(n.id, { status: p.status || "pending" }), risk = p.risk || "medium";
  const decide = (status, event) => { c.set(n.id, { status }); c.emit(n, event, { value: status }); };
  return h("div", { class: `fl-approval is-${risk} status-${st.status}` }, h("div", { class: "fl-approval-head" }, h("span", { class: "fl-approval-icon" }, icon("shield", 17)),
    h("div", { class: "fl-grow" }, h("div", { class: "fl-approval-title" }, p.title), p.agent && h("div", { class: "fl-approval-agent" }, icon("cpu", 12), `Requested by ${p.agent}`)),
    h("span", { class: `fl-badge is-soft fl-tone-${{ low: "success", medium: "warning", high: "danger" }[risk]}` }, `${risk} risk`)),
    p.summary && h("p", { class: "fl-approval-summary" }, p.summary),
    arr(p.details).length ? h("dl", { class: "fl-kv", style: { "--fl-cols": 2 } }, arr(p.details).map((d) => h("div", { class: "fl-kv-row" }, h("dt", null, d.key), h("dd", null, str(d.value))))) : null,
    st.status === "pending" ? h("div", { class: "fl-approval-foot" }, h("button", { class: "fl-btn is-ghost size-md", type: "button", onclick: () => decide("rejected", "reject") }, p.rejectLabel || "Reject"),
      h("button", { class: "fl-btn is-primary size-md", type: "button", onclick: () => decide("approved", "approve") }, icon("check", 15), p.approveLabel || "Approve"))
      : h("div", { class: "fl-approval-foot is-decided" }, icon(st.status === "approved" ? "check" : "x", 15), st.status === "approved" ? "Approved" : "Rejected"));
};
const STEP_ICON = { done: "check", failed: "x" };
R.AgentTimeline = (n) => h("div", { class: "fl-agent" }, n.props.title && h("div", { class: "fl-agent-title" }, icon("cpu", 14), n.props.title), h("ol", { class: "fl-agent-steps" }, arr(n.props.steps).map((s) => h("li", { class: `fl-agent-step is-${s.status || "pending"}` },
  h("span", { class: "fl-agent-dot" }, s.status === "running" ? h("span", { class: "fl-spinner" }) : STEP_ICON[s.status] ? icon(STEP_ICON[s.status], 11) : null),
  h("div", { class: "fl-agent-main" }, h("div", { class: "fl-agent-row" }, h("span", { class: "fl-agent-name" }, s.title), s.tool && h("code", { class: "fl-code-inline" }, s.tool), s.duration && h("span", { class: "fl-agent-time" }, s.duration)), s.detail && h("div", { class: "fl-agent-detail" }, s.detail))))));
R.Tour = (n, c) => {
  const p = n.props, steps = arr(p.steps), st = c.state(n.id, { active: !!p.active, current: Number(p.current) || 0 });
  if (!st.active || !steps.length) return h("div", { class: "fl-tour-idle" }, h("button", { class: "fl-chip is-ai", type: "button", onclick: () => c.set(n.id, { active: true, current: 0 }) }, icon("play", 12), `Take the tour · ${steps.length} steps`));
  const step = steps[Math.min(st.current, steps.length - 1)], last = st.current >= steps.length - 1;
  const place = (el) => c.placeTour && c.placeTour(el, step.target);
  return h("div", { class: "fl-tour", hook: { mount: place, update: place } }, h("div", { class: "fl-tour-spot" }),
    h("div", { class: "fl-tour-card", role: "dialog", "aria-label": step.title }, h("div", { class: "fl-tour-count" }, `${st.current + 1} / ${steps.length}`), h("div", { class: "fl-tour-title" }, step.title), h("p", { class: "fl-tour-body" }, step.body),
      h("div", { class: "fl-tour-foot" }, h("button", { class: "fl-linkbtn", type: "button", onclick: () => { c.set(n.id, { active: false }); c.emit(n, "finish", { value: st.current }); } }, "Skip"), h("span", { class: "fl-grow" }),
        st.current > 0 && h("button", { class: "fl-btn is-ghost size-sm", type: "button", onclick: () => c.set(n.id, { current: st.current - 1 }) }, "Back"),
        h("button", { class: "fl-btn is-primary size-sm", type: "button", onclick: () => (last ? (c.set(n.id, { active: false }), c.emit(n, "finish", { value: st.current })) : c.set(n.id, { current: st.current + 1 })) }, last ? "Done" : "Next"))));
};
function composeInto(n, c, capability, input, st) {
  if (st.state === "thinking") return;
  st.state = "thinking"; c.rerender();
  c.invoke(capability, input, { stream: true, onPartial: (part) => { if (part && part.scene && part.scene.type) { st.scene = part.scene; c.rerender(); } } }).then((res) => {
    if (res && res.ok && res.data.scene) { st.scene = res.data.scene; st.rationale = res.data.rationale; st.prov = res.provenance; st.state = "ready"; c.emit(n, "ready", {}); }
    else { st.state = "error"; st.error = res && res.error ? res.error.message : "No scene returned"; }
    c.rerender();
  });
}
R.Generative = (n, c) => {
  const p = n.props, st = c.state(n.id, { state: p.state || "idle", scene: null, started: false, intent: p.intent });
  const capability = p.capability || "compose.intent", input = Object.assign({ intent: st.intent, description: st.intent, goal: st.intent, sketch: st.intent, context: st.intent }, p.input || {});
  if (c.live !== false && p.auto !== false && !st.started && c.invoke) { st.started = true; queueMicrotask(() => composeInto(n, c, capability, input, st)); }
  const refine = (e) => { e.preventDefault(); const text = e.target.elements.r.value.trim(); if (!text || !st.scene) return; e.target.reset(); st.state = "idle"; composeInto(n, c, "compose.refine", { instruction: text, scene: st.scene }, st); };
  return h("section", { class: `fl-generative is-${st.state}` }, h("header", { class: "fl-gen-head" }, h("span", { class: "fl-gen-mark" }, icon("sparkles", 14)), h("span", { class: "fl-gen-intent" }, "“" + str(st.intent) + "”"),
    st.prov && provenance(st.prov), h("span", { class: "fl-grow" }), h("button", { class: "fl-iconbtn", type: "button", title: "Compose again", "aria-label": "Compose again", onclick: () => { st.state = "idle"; composeInto(n, c, capability, input, st); } }, icon("refresh", 14))),
    st.scene ? h("div", { class: "fl-gen-body", key: "scene" }, renderNode(scoped(st.scene, n.id), c)) : st.state === "error" ? h("div", { class: "fl-callout fl-tone-danger" }, icon("alert", 18), h("div", { class: "fl-callout-main" }, h("div", { class: "fl-callout-title" }, "Could not compose this region"), h("div", { class: "fl-callout-body" }, st.error)))
      : arr(n.children).length ? h("div", { class: "fl-gen-body" }, arr(n.children).map((k) => renderNode(k, c))) : h("div", { class: "fl-gen-body" }, R.Thinking({ props: { label: "Composing interface", steps: ["Reading intent", "Choosing components", "Laying out"], current: 1 } })),
    st.scene ? h("form", { class: "fl-gen-foot", onsubmit: refine }, icon("wand", 14), h("input", { name: "r", class: "fl-gen-refine", placeholder: "Refine: “add a phone field”, “make it compact”, “use two columns”…", "aria-label": "Refine this region" }),
      st.state === "thinking" ? h("span", { class: "fl-spinner" }) : h("button", { class: "fl-btn is-ai size-sm", type: "submit" }, "Refine")) : null,
    st.rationale ? h("div", { class: "fl-gen-why" }, st.rationale) : null);
};
R.SmartForm = (n, c) => {
  const p = n.props, st = c.state(n.id, { state: "idle", scene: null, started: false });
  if (!st.started && c.invoke) { st.started = true; queueMicrotask(() => composeInto(n, c, "compose.schema_form", { schema: p.schema || {}, name: p.name, values: p.values, submitLabel: p.submitLabel }, st)); }
  if (!st.scene) return h("div", { class: "fl-smartform" }, R.Skeleton({ props: { shape: "text", lines: 4 } }));
  const scene = scoped(st.scene, n.id);
  (function bind(x) { if (x.type === "Form" && n.on && n.on.submit) x.on = { submit: n.on.submit }; if (x.type === "Button" && x.props.variant === "primary" && n.on && n.on.submit) x.on = { click: n.on.submit }; arr(x.children).forEach(bind); })(scene);
  return h("div", { class: "fl-smartform" }, p.title && h("h3", { class: "fl-card-title" }, p.title), renderNode(scene, c), st.prov && h("div", { class: "fl-gen-why" }, provenance(st.prov), " Form inferred from schema"));
};
R.IntentBar = (n, c, slots) => {
  const p = n.props, st = c.state(n.id, { open: !!p.open, query: str(typeof p.query === "string" ? p.query : ""), reply: null, busy: false, extra: null });
  if (slots) slots.used = true;
  const submit = (text) => {
    if (!text.trim()) return;
    if (n.on && n.on.command) return c.emit(n, "command", { value: text });
    c.set(n.id, { busy: true, reply: null });
    c.invoke("command.route", { utterance: text }).then((res) => {
      const d = res && res.ok ? res.data : null;
      if (d && d.action && d.action !== "none" && d.confidence >= 0.55) { c.event(d.action, d.args, n); c.set(n.id, { busy: false, reply: { text: d.reply, prov: res.provenance, tone: "success" }, query: "" }); }
      else if (d && arr(d.alternatives).length) c.set(n.id, { busy: false, reply: { text: "Did you mean…", prov: res.provenance, choices: d.alternatives } });
      else c.set(n.id, { busy: false, reply: { text: d ? d.reply : (res && res.error && res.error.message) || "No matching action.", prov: res && res.provenance, tone: "warning" } });
    });
  };
  const sugg = arr(p.suggestions).concat(arr(st.extra)), q = st.query.toLowerCase(), words = q.split(/[^\p{L}\p{N}]+/u).filter((w) => w.length > 2);
  const overlap = (s) => { const hay = (str(s.label) + " " + str(s.detail)).toLowerCase(); return hay.includes(q) ? 99 : words.filter((w) => hay.includes(w)).length; };
  const shown = (q ? sugg.map((s) => [overlap(s), s]).filter(([score]) => score > 0).sort((a, b) => b[0] - a[0]).map(([, s]) => s) : sugg).slice(0, 7);
  return h("div", { class: cx("fl-intent", st.open && "is-open") }, h("form", { class: "fl-intent-bar", onsubmit: (e) => { e.preventDefault(); submit(st.query); } }, h("span", { class: "fl-intent-mark" }, icon("sparkles", 16)),
    h("input", { class: "fl-intent-input", name: "utterance", value: st.query, placeholder: p.placeholder || "Ask or command…", "aria-label": "Intent bar", autocomplete: "off", "data-fl-intent": "1",
      onfocus: () => !st.open && c.set(n.id, { open: true }), oninput: (e) => c.set(n.id, { query: e.target.value, reply: null }) }), st.busy ? h("span", { class: "fl-spinner" }) : h("kbd", { class: "fl-kbd" }, "⌘K")),
    st.open ? h("div", { class: "fl-intent-panel" }, st.reply ? h("div", { class: `fl-intent-reply is-${st.reply.tone || "info"}` }, icon("sparkles", 14), h("span", null, st.reply.text), arr(st.reply.choices).map((a) => chip(a.replace(/_/g, " "), () => { c.event(a, {}, n); c.set(n.id, { reply: null }); }, "bolt", "is-ai")), provenance(st.reply.prov)) : null,
      shown.map((s) => h("button", { class: "fl-intent-item", type: "button", onclick: () => (s.action ? (c.event(s.action, { value: s.value }, n), c.set(n.id, { reply: { text: `Ran “${s.label}”.`, tone: "success" } })) : c.set(n.id, { query: s.label })) },
        h("span", { class: "fl-intent-ic" }, icon(s.icon || "bolt", 15)), h("span", { class: "fl-intent-text" }, h("span", null, s.label), s.detail && h("span", { class: "fl-help" }, s.detail)), s.kbd && h("kbd", { class: "fl-kbd" }, s.kbd))),
      h("div", { class: "fl-intent-hint" }, p.hint || "Type what you want to do — actions run only when the match is confident."), slots ? slots.below : null) : null);
};
R.Copilot = (n, c) => {
  const p = n.props, st = c.state(n.id, { messages: null, busy: false, draft: "" }), messages = st.messages || arr(p.messages);
  const send = (text) => {
    if (!text.trim() || st.busy) return;
    if (n.on && n.on.message) return c.emit(n, "message", { value: text });
    const next = messages.concat([{ role: "user", content: text }]);
    c.set(n.id, { messages: next, busy: true, draft: "" });
    c.invoke("command.copilot", { message: text, history: next.slice(-8) }).then((res) => {
      const d = res && res.ok ? res.data : null;
      c.set(n.id, { busy: false, messages: next.concat([{ role: "assistant", content: d ? d.reply : (res && res.error && res.error.message) || "Something went wrong.", prov: res && res.provenance, action: d && d.action && d.action !== "none" ? d.action : null, args: d && d.args, chips: d ? d.suggestions : [] }]) });
    });
  };
  const last = messages[messages.length - 1], chips = (last && last.chips) || p.suggestions;
  return h("section", { class: `fl-copilot is-${p.mode || "inline"}` }, h("header", { class: "fl-copilot-head" }, h("span", { class: "fl-orb" }), h("span", { class: "fl-copilot-title" }, p.title || "Copilot"), h("span", { class: "fl-copilot-sub" }, "Grounded in this screen")),
    h("div", { class: "fl-copilot-log", role: "log", "aria-live": "polite", hook: { update: (el) => { el.scrollTop = el.scrollHeight; } } }, messages.map((m, i) => h("div", { class: `fl-bubble is-${m.role === "user" ? "user" : "assistant"}`, key: "m" + i },
      h("div", { class: "fl-bubble-text" }, str(m.content)), m.action ? h("button", { class: "fl-chip is-ai", type: "button", onclick: () => c.event(m.action, m.args || {}, n) }, icon("bolt", 12), `Run ${m.action.replace(/_/g, " ")}`) : null, m.prov ? provenance(m.prov) : null)),
      (st.busy || p.thinking) ? h("div", { class: "fl-bubble is-assistant is-typing", key: "typing" }, h("i"), h("i"), h("i")) : null),
    arr(chips).length ? h("div", { class: "fl-suggest-row" }, arr(chips).map((s) => chip(s, () => send(s), null, "is-ai"))) : null,
    h("form", { class: "fl-copilot-form", onsubmit: (e) => { e.preventDefault(); const el = e.target.elements.message; send(el.value); el.value = ""; } }, h("input", { class: "fl-input", name: "message", placeholder: p.placeholder || "Ask about this screen", "aria-label": "Message", autocomplete: "off" }),
      h("button", { class: "fl-btn is-ai is-icon size-md", type: "submit", "aria-label": "Send" }, icon("send", 16))));
};
export { P as presenters, report as reportView, generic as genericView };
