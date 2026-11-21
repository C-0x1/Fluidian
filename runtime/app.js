// Fluidian runtime — browser entry point: session, transport, events, signals, AI plumbing.
import { h, patch, cx } from "./core.js";
import { R, renderNode, icon, fluidianMark } from "./components.js";
import { slotsFor, buildInput, reportView, genericView, provenance } from "./ai.js";
import "./blocks.js";
import "./viz.js";
import { THEMES } from "./themes.js";
import { createStore, isLocal, runActions, lint } from "./logic.js";

const params = new URLSearchParams(location.search);
const S = { errors: [], palette: false, scheme: "", sid: "", token: "", scene: null, route: location.pathname, app: { name: "Fluidian" }, live: false, dev: false, catalog: null, actions: [],
  ui: new Map(), ai: new Map(), values: new Map(), toasts: [], signals: [], sent: 0, tour: null, pop: null, dev_open: false, devdata: null, fixes: [],
  observed: 0, consentAsked: new Set(), events: [], started: performance.now() };
const root = document.getElementById("fl-root");
let frame = 0;
const rerender = () => { if (!frame) frame = requestAnimationFrame(() => { frame = 0; patch(root, view()); }); };
const arr = (v) => (Array.isArray(v) ? v : []);

// ---------------------------------------------------------------- transport
async function post(path, body) {
  const res = await fetch("/_fluidian/" + path, { method: "POST", headers: { "Content-Type": "application/json", "X-Fluidian-Token": S.token }, body: JSON.stringify(Object.assign({ sid: S.sid }, body)) });
  return res.json().catch(() => ({ ok: false, error: { code: String(res.status), message: res.statusText } }));
}
async function invoke(capability, input, opts = {}) {
  const body = { capability, input, mode: opts.mode || "auto" };
  try {
    if (!opts.stream) return await post("ai", body);
    const res = await fetch("/_fluidian/ai/stream", { method: "POST", headers: { "Content-Type": "application/json", "X-Fluidian-Token": S.token }, body: JSON.stringify(Object.assign({ sid: S.sid }, body)) });
    if (!res.ok || !res.body) return res.json();
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = "", result = null;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let cut;
      while ((cut = buf.indexOf("\n\n")) >= 0) {
        const block = buf.slice(0, cut); buf = buf.slice(cut + 2);
        const ev = (/^event: (.*)$/m.exec(block) || [])[1], data = (/^data: (.*)$/m.exec(block) || [])[1];
        if (!data) continue;
        if (ev === "partial" && opts.onPartial) opts.onPartial(JSON.parse(data)); else if (ev === "result") result = JSON.parse(data);
      }
    }
    return result || { ok: false, error: { code: "stream", message: "The stream ended without a result." } };
  } catch (err) { return { ok: false, error: { code: "network", message: String(err.message || err) } }; }
}
function connect() {
  const es = new EventSource(`/_fluidian/events?sid=${encodeURIComponent(S.sid)}&token=${encodeURIComponent(S.token)}`);
  es.addEventListener("scene", (e) => { const d = JSON.parse(e.data); S.scene = d.root; S.fixes = (d.fixes || []).concat(S.dev ? lint(d.root) : []); S.route = d.route || S.route; document.title = titleOf(d.root); rerender(); afterScene(); });
  es.addEventListener("toast", (e) => { const d = JSON.parse(e.data); toast(d.text, d.tone); });
  es.addEventListener("navigate", (e) => { const d = JSON.parse(e.data); if (d.route !== location.pathname) history.pushState({}, "", d.route + location.search); S.route = d.route; });
  es.onerror = () => { if (es.readyState === 2) setTimeout(connect, 1500); };
}
const titleOf = (scene) => [scene && (scene.props.title || scene.props.brand), S.app.name].filter(Boolean).filter((v, i, a) => a.indexOf(v) === i).join(" · ");

