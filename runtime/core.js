// Fluidian runtime — virtual DOM core.
// A small keyed virtual DOM with two back ends: `patch` for the browser and
// `renderToString` for server-side rendering, static export and tests.

const SVG_NS = "http://www.w3.org/2000/svg";
const SVG_TAGS = new Set(["svg", "path", "circle", "rect", "line", "polyline", "polygon", "g", "text", "defs", "linearGradient",
  "stop", "ellipse", "tspan", "clipPath", "title"]);
const VOID = new Set(["input", "br", "hr", "img", "meta", "link"]);
const BOOL = new Set(["disabled", "checked", "selected", "required", "readonly", "hidden", "open", "multiple", "autofocus"]);

/** Create a virtual node. `attrs.key` identifies it among siblings; `attrs.hook` receives lifecycle calls. */
export function h(tag, attrs, ...children) {
  const flat = [];
  const push = (c) => {
    if (c === null || c === undefined || c === false || c === true) return;
    if (Array.isArray(c)) c.forEach(push);
    else if (typeof c !== "object") flat.push(String(c));
    else if (typeof c.tag === "string") flat.push(c); // anything else is not renderable and is dropped rather than printed
  };
  children.forEach(push);
  attrs = attrs || {};
  return { tag, attrs, children: flat, key: attrs.key };
}

export function cx(...parts) {
  const out = [];
  for (const p of parts) {
    if (!p) continue;
    if (typeof p === "string") out.push(p);
    else for (const k in p) if (p[k]) out.push(k);
  }
  return out.join(" ");
}

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function styleText(style) {
  if (typeof style === "string") return style;
  return Object.keys(style).filter((k) => style[k] !== null && style[k] !== undefined && style[k] !== "")
    .map((k) => `${k.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase())}:${style[k]}`).join(";");
}

function skip(name, value) {
  return name === "key" || name === "hook" || typeof value === "function" || value === null || value === undefined || value === false;
}

/** Serialise a virtual tree to HTML. Event handlers and hooks are omitted; all text is escaped. */
export function renderToString(vnode) {
  if (typeof vnode === "string") return escapeHtml(vnode);
  if (!vnode) return "";
  let out = "<" + vnode.tag;
  for (const name in vnode.attrs) {
    const value = vnode.attrs[name];
    if (skip(name, value)) continue;
    if (name === "style") { const s = styleText(value); if (s) out += ` style="${escapeHtml(s)}"`; continue; }
    if (name === "value" && vnode.tag === "textarea") continue;
    if (value === true) { out += " " + name; continue; }
    out += ` ${name === "className" ? "class" : name}="${escapeHtml(value)}"`;
  }
  if (VOID.has(vnode.tag)) return out + ">";
  out += ">";
  if (vnode.tag === "textarea" && vnode.attrs.value) out += escapeHtml(vnode.attrs.value);
  for (const child of vnode.children) out += renderToString(child);
  return out + `</${vnode.tag}>`;
}

function setAttr(el, name, value, old) {
  if (name === "key" || name === "hook") return;
  if (name.startsWith("on") && (typeof value === "function" || typeof old === "function")) {
    const type = name.slice(2).toLowerCase();
    el.__fl = el.__fl || {};
    if (!el.__fl[type]) {
      el.__fl[type] = { fn: null };
      el.addEventListener(type, (ev) => el.__fl[type].fn && el.__fl[type].fn(ev));
    }
    el.__fl[type].fn = typeof value === "function" ? value : null;
    return;
  }
  if (name === "style") { el.setAttribute("style", value ? styleText(value) : ""); return; }
  if (name === "value" && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT")) {
    // Only write when the scene changed the value, so typing is never clobbered.
    if (value !== old && el.value !== String(value ?? "")) el.value = value ?? "";
    return;
  }
  if (name === "checked" && el.tagName === "INPUT") { if (value !== old) el.checked = !!value; return; }
  if (value === null || value === undefined || value === false) { el.removeAttribute(name === "className" ? "class" : name); return; }
  if (BOOL.has(name)) { el.setAttribute(name, ""); return; }
  el.setAttribute(name === "className" ? "class" : name, value === true ? "" : String(value));
}

