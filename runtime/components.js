// Fluidian runtime — component renderers.
// Every renderer is a pure function (node, ctx) → virtual node, so the same
// code paints the browser DOM and produces HTML strings on the server.
import { h, cx } from "./core.js";
import { ICONS } from "./icons.js";
import { evaluate, hasBindings, resolve } from "./logic.js";
import { FLUIDIAN_MARK } from "./brand.js";

export const R = {};

// Fluidian's own mark, the ribbon F on its ink tile: the gallery's rail, DevTools, and logo="fluidian" on NavBar and Footer.
export function fluidianMark(size = 28) {
  const m = FLUIDIAN_MARK, stops = (list) => list.map(([offset, colour]) => h("stop", { offset, "stop-color": colour }));
  return h("svg", { class: "fl-fluidian-mark", width: size, height: size, viewBox: "0 0 64 64", role: "img", "aria-label": "Fluidian" },
    h("defs", null, h("linearGradient", { id: "fl-mark-t", x1: 0, y1: 0, x2: 1, y2: 1 }, stops(m.tile)),
      h("linearGradient", { id: "fl-mark-g", gradientUnits: "userSpaceOnUse", x1: 16, y1: 13, x2: 46, y2: 50 }, stops(m.ribbon))),
    h("rect", { x: 0.75, y: 0.75, width: 62.5, height: 62.5, rx: 16.5, fill: "url(#fl-mark-t)", stroke: "rgba(255, 255, 255, 0.22)", "stroke-width": 1.5 }),
    h("g", { fill: "none", stroke: "url(#fl-mark-g)", "stroke-width": m.weight, "stroke-linecap": "round", "stroke-linejoin": "round" }, h("path", { d: m.stem }), h("path", { d: m.wave })));
}
const isFluidian = (brand) => /^fluidian\b/i.test(String(brand || ""));
const GAP = { none: "0", xs: "4px", sm: "8px", md: "16px", lg: "24px", xl: "40px" };
const ALIGN = { start: "flex-start", center: "center", end: "flex-end", stretch: "stretch", baseline: "baseline", between: "space-between" };
const arr = (v) => (Array.isArray(v) ? v : []);
const str = (v) => (v === null || v === undefined ? "" : String(v));

export function icon(name, size = 18, cls = "") {
  const d = ICONS[name] || ICONS.sparkles;
  return h("svg", { class: cx("fl-icon", cls), width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
    "stroke-width": "1.8", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" }, h("path", { d }));
}

export function fmt(value, style, locale = "en-US") {
  if (value === null || value === undefined || value === "") return "";
  const n = typeof value === "number" ? value : Number(String(value).replace(/[$€£,%\s]/g, ""));
  try {
    if (style === "date") {
      // A date without a time is a calendar day, not an instant: build it in local time so it never shifts across midnight.
      const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value));
      const d = day ? new Date(Number(day[1]), Number(day[2]) - 1, Number(day[3])) : new Date(value);
      return isNaN(d) ? String(value) : d.toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric" });
    }
    if (!isFinite(n) || style === "text" || style === "badge" || !style) return String(value);
    if (style === "currency") { const cents = Number.isInteger(n) && Math.abs(n) >= 100 ? 0 : 2; return new Intl.NumberFormat(locale, { style: "currency", currency: "USD", minimumFractionDigits: cents, maximumFractionDigits: cents }).format(n); }
    if (style === "percent") return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(n) + "%";
    if (style === "compact") return new Intl.NumberFormat(locale, { notation: "compact", maximumFractionDigits: 1 }).format(n);
    return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(n);
  } catch (e) { return String(value); }
}

const TONE_OF = [[/^(paid|active|success|complete|completed|done|approved|healthy|online|delivered|resolved|live|won)$/i, "success"],
  [/^(pending|review|waiting|in progress|processing|trial|scheduled|draft|partial)$/i, "warning"],
  [/^(failed|overdue|error|rejected|blocked|cancelled|canceled|churned|critical|offline|expired|lost)$/i, "danger"], [/^(new|info|open|invited|queued|beta)$/i, "info"]];
export const toneOf = (label) => (TONE_OF.find(([re]) => re.test(String(label).trim())) || [0, "neutral"])[1];
export function primaryText(node) {
  const p = node.props || {};
  for (const k of ["title", "label", "text", "content", "brand", "name", "intent", "placeholder"]) if (typeof p[k] === "string" && p[k].trim()) return p[k];
  return "";
}

// Scenes are normalised by the engine, but list props can still carry holes (a model may emit `null` rows).
// Lists are cleaned once per props object so no renderer has to defend against missing records.
const CLEAN = new WeakMap();
const plain = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
function cleanList(list, depth) {
  const present = list.filter((x) => x !== null && x !== undefined);
  const records = present.filter(plain);
  let out = records.length && records.length * 2 >= present.length ? records : present;
  let changed = out.length !== list.length;
  if (depth < 3) {
    out = out.map((item) => {
      if (!plain(item)) return item;
      let copy = item;
      for (const key in item) {
        if (!Array.isArray(item[key])) continue;
        const cleaned = cleanList(item[key], depth + 1);
        if (cleaned !== item[key]) { if (copy === item) copy = Object.assign({}, item); copy[key] = cleaned; changed = true; }
      }
      return copy;
    });
  }
  return changed ? out : list;
}
function cleanProps(props) {
  if (!plain(props)) return {};
  let cleaned = CLEAN.get(props);
  if (cleaned) return cleaned;
  cleaned = props;
  for (const key in props) {
    if (!Array.isArray(props[key])) continue;
    const list = cleanList(props[key], 0);
    if (list !== props[key]) { if (cleaned === props) cleaned = Object.assign({}, props); cleaned[key] = list; }
  }
  CLEAN.set(props, cleaned);
  return cleaned;
}

// Portable logic: `State` seeds client state, `{{ }}` bindings read it, `Show` and `Each` shape the tree.
// A node rendered inside `Each` carries its scope (`item`, `index`) so its actions can read it too.
const LITERAL = new Set(["Code", "Terminal"]); // source text is shown as written, never interpolated
function bind(node, ctx) {
  const env = { state: ctx.local ? ctx.local.state : {}, scope: ctx.scope || {} };
  let props = node.props;
  if (!LITERAL.has(node.type) && hasBindings(props)) props = resolve(props, env);
  if (typeof props.bind === "string" && props.bind) {
    const value = evaluate(props.bind, env), set = { action: `@${props.bind} = value` };
    props = Object.assign({}, props, typeof value === "boolean" ? { checked: value } : { value: value === undefined || value === null ? "" : value });
    node = Object.assign({}, node, { on: Object.assign({ input: set, change: set }, node.on) });
  }
  return props === node.props && !ctx.scope && !ctx.suffix ? node : Object.assign({}, node, { props, scope: ctx.scope, id: ctx.suffix ? node.id + ctx.suffix : node.id });
}
export function renderNode(node, ctx) {
  if (node.type === "State") { if (ctx.local) ctx.local.declare(node.props.values); return null; }
  node = bind(node, ctx);
  const env = { state: ctx.local ? ctx.local.state : {}, scope: ctx.scope || {} };
  if (node.type === "Show") return evaluate(node.props.when, env) ? h("div", { class: "fl-show", key: node.id, "data-fl-id": node.id }, arr(node.children).map((c) => renderNode(c, ctx))) : null;
  if (node.type === "Each") {
    const items = arr(typeof node.props.items === "string" ? evaluate(node.props.items, env) : node.props.items), name = /^[A-Za-z_]\w*$/.test(node.props.as || "") ? node.props.as : "item";
    const rows = items.slice(0, 500).map((item, index) => { const sub = Object.assign(Object.create(ctx), { scope: Object.assign({}, ctx.scope, { [name]: item, index }), suffix: (ctx.suffix || "") + "#" + index }); return arr(node.children).map((c) => renderNode(c, sub)); });
    if (!items.length && node.props.empty) rows.push(h("div", { class: "fl-each-empty" }, str(node.props.empty)));
    return h("div", { class: cx("fl-each", `is-${node.props.layout || "stack"}`), key: node.id, "data-fl-id": node.id }, rows);
  }
  const safe = cleanProps(node.props);
  if (safe !== node.props) node = Object.assign({}, node, { props: safe });
  const fn = R[node.type] || R.Unknown;
  const slots = ctx.slots ? ctx.slots(node) : null;
  if (slots && slots.props) node = Object.assign({}, node, { props: Object.assign({}, node.props, slots.props) });
  let v = fn(node, ctx, slots);
  if (!v || typeof v !== "object") return v;
  v.attrs["data-fl-id"] = node.id;
  v.attrs["data-fl-type"] = node.type;
  if (slots && slots.attrs) Object.assign(v.attrs, slots.attrs);
  if (slots && !slots.used && (slots.inline.length || slots.below.length)) {
    v = h("div", { class: cx("fl-ai-wrap", slots.inline.length && "has-actions") }, v,
      slots.inline.length ? h("div", { class: "fl-ai-actions" }, slots.inline) : null, slots.below);
  }
  v.key = v.attrs.key = node.id;
  return v;
}
const kids = (node, ctx) => arr(node.children).map((c) => renderNode(c, ctx));
const badge = (label, tone = "neutral", variant = "soft", extra) => h("span", { class: `fl-badge fl-tone-${tone} is-${variant}` }, extra, str(label));