// ---------------------------------------------------------------- forms and events
const elOf = (id) => root.querySelector(`[data-fl-id="${CSS.escape(id)}"]`);
function readForm(scope) {
  const values = {}, fields = [];
  if (!scope) return { values, fields };
  for (const el of scope.querySelectorAll("input[name], textarea[name], select[name]")) {
    if (el.closest(".fl-smartpaste, .fl-nlq, .fl-intent, .fl-copilot, .fl-gen-foot")) continue;
    let v = el.value;
    if (el.type === "checkbox") v = el.checked;
    else if (el.type === "file") continue;
    else if ((el.type === "number" || el.type === "range") && v !== "") v = Number(v);
    else if (el.type === "hidden" && /^\[.*\]$/.test(v)) { try { v = JSON.parse(v); } catch (e) { /* keep text */ } }
    values[el.name] = v;
    if (!fields.includes(el.name)) fields.push(el.name);
  }
  return { values, fields };
}
function formOf(node) {
  const el = node && elOf(node.id);
  return readForm(el ? (el.matches("[data-fl-form]") ? el : el.closest("[data-fl-form]") || el.querySelector("[data-fl-form]") || root) : root);
}
function send(name, node, extra) {
  S.events.push(name);
  document.body.dataset.events = S.events.join(",");
  return post("event", Object.assign({ name, target: node ? node.id : null, value: null, payload: null, form: node ? formOf(node).values : {} }, extra));
}
// Client-side state for portable logic, kept per route so every page starts from its own State.
const stores = new Map();
function localStore() { if (!stores.has(S.route)) stores.set(S.route, createStore()); return stores.get(S.route); }
function runLocal(binding, node, detail) {
  const store = localStore(), value = detail.value === undefined ? null : detail.value;
  runActions(binding.action, { state: store.state, scope: Object.assign({}, node.scope, { value, payload: binding.payload === undefined ? null : binding.payload, form: formOf(node).values }) }, {
    navigate, toast, changed: rerender, emit: (name, payload) => send(name, node, { value, payload: payload === undefined ? null : payload }),
    ask: (capability, input) => invoke(capability, input || {}).then((res) => (res && res.ok ? res.data : { error: res && res.error ? res.error.message : "The request failed." })),
    error: (message) => { if (S.dev) toast("Action: " + message, "warning"); } });
}
function emit(node, event, detail = {}) {
  const binding = node.on && node.on[event];
  if (!binding) return false;
  if (isLocal(binding)) { runLocal(binding, node, detail); return true; }
  send(binding.action, node, { value: detail.value === undefined ? null : detail.value, payload: binding.payload === undefined ? (detail.payload ?? null) : binding.payload });
  return true;
}
function press(node, e) {
  signal("click", node.id);
  if (emit(node, "click")) return;
  const form = e.currentTarget.closest("form");
  if (form && node.props.variant === "primary") form.requestSubmit();
}
function fieldInput(node) { const el = elOf(node.id); return el && (el.matches("input,textarea,select") ? el : el.querySelector("input:not([type=hidden]),textarea,select")); }
function setField(node, value) {
  const el = fieldInput(node);
  S.values.set(node.id, value);
  if (el) { el.value = value; el.classList.add("fl-ai-filled"); setTimeout(() => el.classList.remove("fl-ai-filled"), 1600); }
  rerender();
}
function setFieldByName(node, name, value) {
  const el = elOf(node.id), scope = el ? el.closest("[data-fl-form]") || (el.matches("[data-fl-form]") ? el : el.querySelector("[data-fl-form]")) || root : root;
  const target = scope.querySelector(`[name="${CSS.escape(name)}"]`);
  if (!target) return false;
  if (target.type === "checkbox") target.checked = value === true || value === "true"; else target.value = value;
  target.classList.add("fl-ai-filled"); setTimeout(() => target.classList.remove("fl-ai-filled"), 1600);
  const host = target.closest("[data-fl-id]");
  if (host) S.values.set(host.dataset.flId, value);
  return true;
}
const timers = new Map();
const debounce = (key, ms, fn) => { clearTimeout(timers.get(key)); timers.set(key, setTimeout(fn, ms)); };
function bindings(node, present) { return arr(node.ai).map((b) => [b, S.catalog && S.catalog[b.capability]]).filter(([, cap]) => cap && (!present || cap.present === present)); }
function runBinding(node, b, cap, extra, force) {
  const st = aiState(node.id), input = buildInput(cap, node, ctx, b.options, extra);
  if (!input) return;
  const sig = JSON.stringify(input);
  if (!force && st.sig[cap.id] === sig) return;
  st.sig[cap.id] = sig; st.busy[cap.id] = true; rerender();
  return invoke(cap.id, input).then((res) => {
    st.busy[cap.id] = false; st.results[cap.id] = res;
    const d = res && res.ok ? res.data : null;
    if (d && cap.present === "fill" && node.type !== "Table") {
      if (arr(d.fields).length && node.type !== "Form") { let count = 0; d.fields.forEach((x) => { if (setFieldByName(node, x.name, x.value)) count++; }); st.filled = count; }
      else if (typeof d.value === "string" && d.value && (d.confidence === undefined || d.confidence >= 0.5) && (d.changed === undefined || d.changed)) setField(node, d.value);
      else if (typeof d.text === "string" && d.detected && d.detected !== "en" && d.text) setField(node, d.text);
    }
    rerender();
    return res;
  });
}
function fieldEvents(node, mode) {
  const ghosts = () => bindings(node, "ghost");
  return {
    oninput: (e) => {
      const value = e.target.value, st = aiState(node.id);
      S.values.set(node.id, value); signal("input", node.id);
      if (st.ghost) { st.ghost = null; rerender(); }
      if (node.on && node.on.input) { if (isLocal(node.on.input)) emit(node, "input", { value }); else debounce("in:" + node.id, 250, () => emit(node, "input", { value })); }
      const g = ghosts()[0];
      if (g && value.trim().length >= 2) debounce("gh:" + node.id, 320, () => {
        const input = buildInput(g[1], node, ctx, g[0].options, { text: value });
        if (input) invoke(g[1].id, input).then((res) => { if (res && res.ok && res.data.completion && e.target.value === value) { st.ghost = { typed: value, rest: res.data.completion, prov: res.provenance }; rerender(); } });
      });
      if (mode === "search") bindings(node, "suggest").forEach(([b, cap]) => debounce("sg:" + node.id + cap.id, 300, () => runBinding(node, b, cap, { query: value, text: value }, true)));
    },
    onkeydown: (e) => {
      const st = aiState(node.id);
      if (st.ghost && (e.key === "Tab" || (e.key === "ArrowRight" && e.target.selectionStart === e.target.value.length))) {
        e.preventDefault(); e.target.value = st.ghost.typed + st.ghost.rest; S.values.set(node.id, e.target.value); st.ghost = null; signal("shortcut", node.id, "ghost-accept"); rerender();
      } else if (e.key === "Escape" && st.ghost) { st.ghost = null; rerender(); }
      else if (e.key === "Enter" && e.target.tagName === "INPUT" && (emit(node, mode === "search" ? "search" : "submit", { value: e.target.value }))) e.preventDefault();
    },
    onchange: (e) => { S.values.set(node.id, e.target.value); emit(node, "change", { value: e.target.type === "number" && e.target.value !== "" ? Number(e.target.value) : e.target.value }); },
    onblur: (e) => {
      const value = e.target.value;
      if (!String(value).trim()) return;
      arr(node.ai).forEach((b) => { const cap = S.catalog && S.catalog[b.capability]; if (cap && ["validate", "fill", "suggest"].includes(cap.present) && node.type !== "Form") runBinding(node, b, cap, { text: value, value }); });
    },
  };
}