function create(vnode, svg) {
  if (typeof vnode === "string") return document.createTextNode(vnode);
  svg = svg || SVG_TAGS.has(vnode.tag) && vnode.tag !== "title" || vnode.tag === "svg";
  const el = svg ? document.createElementNS(SVG_NS, vnode.tag) : document.createElement(vnode.tag);
  for (const name in vnode.attrs) setAttr(el, name, vnode.attrs[name], undefined);
  for (const child of vnode.children) el.appendChild(create(child, svg && vnode.tag !== "foreignObject"));
  if (vnode.attrs.value !== undefined && vnode.tag === "select") el.value = vnode.attrs.value;
  el.__v = vnode;
  if (vnode.attrs.hook && vnode.attrs.hook.mount) queueMicrotask(() => vnode.attrs.hook.mount(el, vnode));
  return el;
}

function destroy(el) {
  if (el.nodeType !== 1) return;
  for (const child of Array.from(el.childNodes)) destroy(child);
  const v = el.__v;
  if (v && v.attrs.hook && v.attrs.hook.unmount) v.attrs.hook.unmount(el, v);
}

function same(a, b) {
  if (typeof a === "string" || typeof b === "string") return typeof a === typeof b;
  return a.tag === b.tag && a.key === b.key;
}

function update(el, old, next) {
  if (typeof next === "string") { if (el.nodeValue !== next) el.nodeValue = next; return el; }
  for (const name in old.attrs) if (!(name in next.attrs)) setAttr(el, name, null, old.attrs[name]);
  for (const name in next.attrs) if (old.attrs[name] !== next.attrs[name]) setAttr(el, name, next.attrs[name], old.attrs[name]);
  reconcile(el, old.children, next.children);
  el.__v = next;
  if (next.attrs.hook && next.attrs.hook.update) next.attrs.hook.update(el, next, old);
  return el;
}

function reconcile(parent, oldKids, newKids) {
  const dom = Array.from(parent.childNodes);
  const keyed = new Map();
  oldKids.forEach((k, i) => { if (typeof k !== "string" && k.key !== undefined && dom[i]) keyed.set(k.key, i); });
  const used = new Set();
  let cursor = 0;
  const result = [];
  for (const next of newKids) {
    let index = -1;
    if (typeof next !== "string" && next.key !== undefined && keyed.has(next.key)) index = keyed.get(next.key);
    else {
      while (cursor < oldKids.length && (used.has(cursor) || (typeof oldKids[cursor] !== "string" && oldKids[cursor].key !== undefined && keyed.has(oldKids[cursor].key)))) cursor++;
      if (cursor < oldKids.length && dom[cursor] && same(oldKids[cursor], next)) index = cursor;
    }
    if (index >= 0 && !used.has(index) && dom[index] && same(oldKids[index], next)) {
      used.add(index);
      result.push(update(dom[index], oldKids[index], next));
    } else {
      result.push(create(next, parent.namespaceURI === SVG_NS));
    }
  }
  dom.forEach((node, i) => { if (!used.has(i)) { destroy(node); parent.removeChild(node); } });
  let ref = parent.firstChild;
  for (const node of result) {
    if (node === ref) ref = ref.nextSibling;
    else parent.insertBefore(node, ref);
  }
}

/** Render `vnode` into `container`, reusing existing DOM where the trees match. */
export function patch(container, vnode) {
  const old = container.__root;
  if (old && same(old, vnode) && container.firstChild) update(container.firstChild, old, vnode);
  else {
    while (container.firstChild) { destroy(container.firstChild); container.removeChild(container.firstChild); }
    container.appendChild(create(vnode, false));
  }
  container.__root = vnode;
}