// --- layout -----------------------------------------------------------------
R.State = () => null;
R.Show = R.Each = (n, c) => h("div", { class: "fl-show" }, kids(n, c));
R.Unknown = (n) => h("div", { class: "fl-unknown" }, `Unknown component: ${n.type}`);
R.Page = (n, c) => {
  const p = n.props;
  return h("main", { class: `fl-page is-${p.width || "default"}` },
    (p.title || p.subtitle || p.eyebrow) ? h("header", { class: "fl-page-head" }, p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow),
      p.title && h("h1", { class: "fl-page-title" }, p.title), p.subtitle && h("p", { class: "fl-page-sub" }, p.subtitle)) : null,
    h("div", { class: "fl-page-body" }, kids(n, c)));
};
R.Shell = (n, c) => {
  const p = n.props, user = p.user || null;
  let section = null;
  const items = [];
  for (const it of arr(p.nav)) {
    if (it.section && it.section !== section) { section = it.section; items.push(h("div", { class: "fl-nav-section", key: "s:" + section }, section)); }
    const active = it.active || (c.route && it.route === c.route);
    items.push(h("a", { class: cx("fl-nav-item", active && "is-active"), href: it.route || "#", key: "n:" + (it.route || it.label), "aria-current": active ? "page" : null,
      onclick: (e) => { e.preventDefault(); c.signal && c.signal("nav", it.label); n.on && n.on.navigate ? c.emit(n, "navigate", { value: it.route }) : c.navigate(it.route); } },
      it.icon && icon(it.icon, 17), h("span", { class: "fl-nav-label" }, it.label), it.badge && h("span", { class: "fl-nav-badge" }, it.badge)));
  }
  return h("div", { class: "fl-shell" },
    h("aside", { class: "fl-rail" },
      h("div", { class: "fl-brand" }, isFluidian(p.brand) ? fluidianMark(28) : h("span", { class: "fl-brand-mark" }), h("div", null, h("div", { class: "fl-brand-name" }, p.brand), p.tagline && h("div", { class: "fl-brand-tag" }, p.tagline))),
      h("nav", { class: "fl-nav", "aria-label": "Primary" }, items),
      user && h("div", { class: "fl-rail-user" }, R.Avatar({ props: { name: user.name, size: "sm" } }), h("div", null, h("div", { class: "fl-user-name" }, user.name), user.role && h("div", { class: "fl-user-role" }, user.role))),
      p.footer && h("div", { class: "fl-rail-foot" }, p.footer)),
    h("div", { class: "fl-shell-main" }, kids(n, c)));
};
const flex = (cls, dir) => (n, c) => {
  const p = n.props;
  return h("div", { class: cx(cls, p.wrap === false && "no-wrap"), style: { gap: GAP[p.gap] || GAP.md, alignItems: ALIGN[p.align] || (dir === "row" ? "center" : null),
    justifyContent: ALIGN[p.justify] || null } }, kids(n, c));
};
R.Stack = flex("fl-stack", "col");
R.Row = flex("fl-row", "row");
R.Toolbar = (n, c) => h("div", { class: "fl-toolbar", style: { justifyContent: ALIGN[n.props.justify || "between"] } }, kids(n, c));
R.Grid = (n, c) => {
  const p = n.props, cols = Math.max(1, Math.min(12, Number(p.columns) || 3));
  return h("div", { class: "fl-grid", style: { gap: GAP[p.gap] || GAP.md, "--fl-cols": cols, "--fl-min": p.minWidth ? p.minWidth + "px" : null }, "data-auto": p.minWidth ? "1" : null }, kids(n, c));
};
R.Split = (n, c) => {
  const p = n.props, parts = String(p.ratio || "1:1").split(":").map((x) => Math.max(1, Number(x) || 1));
  return h("div", { class: "fl-split", style: { gap: GAP[p.gap] || GAP.lg, gridTemplateColumns: parts.map((x) => `minmax(0, ${x}fr)`).join(" ") } }, kids(n, c));
};
R.Card = (n, c) => {
  const p = n.props;
  return h("section", { class: cx("fl-card", `fl-tone-${p.tone || "neutral"}`, p.elevated && "is-elevated", `pad-${p.padding || "md"}`) },
    (p.title || p.subtitle || p.eyebrow) ? h("header", { class: "fl-card-head" }, h("div", null, p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow),
      p.title && h("h3", { class: "fl-card-title" }, p.title), p.subtitle && h("p", { class: "fl-card-sub" }, p.subtitle))) : null,
    h("div", { class: "fl-card-body" }, kids(n, c)));
};
R.Section = (n, c) => h("section", { class: cx("fl-section", n.props.divider && "has-divider") },
  h("header", { class: "fl-section-head" }, h("h2", { class: "fl-section-title" }, n.props.title), n.props.description && h("p", { class: "fl-section-desc" }, n.props.description)),
  h("div", { class: "fl-section-body" }, kids(n, c)));