// ---------------------------------------------------------------- local state
function state(id, init) { if (!S.ui.has(id)) S.ui.set(id, Object.assign({}, init)); return S.ui.get(id); }
function set(id, patchObj) { S.ui.set(id, Object.assign(S.ui.get(id) || {}, patchObj)); rerender(); }
function aiState(id) { if (!S.ai.has(id)) S.ai.set(id, { results: {}, busy: {}, sig: {} }); return S.ai.get(id); }
function toast(text, tone = "info", action) {
  const item = { id: Math.random().toString(36).slice(2), text, tone, action };
  S.toasts.push(item); rerender();
  setTimeout(() => { S.toasts = S.toasts.filter((t) => t !== item); rerender(); }, action ? 9000 : 4200);
}
function navigate(route) {
  if (!route || /^https?:/i.test(route)) { if (route) location.href = route; return; }
  if (route.startsWith("#")) return;
  history.pushState({}, "", route + location.search); S.route = route; signal("nav", route);
  post("event", { name: "@route", value: route });
}
function applyTokens(tokens) { for (const t of arr(tokens)) { if (t.name === "--fl-scheme") document.documentElement.dataset.scheme = S.scheme = t.value; else if (/^--fl-[\w-]+$/.test(t.name)) document.documentElement.style.setProperty(t.name, t.value); } }
const setDensity = (mode) => document.documentElement.style.setProperty("--fl-density", { compact: "0.85", comfortable: "1", spacious: "1.18" }[mode] || "1");
function highlight(id) { const el = elOf(id); if (!el) return; el.scrollIntoView({ block: "center", behavior: "smooth" }); el.classList.add("fl-pulse"); setTimeout(() => el.classList.remove("fl-pulse"), 1800); }
function placeTour(el, target) {
  const t = target && elOf(target), spot = el.querySelector(".fl-tour-spot"), card = el.querySelector(".fl-tour-card");
  if (!t) { spot.style.display = "none"; card.style.cssText = "left:50%;top:30%;transform:translateX(-50%)"; return; }
  const r = t.getBoundingClientRect(); t.scrollIntoView({ block: "nearest" });
  spot.style.cssText = `display:block;left:${r.left - 6}px;top:${r.top - 6}px;width:${r.width + 12}px;height:${r.height + 12}px`;
  const top = r.bottom + 14 + 170 > innerHeight ? Math.max(12, r.top - 184) : r.bottom + 14;
  card.style.cssText = `left:${Math.max(12, Math.min(innerWidth - 332, r.left))}px;top:${top}px`;
}
async function ensureConsent(scope) { const res = await invoke("trust.consent", { scope, grant: true }); return !!(res && res.ok); }
async function media(node, binding, cap) {
  const st = aiState(node.id), input = buildInput(cap, node, ctx, binding.options) || {};
  if (cap.id === "modal.dictate") {
    if (st.recorder) { st.recorder.stop(); return; }
    if (!navigator.mediaDevices || !window.MediaRecorder) return toast("This browser cannot record audio.", "warning");
    if (!(await ensureConsent("microphone"))) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true }).catch(() => null);
    if (!stream) return toast("Microphone access was not granted.", "warning");
    const chunks = [], rec = new MediaRecorder(stream);
    st.recorder = rec; st.busy[cap.id] = true; rerender();
    rec.ondataavailable = (e) => chunks.push(e.data);
    rec.onstop = () => { stream.getTracks().forEach((t) => t.stop()); st.recorder = null; const reader = new FileReader();
      reader.onload = () => invoke(cap.id, { audio: reader.result }).then((res) => { st.busy[cap.id] = false; if (res.ok && res.data.text) setField(node, ((S.values.get(node.id) || "") + " " + res.data.text).trim()); else toast(res.ok ? "Nothing was heard." : res.error.message, "warning"); rerender(); });
      reader.readAsDataURL(new Blob(chunks, { type: rec.mimeType })); };
    rec.start(); setTimeout(() => rec.state === "recording" && rec.stop(), 30000);
    return;
  }
  st.busy[cap.id] = true; rerender();
  const res = await invoke(cap.id, input);
  st.busy[cap.id] = false; rerender();
  if (!res.ok) return toast(res.error.message, "warning");
  const d = res.data;
  if (arr(d.notes).length) {
    const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    const ac = new AC(); d.notes.forEach((nt) => { const o = ac.createOscillator(), g = ac.createGain(); o.frequency.value = nt.freq; o.connect(g); g.connect(ac.destination);
      g.gain.setValueAtTime(0.0001, ac.currentTime + nt.t); g.gain.exponentialRampToValueAtTime(0.18, ac.currentTime + nt.t + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, ac.currentTime + nt.t + nt.dur); o.start(ac.currentTime + nt.t); o.stop(ac.currentTime + nt.t + nt.dur + 0.02); });
    return toast(d.legend, "info");
  }
  if (d.audio) return void new Audio(d.audio).play();
  const text = d.text || input.text;
  if (text && window.speechSynthesis) speechSynthesis.speak(new SpeechSynthesisUtterance(text));
}