R.Tabs = (n, c) => {
  const tabs = arr(n.children).filter((t) => t.type === "Tab"), st = c.state(n.id, { active: Number(n.props.active) || 0 });
  const active = Math.min(st.active, Math.max(0, tabs.length - 1));
  return h("div", { class: `fl-tabs is-${n.props.variant || "line"}` },
    h("div", { class: "fl-tablist", role: "tablist" }, tabs.map((t, i) => h("button", { class: cx("fl-tab", i === active && "is-active"), role: "tab", type: "button", key: t.id,
      "aria-selected": String(i === active), "data-fl-id": t.id, onclick: () => { c.set(n.id, { active: i }); c.emit(n, "change", { value: i }); } },
      t.props.icon && icon(t.props.icon, 15), t.props.label, t.props.badge && h("span", { class: "fl-tab-badge" }, t.props.badge)))),
    tabs[active] ? h("div", { class: "fl-tabpanel", role: "tabpanel", key: "panel:" + tabs[active].id }, kids(tabs[active], c)) : null);
};
R.Tab = (n, c) => h("div", { class: "fl-tabpanel" }, kids(n, c));
R.Disclosure = (n, c) => {
  const st = c.state(n.id, { open: !!n.props.open });
  return h("div", { class: cx("fl-disclosure", st.open && "is-open") },
    h("button", { class: "fl-disclosure-head", type: "button", "aria-expanded": String(st.open), onclick: () => { c.set(n.id, { open: !st.open }); c.emit(n, "toggle", { value: !st.open }); } },
      icon("chevron-right", 15, "fl-chevron"), h("span", { class: "fl-disclosure-title" }, n.props.title), n.props.hint && h("span", { class: "fl-disclosure-hint" }, n.props.hint)),
    st.open ? h("div", { class: "fl-disclosure-body" }, kids(n, c)) : null);
};
R.Divider = (n) => h("div", { class: "fl-divider", role: "separator" }, n.props.label && h("span", null, n.props.label));
R.Spacer = (n) => h("div", { class: "fl-spacer", style: { height: GAP[n.props.size] || GAP.md }, "aria-hidden": "true" });
const overlay = (kind) => (n, c) => {
  const p = n.props, st = c.state(n.id, { open: p.open !== false });
  if (!st.open) return h("div", { class: "fl-hidden", hidden: true });
  const close = () => { c.set(n.id, { open: false }); c.emit(n, "close", {}); };
  return h("div", { class: `fl-overlay is-${kind}`, onclick: (e) => { if (e.target === e.currentTarget) close(); } },
    h("div", { class: cx(`fl-${kind}`, `is-${p.size || p.side || "md"}`), role: "dialog", "aria-modal": "true", "aria-label": p.title },
      h("header", { class: "fl-dialog-head" }, h("div", null, h("h2", { class: "fl-dialog-title" }, p.title), p.subtitle && h("p", { class: "fl-card-sub" }, p.subtitle)),
        h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Close", onclick: close }, icon("x", 16))),
      h("div", { class: "fl-dialog-body" }, kids(n, c))));
};
R.Modal = overlay("modal");
R.Drawer = overlay("drawer");
R.Hero = (n, c) => {
  const p = n.props, title = str(p.title), hi = str(p.highlight), at = hi ? title.indexOf(hi) : -1;
  return h("section", { class: `fl-hero is-${p.tone || "plain"} align-${p.align || "start"} size-${p.size || "md"}` },
    p.badge && h("div", { class: "fl-hero-badge" }, p.badgeTag && h("span", { class: "fl-hero-badge-tag" }, p.badgeTag), h("span", null, p.badge), icon("arrow-right", 13)),
    p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow),
    h("h1", { class: "fl-hero-title" }, at < 0 ? title : [title.slice(0, at), h("span", { class: "fl-grad-text" }, hi), title.slice(at + hi.length)]),
    p.subtitle && h("p", { class: "fl-hero-sub" }, p.subtitle), arr(n.children).length ? h("div", { class: "fl-hero-body" }, kids(n, c)) : null);
};
R.Breadcrumbs = (n, c) => h("nav", { class: "fl-crumbs", "aria-label": "Breadcrumb" }, arr(n.props.items).map((it, i, all) => [
  i ? icon("chevron-right", 13, "fl-crumb-sep") : null,
  i === all.length - 1 ? h("span", { class: "fl-crumb is-current", "aria-current": "page" }, it.label)
    : h("a", { class: "fl-crumb", href: it.route || "#", onclick: (e) => { e.preventDefault(); c.navigate(it.route); } }, it.label)]));

// --- content ----------------------------------------------------------------
R.Heading = (n) => {
  const level = Math.max(1, Math.min(4, Number(n.props.level) || 2));
  return h("div", { class: "fl-heading-wrap" }, n.props.eyebrow && h("div", { class: "fl-eyebrow" }, n.props.eyebrow), h("h" + level, { class: `fl-heading is-h${level}` }, n.props.text));
};
R.Text = (n) => h("p", { class: cx("fl-text", `tone-${n.props.tone || "default"}`, `size-${n.props.size || "md"}`, `weight-${n.props.weight || "regular"}`),
  style: { textAlign: n.props.align && n.props.align !== "start" ? n.props.align : null } }, str(n.props.content));

function inline(text) {
  const out = [];
  const re = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)\s]+)\))|(_([^_]+)_)|(\*([^*]+)\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[2]) out.push(h("strong", null, m[2]));
    else if (m[4]) out.push(h("code", { class: "fl-code-inline" }, m[4]));
    else if (m[6]) out.push(/^(https?:\/\/|mailto:|\/|#)/i.test(m[7]) ? h("a", { class: "fl-link", href: m[7], rel: "noopener noreferrer" }, m[6]) : m[6]);
    else out.push(h("em", null, m[9] || m[11]));
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
export function markdown(source) {
  const blocks = [], lines = String(source || "").replace(/\r/g, "").split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) { const buf = []; i++; while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]); i++; blocks.push(h("pre", { class: "fl-pre" }, h("code", null, buf.join("\n")))); continue; }
    const head = /^(#{1,4})\s+(.*)$/.exec(line);
    if (head) { blocks.push(h("h" + Math.min(4, head[1].length + 1), { class: `fl-heading is-h${Math.min(4, head[1].length + 1)}` }, inline(head[2]))); i++; continue; }
    if (/^\s*([-*•]|\d+[.)])\s+/.test(line)) {
      const ordered = /^\s*\d/.test(line), items = [];
      while (i < lines.length && /^\s*([-*•]|\d+[.)])\s+/.test(lines[i])) items.push(h("li", null, inline(lines[i++].replace(/^\s*([-*•]|\d+[.)])\s+/, ""))));
      blocks.push(h(ordered ? "ol" : "ul", { class: "fl-md-list" }, items)); continue;
    }
    if (/^>\s?/.test(line)) { blocks.push(h("blockquote", { class: "fl-quote" }, inline(line.replace(/^>\s?/, "")))); i++; continue; }
    if (!line.trim()) { i++; continue; }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|>\s?|\s*([-*•]|\d+[.)])\s+)/.test(lines[i])) para.push(lines[i++]);
    blocks.push(h("p", { class: "fl-text" }, inline(para.join(" "))));
  }
  return blocks;
}
R.Markdown = (n) => h("div", { class: "fl-markdown" }, markdown(n.props.source));
R.Badge = (n) => badge(n.props.label, n.props.tone, n.props.variant, [n.props.dot && h("span", { class: "fl-dot" }), n.props.icon && icon(n.props.icon, 12)]);
R.Tag = (n, c) => h("span", { class: `fl-tag fl-tone-${n.props.tone || "neutral"}` }, n.props.label,
  n.props.removable && h("button", { class: "fl-tag-x", type: "button", "aria-label": `Remove ${n.props.label}`, onclick: () => c.emit(n, "remove", { value: n.props.label }) }, icon("x", 11)));
R.Icon = (n) => h("span", { class: `fl-icon-wrap fl-tone-${n.props.tone || "neutral"}` }, icon(n.props.name, Number(n.props.size) || 18));
R.Image = (n) => {
  const p = n.props, ratio = /^\d+:\d+$/.test(p.ratio || "") ? p.ratio.replace(":", " / ") : null;
  const safe = /^(https?:|data:image\/|\/|blob:)/i.test(p.src || "") ? p.src : "";
  return h("figure", { class: cx("fl-image", p.rounded !== false && "is-rounded") },
    h("img", { src: safe, alt: str(p.alt), loading: "lazy", style: { aspectRatio: ratio, objectFit: p.fit || "cover" } }), p.caption && h("figcaption", null, p.caption));
};
R.Avatar = (n) => {
  const p = n.props, name = str(p.name), initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
  let hue = 0; for (const ch of name) hue = (hue * 31 + ch.charCodeAt(0)) % 360;
  return h("span", { class: `fl-avatar is-${p.size || "md"}`, title: name, style: { "--fl-avatar-hue": hue } },
    p.src && /^(https?:|data:image\/|\/)/.test(p.src) ? h("img", { src: p.src, alt: name }) : initials, p.status && h("span", { class: `fl-presence is-${p.status}` }));
};
const KEYWORDS = new Set(("import from export default const let var function return if else elif for while in of class extends new try catch except finally throw raise async await def lambda with as pass None True False null true false nil end do then fn pub use mod struct enum impl match package func go defer type interface public private static void int string final val fun when using namespace include local require module self this super not and or is yield break continue switch case").split(" "));
const HASH_LANGS = /^(py|python|rb|ruby|ex|exs|elixir|sh|bash|shell|zsh|yaml|yml|toml|php)$/, DASH_LANGS = /^(lua|sql)$/;
/** A small tokenizer for code blocks: comments, strings, numbers, keywords and calls. */
export function highlight(source, language) {
  const lang = str(language).toLowerCase(), comment = HASH_LANGS.test(lang) ? "#[^\\n]*|" + (lang === "php" ? "\\/\\/[^\\n]*|\\/\\*[\\s\\S]*?\\*\\/" : "(?!)") : DASH_LANGS.test(lang) ? "--[^\\n]*" : "\\/\\/[^\\n]*|\\/\\*[\\s\\S]*?\\*\\/";
  const re = new RegExp("(" + comment + ")|(\"(?:[^\"\\\\\\n]|\\\\.)*\"|'(?:[^'\\\\\\n]|\\\\.)*'|`(?:[^`\\\\]|\\\\.)*`)|(\\b\\d[\\d_]*(?:\\.\\d+)?\\b)|([A-Za-z_$@][\\w$]*)", "g");
  const out = [], text = str(source);
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const cls = m[1] ? "c" : m[2] ? "s" : m[3] ? "n" : KEYWORDS.has(m[4]) ? "k" : text[re.lastIndex] === "(" ? "f" : /^[A-Z]/.test(m[4]) ? "t" : "";
    out.push(cls ? h("span", { class: "tk-" + cls }, m[0]) : m[0]);
    last = re.lastIndex;
    if (!m[0].length) re.lastIndex++;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}