// ---------------------------------------------------------------- signals and adaptation
function signal(kind, target, meta) { S.signals.push({ t: Math.round(performance.now() - S.started), kind, target: String(target || ""), meta: meta || "" }); if (S.signals.length - S.sent >= 20) flushSignals(); }
function flushSignals() {
  if (S.sent >= S.signals.length || !S.sid) return;
  const batch = S.signals.slice(S.sent); S.sent = S.signals.length;
  post("signals", { events: batch }).then(observe);
}
function observe() {
  if (!S.scene || S.signals.length - S.observed < 8) return;
  S.observed = S.signals.length;
  const seen = new Set();
  (function walk(n) { bindings(n, "observe").forEach(([b, cap]) => { if (seen.has(cap.id)) return; seen.add(cap.id);
    invoke(cap.id, buildInput(cap, n, ctx, b.options, { items: arr(n.props.nav).map((x) => x.label) }) || {}).then((res) => {
      if (!res.ok) { if (res.error.code === "consent_required" && !S.consentAsked.has(cap.consent)) { S.consentAsked.add(cap.consent); toast("Allow this app to adapt to how you use it?", "ai", { label: "Allow", run: () => ensureConsent(cap.consent) }); } return; }
      const d = res.data;
      if (d.found && d.pitch) toast(d.pitch, "ai");
      arr(d.directives).forEach((x) => {
        if (x.kind === "density") setDensity(x.value);
        else if (x.kind === "offer_help" || x.kind === "offer_tour" || x.kind === "suggest_break" || x.kind === "offer_search") toast(x.reason, "ai");
        else if (x.kind === "explain_target" && x.target) highlight(x.target);
        else if (x.kind === "show_hints") document.documentElement.dataset.hints = "on"; else if (x.kind === "hide_hints") document.documentElement.dataset.hints = "off";
      });
    }); }); arr(n.children).forEach(walk); })(S.scene);
}
function afterScene() { if (params.get("autopilot") && !S.piloted) { S.piloted = true; setTimeout(autopilot, 250); } }
async function autopilot() {
  let steps = [];
  try { steps = JSON.parse(atob(params.get("autopilot").replace(/-/g, "+").replace(/_/g, "/"))); } catch (e) { document.body.dataset.autopilot = "invalid"; return; }
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  for (const step of steps) {
    const host = step.target ? elOf(step.target) : null, el = host && (host.matches("input,textarea,select,button,a") ? host : host.querySelector("input:not([type=hidden]),textarea,select,button,a") || host);
    if (step.do === "wait") await wait(Number(step.value) || 200);
    else if (!el) { document.body.dataset.autopilot = "missing:" + step.target; return; }
    else if (step.do === "click") el.click();
    else if (step.do === "type" || step.do === "select") { el.focus(); el.value = step.value; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); if (step.blur !== false) el.dispatchEvent(new Event("blur")); }
    else if (step.do === "key") el.dispatchEvent(new KeyboardEvent("keydown", { key: step.value, bubbles: true }));
    else if (step.do === "submit") (el.closest("form") || el).requestSubmit();
    await wait(Number(step.pause) || 140);
  }
  await wait(350);
  document.body.dataset.autopilot = "done";
}

// ---------------------------------------------------------------- context and view
const ctx = { catalog: null, values: S.values, get route() { return S.route; }, get live() { return true; }, get local() { return localStore(); }, locale: navigator.language || "en-US",
  state, set, aiState, emit, press, rerender, invoke, navigate, toast, fieldEvents, formOf, setField, setFieldByName, applyTokens, setDensity, highlight, placeTour, media, signal,
  slots: (node) => slotsFor(node, ctx), setValue: (node, value) => S.values.set(node.id, value), event: (action, payload, node) => send(action, node, { payload: payload === undefined ? null : payload }),
  copy: (text) => navigator.clipboard && navigator.clipboard.writeText(text).then(() => toast("Copied", "success")), startTour: (steps) => { S.tour = { steps }; S.ui.delete("@tour"); rerender(); },
  dictate: (node) => { const target = node.props.target && root.querySelector(`[name="${CSS.escape(node.props.target)}"]`); const host = target && target.closest("[data-fl-id]"); const cap = S.catalog["modal.dictate"];
    if (host && cap) media({ id: host.dataset.flId, props: {}, type: "TextArea" }, { options: {} }, cap); },
  file: (node, file) => { const reader = new FileReader(); reader.onload = () => { S.values.set(node.id, reader.result); arr(node.ai).forEach((b) => { const cap = S.catalog[b.capability]; if (cap) runBinding(node, b, cap, { image: reader.result, filename: file.name }, true); }); emit(node, "drop", { value: file.name }); }; reader.readAsDataURL(file); } };