R.Code = (n, c) => h("div", { class: cx("fl-code", n.props.tone === "dark" && "is-dark") },
  h("div", { class: "fl-code-head" }, h("span", null, n.props.title || n.props.language || "code"),
    h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Copy code", onclick: () => c.copy && c.copy(n.props.source) }, icon("copy", 14))),
  h("pre", { class: "fl-pre" }, h("code", null, n.props.plain ? str(n.props.source) : highlight(n.props.source, n.props.language))));
R.Kbd = (n) => h("span", { class: "fl-kbds" }, str(n.props.keys).split("+").map((k) => h("kbd", { class: "fl-kbd" }, k.trim())));
R.Link = (n, c) => h("a", { class: `fl-link tone-${n.props.tone || "brand"}`, href: /^(https?:|mailto:|\/|#)/i.test(n.props.href || "") ? n.props.href : "#",
  target: n.props.external ? "_blank" : null, rel: n.props.external ? "noopener noreferrer" : null,
  onclick: (e) => { if (n.props.external) return; e.preventDefault(); n.on && n.on.navigate ? c.emit(n, "navigate", { value: n.props.href }) : c.navigate(n.props.href); } },
  n.props.label, n.props.external && icon("external", 12));
const TONE_ICON = { info: "info", success: "check", warning: "alert", danger: "alert", ai: "sparkles", brand: "info", neutral: "info" };
R.Callout = (n, c) => {
  const tone = n.props.tone || "info";
  return h("div", { class: `fl-callout fl-tone-${tone}`, role: tone === "danger" ? "alert" : "note" }, icon(n.props.icon || TONE_ICON[tone], 18),
    h("div", { class: "fl-callout-main" }, h("div", { class: "fl-callout-title" }, n.props.title), n.props.body && h("div", { class: "fl-callout-body" }, n.props.body), kids(n, c)));
};
R.Banner = (n, c) => {
  const st = c.state(n.id, { gone: false }), tone = n.props.tone || "brand";
  if (st.gone) return h("div", { hidden: true });
  return h("div", { class: `fl-banner fl-tone-${tone}`, role: "status" }, icon(n.props.icon || TONE_ICON[tone], 16), h("span", null, n.props.text),
    n.props.dismissible && h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Dismiss", onclick: () => { c.set(n.id, { gone: true }); c.emit(n, "dismiss", {}); } }, icon("x", 14)));
};
let sparkSeq = 0;
/** A smooth sparkline with a faded area; `opts.kind = "bar"` draws bars instead. */
export function spark(values, w = 96, hgt = 28, opts = {}) {
  const v = arr(values).map(Number).filter(isFinite);
  if (v.length < 2) return null;
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1, f = (x) => x.toFixed(1);
  if (opts.kind === "bar") {
    const bw = (w - 2) / v.length;
    return h("svg", { class: "fl-spark is-bar", viewBox: `0 0 ${w} ${hgt}`, width: w, height: hgt, "aria-hidden": "true" }, v.map((y, i) => { const bh = Math.max(2, ((y - lo) / span) * (hgt - 4) + 2); return h("rect", { x: f(1 + i * bw), y: f(hgt - bh), width: f(Math.max(1, bw - 1.5)), height: f(bh), rx: 1.2, class: "fl-spark-bar" }); }));
  }
  const pts = v.map((y, i) => [(i / (v.length - 1)) * (w - 4) + 2, hgt - 3 - ((y - lo) / span) * (hgt - 7)]), id = "fl-sp" + (opts.id || ++sparkSeq);
  let d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
  for (let i = 0; i < pts.length - 1; i++) { const a = pts[i], b = pts[i + 1], mx = (a[0] + b[0]) / 2; d += ` C${f(mx)} ${f(a[1])} ${f(mx)} ${f(b[1])} ${f(b[0])} ${f(b[1])}`; }
  const end = pts[pts.length - 1];
  return h("svg", { class: "fl-spark", viewBox: `0 0 ${w} ${hgt}`, width: w, height: hgt, "aria-hidden": "true" },
    h("defs", null, h("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 }, h("stop", { offset: 0, class: "fl-spark-stop-a" }), h("stop", { offset: 1, class: "fl-spark-stop-b" }))),
    opts.area === false ? null : h("path", { d: `${d} L${w - 2} ${hgt} L2 ${hgt} Z`, style: `fill:url(#${id})` }), h("path", { d, class: "fl-spark-line" }),
    opts.dot === false ? null : h("circle", { cx: f(end[0]), cy: f(end[1]), r: "2.4", class: "fl-spark-dot" }));
}
R.Stat = (n) => {
  const p = n.props, trend = p.trend || (/^\+/.test(p.delta || "") ? "up" : /^[-−]/.test(p.delta || "") ? "down" : "flat");
  return h("div", { class: `fl-stat fl-tone-${p.tone || "neutral"}` },
    h("div", { class: "fl-stat-top" }, p.icon && h("span", { class: "fl-stat-icon" }, icon(p.icon, 16)), h("span", { class: "fl-stat-label" }, p.label)),
    h("div", { class: "fl-stat-mid" }, h("span", { class: "fl-stat-value" }, str(p.value)), spark(p.spark, 96, 30, { id: n.id ? n.id.replace(/[^\w-]/g, "_") : undefined })),
    (p.delta || p.hint) ? h("div", { class: "fl-stat-foot" }, p.delta && h("span", { class: `fl-delta is-${trend}` }, icon(trend === "down" ? "trend-down" : trend === "up" ? "trend-up" : "arrow-right", 13), p.delta),
      p.hint && h("span", { class: "fl-stat-hint" }, p.hint)) : null);
};
R.Progress = (n) => {
  const p = n.props, max = Number(p.max) || 100, pct = Math.max(0, Math.min(100, (Number(p.value) || 0) / max * 100));
  return h("div", { class: cx("fl-progress", `fl-tone-${p.tone || "brand"}`, p.indeterminate && "is-indeterminate") },
    (p.label || p.showValue !== false) ? h("div", { class: "fl-progress-head" }, h("span", null, p.label), p.showValue !== false && !p.indeterminate && h("span", { class: "fl-progress-value" }, Math.round(pct) + "%")) : null,
    h("div", { class: "fl-progress-track", role: "progressbar", "aria-valuenow": p.indeterminate ? null : Math.round(pct), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": p.label || "Progress" },
      h("div", { class: "fl-progress-bar", style: { width: p.indeterminate ? "40%" : pct + "%" } })));
};
R.Skeleton = (n) => {
  const p = n.props, shape = p.shape || "text";
  const lines = Math.max(1, Math.min(12, Number(p.lines) || 3));
  if (shape === "text") return h("div", { class: "fl-skeleton is-text", "aria-hidden": "true" }, Array.from({ length: lines }, (_, i) => h("span", { style: { width: i === lines - 1 && lines > 1 ? "62%" : "100%" } })));
  if (shape === "card") return h("div", { class: "fl-skeleton is-card", "aria-hidden": "true" }, h("span", { style: { width: "40%" } }), h("span", { class: "big" }), h("span", { style: { width: "70%" } }));
  return h("div", { class: `fl-skeleton is-${shape}`, style: { height: p.height ? p.height + "px" : null }, "aria-hidden": "true" });
};
R.EmptyState = (n, c) => h("div", { class: "fl-empty" }, h("div", { class: "fl-empty-icon" }, icon(n.props.icon || "inbox", 26)), h("div", { class: "fl-empty-title" }, n.props.title),
  n.props.description && h("p", { class: "fl-empty-desc" }, n.props.description), h("div", { class: "fl-empty-actions" }, kids(n, c)));
R.Timeline = (n) => h("ol", { class: "fl-timeline" }, arr(n.props.items).map((it) => h("li", { class: `fl-timeline-item fl-tone-${it.tone || "neutral"}` },
  h("span", { class: "fl-timeline-dot" }, it.icon && icon(it.icon, 11)), h("div", { class: "fl-timeline-main" },
    h("div", { class: "fl-timeline-head" }, h("span", { class: "fl-timeline-title" }, it.title), it.time && h("time", { class: "fl-timeline-time" }, it.time)), it.detail && h("div", { class: "fl-timeline-detail" }, it.detail)))));
R.Steps = (n) => {
  const cur = Number(n.props.current) || 0;
  return h("ol", { class: `fl-steps is-${n.props.orientation || "horizontal"}` }, arr(n.props.items).map((it, i) => h("li", { class: cx("fl-step", i < cur && "is-done", i === cur && "is-current"), "aria-current": i === cur ? "step" : null },
    h("span", { class: "fl-step-dot" }, i < cur ? icon("check", 12) : String(i + 1)), h("span", { class: "fl-step-text" }, h("span", { class: "fl-step-title" }, it.title), it.detail && h("span", { class: "fl-step-detail" }, it.detail)))));
};
R.KeyValue = (n) => h("dl", { class: "fl-kv", style: { "--fl-cols": Math.max(1, Number(n.props.columns) || 1) } }, arr(n.props.items).map((it) => h("div", { class: "fl-kv-row" }, h("dt", null, it.key != null ? it.key : it.label), h("dd", null, str(it.value)))));
R.List = (n, c) => h("ul", { class: cx("fl-list", n.props.dense && "is-dense", n.props.divided !== false && "is-divided") }, arr(n.props.items).map((it, i) => {
  const body = [it.avatar ? R.Avatar({ props: { name: it.avatar, size: "sm" } }) : it.icon ? h("span", { class: `fl-list-icon fl-tone-${it.tone || "neutral"}` }, icon(it.icon, 16)) : null,
    h("div", { class: "fl-list-main" }, h("div", { class: "fl-list-title" }, it.title), it.detail && h("div", { class: "fl-list-detail" }, it.detail)),
    it.badge && badge(it.badge, it.tone || toneOf(it.badge)), it.meta && h("span", { class: "fl-list-meta" }, it.meta)];
  return n.on && n.on.select ? h("li", null, h("button", { class: "fl-list-row is-action", type: "button", onclick: () => c.emit(n, "select", { value: i }) }, body)) : h("li", { class: "fl-list-row" }, body);
}));
const tree = (items, n, c, depth) => h("ul", { class: "fl-tree", role: depth ? "group" : "tree" }, arr(items).map((it) => h("li", { role: "treeitem" },
  h("span", { class: "fl-tree-row", style: { paddingLeft: 8 + depth * 16 + "px" } }, icon(it.icon || (it.children ? "folder" : "file"), 15), it.label), it.children && n.props.expanded !== false ? tree(it.children, n, c, depth + 1) : null)));
R.Tree = (n, c) => tree(n.props.items, n, c, 0);
R.Blockquote = (n) => h("blockquote", { class: "fl-quote" }, h("p", null, n.props.text), n.props.cite && h("cite", null, "— " + n.props.cite));
R.Thread = (n) => h("div", { class: "fl-thread" }, n.props.title && h("div", { class: "fl-thread-title" }, n.props.title), arr(n.props.messages).map((m) => h("div", { class: "fl-msg" },
  R.Avatar({ props: { name: m.author || "?", size: "sm" } }), h("div", { class: "fl-msg-main" }, h("div", { class: "fl-msg-head" }, h("span", { class: "fl-msg-author" }, m.author), m.time && h("time", null, m.time), m.tone && badge(m.tone, toneOf(m.tone) === "neutral" ? m.tone : toneOf(m.tone))),
    h("div", { class: "fl-msg-body" }, m.content)))));
R.Board = (n, c) => h("div", { class: "fl-board" }, arr(n.props.columns).map((col, ci) => h("div", { class: "fl-board-col" },
  h("div", { class: "fl-board-head" }, h("span", null, col.title), h("span", { class: "fl-count" }, String(arr(col.cards).length))),
  arr(col.cards).map((card, ri) => h("div", { class: "fl-board-card", onclick: () => c.emit(n, "select", { value: { column: ci, card: ri } }) }, h("div", { class: "fl-board-title" }, card.title), card.detail && h("div", { class: "fl-board-detail" }, card.detail),
    h("div", { class: "fl-board-foot" }, arr(card.tags).map((t) => h("span", { class: "fl-tag fl-tone-neutral" }, t)), card.assignee && R.Avatar({ props: { name: card.assignee, size: "sm" } })))))));

// --- input ------------------------------------------------------------------
R.Button = (n, c) => {
  const p = n.props, variant = p.variant || "secondary";
  const inner = [p.loading ? h("span", { class: "fl-spinner" }) : p.icon ? icon(p.icon, 16) : variant === "ai" ? icon("sparkles", 16) : null, p.label && h("span", null, p.label), p.kbd && h("kbd", { class: "fl-kbd" }, p.kbd)];
  const cls = cx("fl-btn", `is-${variant}`, `size-${p.size || "md"}`, p.block && "is-block", p.loading && "is-loading", !p.label && "is-icon");
  if (p.href && !p.disabled) return h("a", { class: cls, href: /^(https?:|\/|#|mailto:)/i.test(p.href) ? p.href : "#", onclick: (e) => { if (!/^https?:/i.test(p.href)) { e.preventDefault(); c.navigate(p.href); } } }, inner);
  return h("button", { class: cls, type: "button", disabled: !!p.disabled || !!p.loading, "aria-label": p.label ? null : p.icon || "Action", onclick: (e) => c.press(n, e) }, inner);
};
function field(n, c, slots, control, opts = {}) {
  const p = n.props, id = "f-" + n.id;
  if (slots) slots.used = true;
  return h("div", { class: cx("fl-field", p.error && "is-error", p.disabled && "is-disabled", opts.cls) },
    p.label && h("label", { class: "fl-label", for: id }, p.label, p.required && h("span", { class: "fl-req", "aria-hidden": "true" }, " *")),
    h("div", { class: "fl-control-row" }, control(id), slots && slots.inline.length ? h("div", { class: "fl-field-actions" }, slots.inline) : null),
    slots ? slots.below : null,
    p.error ? h("div", { class: "fl-error", role: "alert" }, icon("alert", 13), p.error) : p.help ? h("div", { class: "fl-help" }, p.help) : null);
}
R.Input = (n, c, slots) => field(n, c, slots, (id) => {
  const p = n.props, ghost = slots && slots.ghost;
  return h("div", { class: cx("fl-input-wrap", p.icon && "has-icon", p.prefix && "has-prefix") }, p.icon && icon(p.icon, 16, "fl-input-icon"), p.prefix && h("span", { class: "fl-affix" }, p.prefix),
    h("div", { class: "fl-input-box" }, ghost ? h("div", { class: "fl-ghost", "aria-hidden": "true" }, h("span", { class: "fl-ghost-typed" }, ghost.typed), h("span", { class: "fl-ghost-rest" }, ghost.rest)) : null,
      h("input", Object.assign({ class: "fl-input", id, name: p.name, type: p.kind || "text", value: p.value === undefined ? undefined : str(p.value), placeholder: p.placeholder, required: !!p.required,
        disabled: !!p.disabled, autocomplete: "off", "aria-invalid": p.error ? "true" : null }, c.fieldEvents(n)))),
    p.suffix && h("span", { class: "fl-affix" }, p.suffix));
});
R.TextArea = (n, c, slots) => field(n, c, slots, (id) => {
  const p = n.props, ghost = slots && slots.ghost;
  return h("div", { class: "fl-input-box is-area" }, ghost ? h("div", { class: "fl-ghost is-area", "aria-hidden": "true" }, h("span", { class: "fl-ghost-typed" }, ghost.typed), h("span", { class: "fl-ghost-rest" }, ghost.rest)) : null,
    h("textarea", Object.assign({ class: "fl-input fl-textarea", id, name: p.name, rows: Number(p.rows) || 4, value: p.value === undefined ? undefined : str(p.value), placeholder: p.placeholder, "aria-invalid": p.error ? "true" : null }, c.fieldEvents(n))));
});
const optList = (options) => arr(options).map((o) => (o && typeof o === "object" ? { label: str(o.label ?? o.value), value: str(o.value ?? o.label), detail: o.detail } : { label: str(o), value: str(o) }));
R.Select = (n, c, slots) => field(n, c, slots, (id) => {
  const p = n.props, order = c.state(n.id, {}).order, opts = optList(p.options);
  const sorted = order ? [...opts].sort((a, b) => (order.indexOf(a.value) + 1 || 99) - (order.indexOf(b.value) + 1 || 99)) : opts;
  return h("div", { class: "fl-select-wrap" }, h("select", Object.assign({ class: "fl-input fl-select", id, name: p.name, value: p.value === undefined ? (p.placeholder ? "" : undefined) : str(p.value) }, c.fieldEvents(n)),
    p.placeholder && h("option", { value: "", disabled: true, selected: p.value === undefined || p.value === null }, p.placeholder), sorted.map((o) => h("option", { value: o.value, selected: str(p.value) === o.value }, o.label))), icon("chevron-down", 15, "fl-select-caret"));
});
const check = (kind) => (n, c, slots) => {
  const p = n.props, st = c.state(n.id, { on: !!p.checked, seed: !!p.checked });
  if (st.seed !== !!p.checked) { st.on = st.seed = !!p.checked; }
  if (slots) slots.used = true;
  return h("div", { class: "fl-field" }, h("label", { class: `fl-${kind}` },
    h("input", { type: "checkbox", name: p.name, checked: st.on, role: kind === "toggle" ? "switch" : null, onchange: (e) => { c.set(n.id, { on: e.target.checked }); c.setValue(n, e.target.checked); c.emit(n, "change", { value: e.target.checked }); } }),
    h("span", { class: `fl-${kind}-ui` }, kind === "checkbox" ? icon("check", 12) : null), h("span", { class: "fl-check-text" }, h("span", null, p.label), p.help && h("span", { class: "fl-help" }, p.help))),
    slots ? [slots.inline.length ? h("div", { class: "fl-field-actions" }, slots.inline) : null, slots.below] : null);
};
R.Checkbox = check("checkbox");
R.Toggle = check("toggle");
const choice = (cls) => (n, c, slots) => {
  const p = n.props, st = c.state(n.id, { value: p.value, seed: p.value });
  if (st.seed !== p.value) st.value = st.seed = p.value;
  const pick = (v) => { c.set(n.id, { value: v }); c.setValue(n, v); c.emit(n, "change", { value: v }); };
  return field(n, c, slots, () => h("div", { class: cx(cls, `is-${p.layout || "vertical"}`), role: "radiogroup", "aria-label": p.label || p.name },
    h("input", { type: "hidden", name: p.name, value: str(st.value) }),
    optList(p.options).map((o) => h("button", { class: cx("fl-choice", str(st.value) === o.value && "is-active"), type: "button", role: "radio", "aria-checked": String(str(st.value) === o.value), onclick: () => pick(o.value) },
      cls === "fl-radio" ? h("span", { class: "fl-radio-dot" }) : null, h("span", { class: "fl-choice-text" }, h("span", null, o.label), o.detail && h("span", { class: "fl-help" }, o.detail))))));
};
R.RadioGroup = choice("fl-radio");
R.Segmented = choice("fl-segmented");
R.Slider = (n, c, slots) => field(n, c, slots, (id) => {
  const p = n.props, st = c.state(n.id, { value: p.value ?? p.min ?? 0 });
  return h("div", { class: "fl-slider" }, h("input", { type: "range", id, name: p.name, min: p.min ?? 0, max: p.max ?? 100, step: p.step ?? 1, value: st.value,
    oninput: (e) => { c.set(n.id, { value: Number(e.target.value) }); c.setValue(n, Number(e.target.value)); }, onchange: (e) => c.emit(n, "change", { value: Number(e.target.value) }) }),
  h("output", { class: "fl-slider-value" }, st.value + (p.unit ? " " + p.unit : "")));
});
R.TagInput = (n, c, slots) => field(n, c, slots, (id) => {
  const p = n.props, st = c.state(n.id, { tags: arr(p.value).map(str) });
  const commit = (tags) => { c.set(n.id, { tags }); c.setValue(n, tags); c.emit(n, "change", { value: tags }); };
  return h("div", { class: "fl-taginput" }, h("input", { type: "hidden", name: p.name, value: JSON.stringify(st.tags) }),
    st.tags.map((t) => h("span", { class: "fl-tag fl-tone-brand" }, t, h("button", { class: "fl-tag-x", type: "button", "aria-label": `Remove ${t}`, onclick: () => commit(st.tags.filter((x) => x !== t)) }, icon("x", 11)))),
    h("input", { class: "fl-taginput-entry", id, placeholder: p.placeholder || "Add…", onkeydown: (e) => {
      const v = e.target.value.trim();
      if ((e.key === "Enter" || e.key === ",") && v) { e.preventDefault(); if (!st.tags.includes(v)) commit([...st.tags, v]); e.target.value = ""; }
      else if (e.key === "Backspace" && !e.target.value && st.tags.length) commit(st.tags.slice(0, -1));
    } }),
    arr(p.suggestions).filter((s) => !st.tags.includes(s)).slice(0, 4).map((s) => h("button", { class: "fl-chip is-ghost", type: "button", onclick: () => commit([...st.tags, s]) }, icon("plus", 11), s)));
});
R.Rating = (n, c, slots) => field(n, c, slots, () => {
  const p = n.props, st = c.state(n.id, { value: Number(p.value) || 0 }), max = Math.max(1, Math.min(10, Number(p.max) || 5));
  return h("div", { class: "fl-rating", role: "radiogroup", "aria-label": p.label || "Rating" }, h("input", { type: "hidden", name: p.name, value: st.value }),
    Array.from({ length: max }, (_, i) => h("button", { class: cx("fl-star", i < st.value && "is-on"), type: "button", role: "radio", "aria-checked": String(i + 1 === st.value), "aria-label": `${i + 1} of ${max}`,
      onclick: () => { c.set(n.id, { value: i + 1 }); c.setValue(n, i + 1); c.emit(n, "change", { value: i + 1 }); } }, icon("star", 20))));
});
R.FileDrop = (n, c, slots) => {
  const p = n.props, st = c.state(n.id, { name: "", over: false });
  if (slots) slots.used = true;
  const take = (file) => { if (!file) return; c.set(n.id, { name: file.name, over: false }); c.file && c.file(n, file); };
  return h("div", { class: "fl-field" }, h("label", { class: cx("fl-filedrop", st.over && "is-over"), ondragover: (e) => { e.preventDefault(); if (!st.over) c.set(n.id, { over: true }); },
    ondragleave: () => c.set(n.id, { over: false }), ondrop: (e) => { e.preventDefault(); take(e.dataTransfer.files[0]); } },
    h("input", { type: "file", name: p.name, accept: p.accept, class: "fl-visually-hidden", onchange: (e) => take(e.target.files[0]) }), icon("upload", 22),
    h("span", { class: "fl-filedrop-label" }, st.name || p.label || "Drop a file or browse"), p.hint && h("span", { class: "fl-help" }, p.hint)), slots ? slots.below : null);
};
R.Form = (n, c) => h("form", { class: "fl-form", "data-fl-form": n.props.name || n.id, novalidate: true, onsubmit: (e) => { e.preventDefault(); c.emit(n, "submit", {}); } }, kids(n, c));
R.Search = (n, c, slots) => {
  const p = n.props;
  if (slots) slots.used = true;
  return h("div", { class: "fl-search-wrap" }, h("div", { class: "fl-search" }, icon("search", 16, "fl-input-icon"),
    h("input", Object.assign({ class: "fl-input", type: "search", name: p.name, value: p.value === undefined ? undefined : str(p.value), placeholder: p.placeholder || "Search", "aria-label": p.placeholder || "Search" }, c.fieldEvents(n, "search"))),
    slots && slots.inline.length ? slots.inline : null, p.kbd && h("kbd", { class: "fl-kbd" }, p.kbd)), slots ? slots.below : null);
};
R.Mic = (n, c) => {
  const st = c.state(n.id, { rec: false });
  return h("button", { class: cx("fl-btn is-secondary fl-mic", st.rec && "is-recording"), type: "button", "aria-pressed": String(st.rec), onclick: () => c.dictate && c.dictate(n) },
    icon("mic", 16), h("span", null, st.rec ? "Listening…" : n.props.label || "Dictate"));
};

// --- data -------------------------------------------------------------------
R.Table = (n, c, slots) => {
  const p = n.props, st = c.state(n.id, { sort: null, dir: "asc", page: 0, rows: null, note: "" });
  let rows = arr(st.rows || p.rows);
  const cols = arr(p.columns).length ? arr(p.columns) : Object.keys(rows[0] || {}).map((k) => ({ key: k, label: k }));
  if (st.sort) {
    const k = st.sort, sign = st.dir === "asc" ? 1 : -1;
    rows = [...rows].sort((a, b) => { const x = a[k], y = b[k]; return (typeof x === "number" && typeof y === "number" ? x - y : str(x).localeCompare(str(y), undefined, { numeric: true })) * sign; });
  }
  const size = Number(p.pageSize) || 0, pages = size ? Math.max(1, Math.ceil(rows.length / size)) : 1, page = Math.min(st.page, pages - 1);
  const shown = size ? rows.slice(page * size, page * size + size) : rows;
  const cell = (row, col) => {
    const v = row[col.key];
    if (col.format === "badge" || (col.format === undefined && typeof v === "string" && toneOf(v) !== "neutral")) return badge(v === true ? "Yes" : v === false ? "No" : v, toneOf(v));
    return fmt(v, col.format, c.locale);
  };
  if (slots) slots.used = true;
  return h("div", { class: "fl-table-wrap" }, slots && (slots.inline.length || slots.top) ? h("div", { class: "fl-table-tools" }, slots.top, slots.inline) : null,
    st.note ? h("div", { class: "fl-table-note" }, icon("sparkles", 13), st.note, h("button", { class: "fl-linkbtn", type: "button", onclick: () => c.set(n.id, { rows: null, note: "" }) }, "Clear")) : null,
    h("div", { class: "fl-table-scroll" }, h("table", { class: cx("fl-table", p.dense && "is-dense", p.striped && "is-striped") }, p.caption && h("caption", null, p.caption),
      h("thead", null, h("tr", null, cols.map((col) => h("th", { scope: "col", class: `align-${col.align || "start"}`, style: { width: col.width ? col.width + "px" : null }, "aria-sort": st.sort === col.key ? (st.dir === "asc" ? "ascending" : "descending") : null },
        p.sortable === false ? col.label : h("button", { class: "fl-th", type: "button", onclick: () => { const dir = st.sort === col.key && st.dir === "asc" ? "desc" : "asc"; c.set(n.id, { sort: col.key, dir }); c.emit(n, "sort", { value: { key: col.key, dir } }); } },
          col.label, st.sort === col.key ? icon(st.dir === "asc" ? "chevron-down" : "chevron-down", 12, st.dir === "asc" ? "fl-sort is-asc" : "fl-sort") : null))))),
      h("tbody", null, !shown.length && slots && slots.below.length ? null : shown.length ? shown.map((row, i) => h("tr", { class: n.on && n.on.rowClick ? "is-action" : null, onclick: n.on && n.on.rowClick ? () => c.emit(n, "rowClick", { value: row }) : null },
        cols.map((col) => h("td", { class: `align-${col.align || "start"}` }, cell(row, col))))) : h("tr", null, h("td", { class: "fl-table-empty", colspan: cols.length }, p.empty || "No rows"))))),
    size && pages > 1 ? h("div", { class: "fl-pager" }, h("span", null, `${page * size + 1}–${Math.min(rows.length, page * size + size)} of ${rows.length}`),
      h("button", { class: "fl-iconbtn", type: "button", disabled: page === 0, "aria-label": "Previous page", onclick: () => c.set(n.id, { page: page - 1 }) }, icon("arrow-left", 14)),
      h("button", { class: "fl-iconbtn", type: "button", disabled: page >= pages - 1, "aria-label": "Next page", onclick: () => c.set(n.id, { page: page + 1 }) }, icon("arrow-right", 14))) : null,
    slots ? slots.below : null);
};
function ticks(lo, hi, count = 4) {
  if (hi === lo) hi = lo + 1;
  const raw = (hi - lo) / count, mag = Math.pow(10, Math.floor(Math.log10(raw))), norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag, start = Math.floor(lo / step) * step, out = [];
  for (let v = start; v <= hi + step * 0.5; v += step) out.push(Number(v.toFixed(10)));
  return out;
}
R.Chart = (n, c, slots) => {
  const p = n.props, data = arr(p.data), kind = p.kind || "bar", ys = (Array.isArray(p.y) ? p.y : [p.y]).filter(Boolean);
  const box = c.state(n.id, { w: 640 }), W = Math.max(280, Math.round(box.w)), H = Math.max(120, Number(p.height) || 260), m = { l: 46, r: 14, t: 14, b: 30 }, iw = W - m.l - m.r, ih = H - m.t - m.b;
  const measure = (el) => { const w = el.clientWidth; if (w && Math.abs(w - box.w) > 6) c.set(n.id, { w }); };
  const f = (v) => fmt(v, p.format || "compact", c.locale), label = (r, i) => str(r[p.x] ?? i);
  if (slots) slots.used = true;
  const frame = (svgKids, legend) => h("figure", { class: "fl-chart", hook: { mount: measure, update: measure } }, p.title && h("figcaption", { class: "fl-chart-title" }, p.title),
    h("svg", { class: "fl-chart-svg", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": p.title || `${kind} chart` }, svgKids), legend, slots ? [slots.inline.length ? h("div", { class: "fl-ai-actions is-static" }, slots.inline) : null, slots.below] : null);
  if (!data.length || !ys.length) return frame([h("text", { x: W / 2, y: H / 2, class: "fl-chart-empty", "text-anchor": "middle" }, "No data")]);
  if (kind === "donut" || kind === "pie") {
    const vals = data.map((r) => Math.max(0, Number(r[ys[0]]) || 0)), total = vals.reduce((a, b) => a + b, 0) || 1, r1 = Math.min(H / 2 - 12, 110, W / 4), cxp = r1 + 20, cyp = H / 2, r0 = kind === "pie" ? 0 : r1 * 0.62;
    let a0 = -Math.PI / 2;
    const arcs = vals.map((v, i) => {
      const a1 = a0 + (v / total) * Math.PI * 2 - 0.012, big = a1 - a0 > Math.PI ? 1 : 0, pt = (a, r) => `${(cxp + Math.cos(a) * r).toFixed(1)} ${(cyp + Math.sin(a) * r).toFixed(1)}`;
      const d = `M${pt(a0, r1)} A${r1} ${r1} 0 ${big} 1 ${pt(a1, r1)} L${pt(a1, r0)} A${r0} ${r0} 0 ${big} 0 ${pt(a0, r0)} Z`;
      a0 = a1 + 0.012;
      return h("path", { d, class: `fl-series s${i % 6}` }, h("title", null, `${label(data[i], i)}: ${f(v)}`));
    });
    return frame([arcs, kind === "donut" ? [h("text", { x: cxp, y: cyp - 2, class: "fl-chart-total", "text-anchor": "middle" }, f(total)), h("text", { x: cxp, y: cyp + 16, class: "fl-chart-tick", "text-anchor": "middle" }, "total")] : null,
      data.slice(0, 8).map((r, i) => [h("rect", { x: cxp + r1 + 36, y: 30 + i * 24, width: 10, height: 10, rx: 3, class: `fl-series s${i % 6}` }), h("text", { x: cxp + r1 + 54, y: 39 + i * 24, class: "fl-chart-legend" }, `${label(r, i)} — ${Math.round(vals[i] / total * 100)}%`)])]);
  }
  const fc = arr(p.forecast), all = data.flatMap((r) => ys.map((k) => Number(r[k]) || 0)).concat(fc.flatMap((q) => [q.high ?? q.value, q.low ?? q.value]).map(Number).filter(isFinite));
  const stacked = !!p.stacked && kind === "bar" && ys.length > 1, tops = stacked ? data.map((r) => ys.reduce((s, k) => s + (Number(r[k]) || 0), 0)) : all;
  const tk = ticks(p.baseline === "auto" && kind !== "bar" ? Math.min(...all) : Math.min(0, ...all), Math.max(...tops, 0)), lo = tk[0], hi = tk[tk.length - 1], Y = (v) => m.t + ih - ((v - lo) / (hi - lo || 1)) * ih;
  const total = data.length + fc.length, band = iw / Math.max(1, kind === "bar" ? data.length : Math.max(1, total - 1));
  const X = (i) => (kind === "bar" ? m.l + band * i + band / 2 : m.l + (total === 1 ? iw / 2 : band * i));
  const g = [tk.map((t) => [h("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t), class: cx("fl-grid-line", t === 0 && "is-zero") }), h("text", { x: m.l - 8, y: Y(t) + 4, class: "fl-chart-tick", "text-anchor": "end" }, f(t))])];
  const every = Math.ceil(data.length / 9);
  data.forEach((r, i) => { if (i % every === 0) g.push(h("text", { x: X(i), y: H - 9, class: "fl-chart-tick", "text-anchor": "middle" }, label(r, i).slice(0, 12))); });
  if (kind === "scatter") {
    const xs = data.map((r) => Number(r[p.x]) || 0), xt = ticks(Math.min(...xs), Math.max(...xs)), X2 = (v) => m.l + ((v - xt[0]) / (xt[xt.length - 1] - xt[0] || 1)) * iw;
    return frame([tk.map((t) => [h("line", { x1: m.l, x2: W - m.r, y1: Y(t), y2: Y(t), class: "fl-grid-line" }), h("text", { x: m.l - 8, y: Y(t) + 4, class: "fl-chart-tick", "text-anchor": "end" }, f(t))]),
      xt.map((t) => h("text", { x: X2(t), y: H - 9, class: "fl-chart-tick", "text-anchor": "middle" }, f(t))),
      data.map((r) => h("circle", { cx: X2(Number(r[p.x]) || 0).toFixed(1), cy: Y(Number(r[ys[0]]) || 0).toFixed(1), r: 4.5, class: "fl-series s0 is-point" }, h("title", null, `${f(r[p.x])}, ${f(r[ys[0]])}`)))]);
  }
  if (kind === "bar") {
    const bw = Math.min(46, (band * 0.72) / (stacked ? 1 : ys.length));
    data.forEach((r, i) => { let base = 0; ys.forEach((k, s) => {
      const v = Number(r[k]) || 0, y0 = stacked ? Y(base) : Y(0), y1 = stacked ? Y(base + v) : Y(v), x = stacked ? X(i) - bw / 2 : X(i) - (bw * ys.length) / 2 + s * bw;
      base += v;
      g.push(h("rect", { x: x.toFixed(1), y: Math.min(y0, y1).toFixed(1), width: Math.max(1, bw - (stacked ? 0 : 3)).toFixed(1), height: Math.max(1, Math.abs(y0 - y1)).toFixed(1), rx: stacked ? 2 : Math.min(6, bw / 3).toFixed(1), class: `fl-series s${s % 6}`,
        onclick: () => c.emit(n, "pointClick", { value: r }) }, h("title", null, `${label(r, i)} · ${k}: ${f(v)}`)));
    }); });
  } else {
    ys.forEach((k, s) => {
      const pts = data.map((r, i) => [X(i), Y(Number(r[k]) || 0)]), gid = "fl-cg-" + String(n.id).replace(/[^\w-]/g, "_") + "-" + s;
      let d = "M" + pts[0][0].toFixed(1) + " " + pts[0][1].toFixed(1);
      for (let i = 0; i < pts.length - 1; i++) { const a = pts[i], b = pts[i + 1], mx = (a[0] + b[0]) / 2; d += p.smooth === false ? ` L${b[0].toFixed(1)} ${b[1].toFixed(1)}` : ` C${mx.toFixed(1)} ${a[1].toFixed(1)} ${mx.toFixed(1)} ${b[1].toFixed(1)} ${b[0].toFixed(1)} ${b[1].toFixed(1)}`; }
      if (kind === "area") g.push(h("defs", null, h("linearGradient", { id: gid, x1: 0, y1: 0, x2: 0, y2: 1 }, h("stop", { offset: 0, class: `fl-area-stop-a s${s % 6}` }), h("stop", { offset: 1, class: `fl-area-stop-b s${s % 6}` }))),
        h("path", { d: `${d} L${pts[pts.length - 1][0].toFixed(1)} ${Y(lo)} L${pts[0][0].toFixed(1)} ${Y(lo)} Z`, class: `fl-area s${s % 6}`, style: `fill:url(#${gid})` }));
      g.push(h("path", { d, class: `fl-line s${s % 6}` }));
      pts.forEach((q, i) => g.push(h("circle", { cx: q[0].toFixed(1), cy: q[1].toFixed(1), r: p.points === true || (p.points !== false && kind === "line" && data.length <= 12) ? 3.2 : 0, class: `fl-series s${s % 6} is-point` }, h("title", null, `${label(data[i], i)} · ${k}: ${f(data[i][k])}`))));
      if (s === 0 && fc.length) {
        const start = pts[pts.length - 1], fp = fc.map((q, i) => [X(data.length + i), Y(Number(q.value)), Y(Number(q.high ?? q.value)), Y(Number(q.low ?? q.value))]);
        g.push(h("path", { d: `M${start[0]} ${start[1]} ` + fp.map((q) => `L${q[0].toFixed(1)} ${q[2].toFixed(1)}`).join(" ") + " " + [...fp].reverse().map((q) => `L${q[0].toFixed(1)} ${q[3].toFixed(1)}`).join(" ") + " Z", class: "fl-forecast-band" }));
        g.push(h("path", { d: `M${start[0]} ${start[1]} ` + fp.map((q) => `L${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(" "), class: "fl-forecast-line" }));
      }
    });
  }
  arr(p.annotations).forEach((a) => {
    const i = data.findIndex((r) => str(r[p.x]) === str(a.x));
    if (i < 0) return;
    const tw = Math.max(40, str(a.label).length * 6.4 + 16), tx = Math.max(m.l, Math.min(W - m.r - tw, X(i) - tw / 2));
    g.push(h("line", { x1: X(i), x2: X(i), y1: m.t + 18, y2: m.t + ih, class: `fl-annot-line tone-${a.tone || "ai"}` }), h("rect", { x: tx, y: m.t - 4, width: tw, height: 20, rx: 10, class: `fl-annot-pill tone-${a.tone || "ai"}` }),
      h("text", { x: tx + tw / 2, y: m.t + 10, class: "fl-annot-text", "text-anchor": "middle" }, str(a.label)));
  });
  const legend = ys.length > 1 && p.legend !== false ? h("div", { class: "fl-legend" }, ys.map((k, s) => h("span", null, h("i", { class: `fl-series-dot s${s % 6}` }), k))) : null;
  return frame(g, legend);
};