function devPanel() {
  const d = S.devdata;
  if (!d) return h("aside", { class: "fl-dev" }, h("div", { class: "fl-dev-head" }, "Fluidian DevTools"), h("div", { class: "fl-dev-body" }, "Loading…"));
  const tab = state("@dev", { tab: "scene" }).tab, tabs = [["scene", "Scene"], ["review", "Review"], ["ai", "AI ledger"], ["kernel", "Kernel"]];
  const kv = (rows) => h("dl", { class: "fl-kv" }, rows.map(([k, v]) => h("div", { class: "fl-kv-row" }, h("dt", null, k), h("dd", null, String(v)))));
  let body;
  if (tab === "scene") body = [kv([["Route", d.route], ["Nodes", d.stats.nodes], ["Depth", d.stats.depth], ["AI bindings", d.stats.aiBindings], ["Registered actions", arr(d.actions).map((a) => a.name).join(", ") || "none"], ["SDK", `${d.app.sdk || "static"} ${d.app.sdkVersion || ""}`]]),
    arr(d.fixes).length ? h("div", { class: "fl-callout fl-tone-warning" }, icon("alert", 16), h("div", { class: "fl-callout-main" }, h("div", { class: "fl-callout-title" }, `${d.fixes.length} scene repairs`), d.fixes.slice(0, 6).map((f) => h("div", { class: "fl-callout-body" }, f)))) : null, h("pre", { class: "fl-pre fl-dev-digest" }, d.digest)];
  else if (tab === "review") body = [["Usability", d.ux], ["Accessibility", d.a11y], ["Structure", d.lint]].map(([name, rep]) => rep && h("div", null, h("div", { class: "fl-dev-sub" }, name), reportView(rep, null, ctx)));
  else if (tab === "ai") body = h("table", { class: "fl-table is-dense" }, h("thead", null, h("tr", null, ["Capability", "Provider", "ms", ""].map((x) => h("th", null, x)))), h("tbody", null, arr(d.ledger).map((e) => h("tr", null, h("td", null, e.capability), h("td", null, e.provider + (e.model ? " · " + e.model : "")), h("td", { class: "align-end" }, String(e.latencyMs)), h("td", null, e.cached ? "cached" : e.ok ? "" : "failed")))));
  else body = [kv([["Provider", d.live ? "OpenAI (live)" : "Reflex (offline)"], ["Calls", d.telemetry.totals.calls], ["Cache hit rate", Math.round(d.cache.hitRate * 100) + "%"], ["Tokens in / out", `${d.telemetry.totals.tokensIn} / ${d.telemetry.totals.tokensOut}`], ["Session budget left", d.budget.session.remaining], ["Signals", d.signals]]),
    h("div", { class: "fl-dev-sub" }, "Model routing"), kv(d.router.tiers.map((t) => [t.tier, t.model]))];
  return h("aside", { class: "fl-dev" }, h("div", { class: "fl-dev-head" }, fluidianMark(20), "DevTools", h("span", { class: "fl-grow" }), h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Refresh", onclick: loadDev }, icon("refresh", 14)),
    h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Close", onclick: () => { S.dev_open = false; rerender(); } }, icon("x", 14))),
    h("div", { class: "fl-tablist" }, tabs.map(([id, label]) => h("button", { class: cx("fl-tab", tab === id && "is-active"), type: "button", onclick: () => set("@dev", { tab: id }) }, label))), h("div", { class: "fl-dev-body" }, body));
}
function loadDev() { fetch(`/_fluidian/devtools?sid=${S.sid}&token=${encodeURIComponent(S.token)}`).then((r) => r.json()).then((d) => { S.devdata = d; rerender(); }); }
// A Theme at the root of the scene themes the whole document, so overlays and toasts match the page.
function applyRootTheme() {
  // A theme asked for in the address (?theme=, or the theme attribute of <fluidian-app>) wins over the scene's own.
  const de = document.documentElement, asked = THEMES[params.get("theme")] ? params.get("theme") : "";
  const p = !asked && S.scene && S.scene.type === "Theme" ? S.scene.props : null, name = asked || (p && THEMES[p.preset] ? p.preset : "");
  if ((de.dataset.flTheme || "") !== name) { if (name) de.dataset.flTheme = name; else delete de.dataset.flTheme; }
  const scheme = p && (p.scheme === "light" || p.scheme === "dark") ? p.scheme : name ? THEMES[name] : S.scheme;
  if ((de.dataset.scheme || "") !== (scheme || "")) { if (scheme) de.dataset.scheme = scheme; else delete de.dataset.scheme; }
}
/** The platform skin: an explicit ?platform= wins, then the host shell's hint, then the user agent. */
function detectPlatform() {
  const asked = params.get("platform") || (window.FluidianHost && window.FluidianHost.platform) || "", ua = navigator.userAgent || "";
  if (["ios", "android", "web", "desktop"].includes(asked)) return asked;
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return "ios";
  if (/Android/.test(ua)) return "android";
  return "web";
}
function view() {
  applyRootTheme();
  return h("div", { class: cx("fl-app", S.dev_open && "has-dev") },
    S.scene ? renderNode(S.scene, ctx) : h("div", { class: "fl-boot" }, h("span", { class: "fl-orb" })),
    S.tour ? R.Tour({ id: "@tour", props: { steps: S.tour.steps, active: true }, on: {} }, Object.assign({}, ctx, { emit: () => { S.tour = null; rerender(); } })) : null,
    S.pop ? h("div", { class: "fl-pop", style: { left: S.pop.x + "px", top: S.pop.y + "px" } }, h("button", { class: "fl-iconbtn fl-pop-x", type: "button", "aria-label": "Close", onclick: () => { S.pop = null; rerender(); } }, icon("x", 13)), S.pop.res ? (S.pop.res.ok ? genericView(S.pop.res.data, S.pop.res.provenance) : h("div", { class: "fl-ai-msg is-warning" }, S.pop.res.error.message)) : h("span", { class: "fl-ai-busy" }, h("span", { class: "fl-spinner" }), "Looking…")) : null,
    h("div", { class: "fl-toasts", role: "status", "aria-live": "polite" }, S.toasts.map((t) => h("div", { class: `fl-toast fl-tone-${t.tone}`, key: t.id }, icon(t.tone === "success" ? "check" : t.tone === "ai" ? "sparkles" : t.tone === "danger" || t.tone === "warning" ? "alert" : "info", 16), h("span", null, t.text),
      t.action ? h("button", { class: "fl-chip is-ai", type: "button", onclick: () => { t.action.run(); S.toasts = S.toasts.filter((x) => x !== t); rerender(); } }, t.action.label) : null))),
    S.dev && S.fixes.length && !S.dev_open && params.get("bare") !== "1" ? h("button", { class: "fl-fixes", type: "button", onclick: () => { S.dev_open = true; loadDev(); rerender(); } }, icon("alert", 13), `${S.fixes.length} scene repair${S.fixes.length === 1 ? "" : "s"}`) : null,
    S.palette ? palette() : null,
    S.dev_open ? devPanel() : null);
}
// The built-in command palette: an Intent Bar over the page, offered whenever the scene has none of its own.
function palette() {
  const suggestions = arr(S.actions).slice(0, 6).map((a) => ({ label: a.description || String(a.name).replace(/_/g, " "), detail: [a.name].concat(Object.keys(a.params || {})).join(" · "), icon: "bolt" }));
  const close = () => { S.palette = false; rerender(); };
  const focus = (el) => { const input = el.querySelector("[data-fl-intent]"); if (input && document.activeElement !== input) input.focus(); };
  return h("div", { class: "fl-overlay is-palette", onclick: (e) => { if (e.target === e.currentTarget) close(); }, hook: { mount: focus } },
    h("div", { class: "fl-palette", role: "dialog", "aria-modal": "true", "aria-label": "Command palette" },
      R.IntentBar({ type: "IntentBar", id: "@palette", props: { open: true, suggestions, placeholder: "What would you like to do?" }, on: {} }, ctx)));
}

// ---------------------------------------------------------------- boot
async function boot() {
  if (params.get("theme") === "dark") document.documentElement.dataset.scheme = S.scheme = "dark";
  else if (THEMES[params.get("theme")]) { document.documentElement.dataset.flTheme = params.get("theme"); document.documentElement.dataset.scheme = S.scheme = THEMES[params.get("theme")]; }
  document.documentElement.dataset.flPlatform = detectPlatform();
  if (params.get("density")) setDensity(params.get("density"));
  const session = await fetch("/_fluidian/session", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ route: location.pathname, locale: navigator.language, viewport: { w: innerWidth, h: innerHeight } }) }).then((r) => r.json());
  Object.assign(S, { sid: session.sid, token: session.token, app: session.app || S.app, live: session.live, dev: session.dev, actions: session.actions || [] });
  const cat = await fetch("/_fluidian/capabilities").then((r) => r.json());
  S.catalog = ctx.catalog = Object.fromEntries(cat.capabilities.map((c) => [c.id, c]));
  document.documentElement.dataset.provider = S.live ? "openai" : "reflex";
  connect();
  setInterval(flushSignals, 4000);
  addEventListener("popstate", () => { S.route = location.pathname; post("event", { name: "@route", value: S.route }); });
  addEventListener("pagehide", () => navigator.sendBeacon && S.sid && fetch("/_fluidian/close", { method: "POST", keepalive: true, headers: { "Content-Type": "application/json", "X-Fluidian-Token": S.token }, body: JSON.stringify({ sid: S.sid }) }));
  addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      const el = root.querySelector(".fl-page [data-fl-intent]");
      if (el && !S.palette) el.focus(); else { S.palette = !S.palette; rerender(); }
      signal("shortcut", "intent-bar");
    }
    else if (e.key === "Escape" && S.palette) { S.palette = false; rerender(); }
    else if ((e.metaKey || e.ctrlKey) && e.key === "." && S.dev) { e.preventDefault(); S.dev_open = !S.dev_open; if (S.dev_open) loadDev(); rerender(); }
    else if (e.key === "Escape" && S.pop) { S.pop = null; rerender(); }
  });
  root.addEventListener("click", (e) => {
    const host = e.target.closest("[data-fl-id]");
    if (e.altKey && host) { e.preventDefault(); e.stopPropagation(); S.pop = { x: Math.min(e.clientX, innerWidth - 360), y: Math.min(e.clientY + 12, innerHeight - 220), res: null }; rerender();
      invoke("command.point_ask", { target: host.dataset.flId }).then((res) => { if (S.pop) { S.pop.res = res; rerender(); } }); return; }
    if (!e.target.closest("button,a,input,select,textarea,label,[role=tab]") && host) signal("deadclick", host.dataset.flId);
  }, true);
  root.addEventListener("focusin", (e) => { const host = e.target.closest("[data-fl-id]"); if (host && e.target.matches("input,textarea,select")) S.values.set(host.dataset.flId, e.target.value); });
  window.__fluidian = { errors: () => S.errors.slice(), fixes: () => S.fixes.slice(), route: () => S.route, sid: () => S.sid, state: () => JSON.parse(JSON.stringify(localStore().state)) };
  window.addEventListener("error", (e) => { S.errors.push({ message: e.message, stack: e.error && e.error.stack ? String(e.error.stack) : "" }); if (S.dev) toast("Runtime error: " + e.message, "danger"); });
}
/** Installed-app plumbing: a service worker for the shell, and size and route reports for a page that embeds this one. */
function host() {
  if ("serviceWorker" in navigator && params.get("sw") !== "off" && (location.protocol === "https:" || ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname))) {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
  }
  if (window.parent === window) return;
  document.documentElement.dataset.flEmbed = "1";
  const tell = (type, detail) => window.parent.postMessage(Object.assign({ source: "fluidian", type }, detail), "*");
  let last = 0;
  const measure = () => { const height = Math.ceil(root.getBoundingClientRect().height); if (height && height !== last) tell("resize", { height: last = height }); };
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(measure).observe(root);
  addEventListener("load", measure);
  let route = null;
  setInterval(() => { if (S.route !== route && S.scene) { tell(route === null ? "ready" : "navigate", { route: S.route }); route = S.route; measure(); } }, 250);
}
function offline(err) {
  root.replaceChildren(h("div", { class: "fl-offline", role: "status" }, h("span", { class: "fl-orb" }),
    h("strong", null, navigator.onLine === false ? "You are offline" : "The application is not reachable"),
    h("span", null, navigator.onLine === false ? "This screen will come back as soon as the connection does." : String(err && err.message || "Trying again shortly.")),
    h("button", { class: "fl-btn is-primary", type: "button", onclick: () => location.reload() }, "Try again")));
  addEventListener("online", () => location.reload(), { once: true });
}
boot().then(host).catch(offline);
