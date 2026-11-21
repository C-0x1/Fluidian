// Fluidian runtime — portable logic.
// Behaviour written as data travels with the scene, so it is identical in every SDK language
// and on every platform:
//
//   bindings   "{{ count }} items"            any string prop may interpolate state
//   actions    on("click", "@count += 1")     an action starting with "@" runs in the runtime
//   structure  State · Show · Each            declare state, render conditionally, repeat
//
// The expression language is a small, side-effect-free subset of JavaScript syntax. It is parsed
// and interpreted here; nothing is ever passed to eval or Function.

const AST = new Map();
const TOKEN = /\s*(?:(\d+\.?\d*|\.\d+)|'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)"|([A-Za-z_$][\w$]*)|(===|!==|==|!=|<=|>=|&&|\|\||\+=|-=|\*=|->|[-+*/%<>!?:.,()[\]{}=;]))/y;

function tokenize(src) {
  const out = [];
  TOKEN.lastIndex = 0;
  let at = 0;
  while (at < src.length) {
    if (/^\s*$/.test(src.slice(at))) break;
    TOKEN.lastIndex = at;
    const m = TOKEN.exec(src);
    if (!m) throw new SyntaxError(`Unexpected character at ${at}: ${src.slice(at, at + 12)}`);
    at = TOKEN.lastIndex;
    if (m[1] !== undefined) out.push({ t: "num", v: Number(m[1]) });
    else if (m[2] !== undefined || m[3] !== undefined) out.push({ t: "str", v: (m[2] ?? m[3]).replace(/\\(.)/g, "$1") });
    else if (m[4] !== undefined) out.push({ t: "id", v: m[4] });
    else out.push({ t: "op", v: m[5] });
  }
  return out;
}

const BINARY = [["||"], ["&&"], ["==", "!=", "===", "!=="], ["<", "<=", ">", ">="], ["+", "-"], ["*", "/", "%"]];
class Parser {
  constructor(tokens) { this.k = tokens; this.i = 0; }
  peek(v) { const t = this.k[this.i]; return t && (v === undefined || (t.t === "op" && t.v === v)) ? t : null; }
  take(v) { const t = this.peek(v); if (t) this.i++; return t; }
  need(v) { if (!this.take(v)) throw new SyntaxError(`Expected "${v}"`); }
  done() { return this.i >= this.k.length; }
  expr() {
    const cond = this.binary(0);
    if (!this.take("?")) return cond;
    const yes = this.expr();
    this.need(":");
    return ["tern", cond, yes, this.expr()];
  }
  binary(level) {
    if (level >= BINARY.length) return this.unary();
    let left = this.binary(level + 1);
    for (;;) { const t = this.k[this.i]; if (!t || t.t !== "op" || !BINARY[level].includes(t.v)) return left; this.i++; left = ["bin", t.v, left, this.binary(level + 1)]; }
  }
  unary() {
    if (this.take("!")) return ["un", "!", this.unary()];
    if (this.take("-")) return ["un", "-", this.unary()];
    return this.postfix();
  }
  postfix() {
    let node = this.primary();
    for (;;) {
      if (this.take(".")) { const t = this.take(); if (!t || t.t !== "id") throw new SyntaxError("Expected a property name"); node = ["get", node, ["lit", t.v]]; }
      else if (this.take("[")) { const key = this.expr(); this.need("]"); node = ["get", node, key]; }
      else return node;
    }
  }
  primary() {
    const t = this.take();
    if (!t) throw new SyntaxError("Unexpected end of expression");
    if (t.t === "num" || t.t === "str") return ["lit", t.v];
    if (t.t === "id") {
      if (t.v === "true") return ["lit", true];
      if (t.v === "false") return ["lit", false];
      if (t.v === "null") return ["lit", null];
      if (this.take("(")) { const args = []; while (!this.peek(")")) { args.push(this.expr()); if (!this.take(",")) break; } this.need(")"); return ["call", t.v, args]; }
      return ["id", t.v];
    }
    if (t.v === "(") { const e = this.expr(); this.need(")"); return e; }
    if (t.v === "[") { const items = []; while (!this.peek("]")) { items.push(this.expr()); if (!this.take(",")) break; } this.need("]"); return ["arr", items]; }
    if (t.v === "{") {
      const pairs = [];
      while (!this.peek("}")) { const key = this.take(); if (!key || key.t === "op") throw new SyntaxError("Expected a key"); let value; if (this.take(":")) value = this.expr(); else value = ["id", String(key.v)]; pairs.push([String(key.v), value]); if (!this.take(",")) break; }
      this.need("}");
      return ["obj", pairs];
    }
    throw new SyntaxError(`Unexpected "${t.v}"`);
  }
}

const own = (obj, key) => obj !== null && obj !== undefined && (Array.isArray(obj) ? key === "length" || (Number.isInteger(Number(key)) && Number(key) >= 0 && Number(key) < obj.length) : typeof obj === "object" ? Object.prototype.hasOwnProperty.call(obj, key) : typeof obj === "string" && key === "length");
const list = (v) => (Array.isArray(v) ? v : []);
const FUNCS = {
  len: (v) => (typeof v === "string" || Array.isArray(v) ? v.length : v && typeof v === "object" ? Object.keys(v).length : 0),
  sum: (v, key) => list(v).reduce((a, x) => a + (Number(key ? x && x[key] : x) || 0), 0),
  count: (v, key, want) => list(v).filter((x) => (key === undefined ? !!x : want === undefined ? !!(x && x[key]) : x && x[key] === want)).length,
  where: (v, key, want) => list(v).filter((x) => (want === undefined ? !!(x && x[key]) : x && x[key] === want)),
  without: (v, key, want) => list(v).filter((x) => !(want === undefined ? !!(x && x[key]) : x && x[key] === want)),
  pluck: (v, key) => list(v).map((x) => (x && typeof x === "object" ? x[key] : undefined)),
  first: (v) => list(v)[0], last: (v) => list(v)[list(v).length - 1],
  round: (v, d = 0) => { const f = Math.pow(10, Number(d) || 0); return Math.round((Number(v) || 0) * f) / f; },
  floor: (v) => Math.floor(Number(v) || 0), ceil: (v) => Math.ceil(Number(v) || 0), abs: (v) => Math.abs(Number(v) || 0),
  min: (...a) => Math.min(...a.flat().map(Number)), max: (...a) => Math.max(...a.flat().map(Number)),
  upper: (v) => String(v ?? "").toUpperCase(), lower: (v) => String(v ?? "").toLowerCase(), trim: (v) => String(v ?? "").trim(),
  str: (v) => (v === null || v === undefined ? "" : String(v)), num: (v) => Number(v) || 0,
  join: (v, sep = ", ") => list(v).join(sep), includes: (v, x) => (typeof v === "string" ? v.includes(String(x)) : list(v).includes(x)),
  default: (v, d) => (v === null || v === undefined || v === "" ? d : v),
  money: (v, cur = "USD") => { try { return new Intl.NumberFormat("en-US", { style: "currency", currency: String(cur) }).format(Number(v) || 0); } catch (e) { return String(v); } },
  percent: (v, d = 0) => (Number(v) * 100 || 0).toFixed(Number(d) || 0) + "%",
  plural: (count, one, many) => (Number(count) === 1 ? one : many === undefined ? one + "s" : many),
};

function run(node, env) {
  switch (node[0]) {
    case "lit": return node[1];
    case "id": return own(env.scope, node[1]) ? env.scope[node[1]] : own(env.state, node[1]) ? env.state[node[1]] : undefined;
    case "get": { const obj = run(node[1], env), key = run(node[2], env); return own(obj, typeof key === "number" ? key : String(key)) ? obj[key] : undefined; }
    case "un": return node[1] === "!" ? !run(node[2], env) : -(Number(run(node[2], env)) || 0);
    case "tern": return run(node[1], env) ? run(node[2], env) : run(node[3], env);
    case "arr": return node[1].map((x) => run(x, env));
    case "obj": return Object.fromEntries(node[1].map(([k, v]) => [k, run(v, env)]));
    case "call": { const fn = Object.prototype.hasOwnProperty.call(FUNCS, node[1]) ? FUNCS[node[1]] : null; if (!fn) throw new ReferenceError(`Unknown function ${node[1]}()`); return fn(...node[2].map((x) => run(x, env))); }
    case "bin": {
      const op = node[1];
      if (op === "&&") { const l = run(node[2], env); return l ? run(node[3], env) : l; }
      if (op === "||") { const l = run(node[2], env); return l ? l : run(node[3], env); }
      const a = run(node[2], env), b = run(node[3], env);
      switch (op) {
        case "+": return typeof a === "string" || typeof b === "string" ? String(a ?? "") + String(b ?? "") : (Number(a) || 0) + (Number(b) || 0);
        case "-": return (Number(a) || 0) - (Number(b) || 0);
        case "*": return (Number(a) || 0) * (Number(b) || 0);
        case "/": return Number(b) ? (Number(a) || 0) / Number(b) : 0;
        case "%": return Number(b) ? (Number(a) || 0) % Number(b) : 0;
        case "==": case "===": return a === b || (a == null && b == null); // eslint-disable-line eqeqeq
        case "!=": case "!==": return !(a === b || (a == null && b == null)); // eslint-disable-line eqeqeq
        case "<": return a < b; case "<=": return a <= b; case ">": return a > b; case ">=": return a >= b;
      }
    }
  }
  return undefined;
}

function compile(src) {
  let ast = AST.get(src);
  if (ast === undefined) {
    try { const p = new Parser(tokenize(src)); ast = p.expr(); if (!p.done()) throw new SyntaxError("Unexpected input after the expression"); } catch (err) { ast = { error: err.message }; }
    if (AST.size > 4000) AST.clear();
    AST.set(src, ast);
  }
  return ast;
}

/** Evaluate an expression against `{ state, scope }`. Syntax and runtime errors yield `undefined`. */
export function evaluate(src, env) {
  const ast = compile(String(src));
  if (!Array.isArray(ast)) return undefined;
  try { return run(ast, env); } catch (err) { return undefined; }
}
/** The syntax error for an expression, or `null` when it parses. */
export function check(src) { const ast = compile(String(src)); return Array.isArray(ast) ? null : ast.error; }

// `\{{` is an escape: it yields a literal `{{` and is never evaluated.
const WHOLE = /^\s*\{\{([^{}]+)\}\}\s*$/, PART = /(\\)?\{\{([^{}]*)\}\}/g;
const FLAG = new WeakMap();
function bound(value, depth) {
  if (typeof value === "string") return value.includes("{{");
  if (!value || typeof value !== "object" || depth > 5) return false;
  if (FLAG.has(value)) return FLAG.get(value);
  const hit = Array.isArray(value) ? value.some((v) => bound(v, depth + 1)) : Object.keys(value).some((k) => bound(value[k], depth + 1));
  FLAG.set(value, hit);
  return hit;
}
/** Resolve `{{ }}` bindings in a prop value. A value that is one whole binding keeps its type. */
export function resolve(value, env, depth = 0) {
  if (typeof value === "string") {
    if (!value.includes("{{")) return value;
    const whole = WHOLE.exec(value);
    if (whole) return evaluate(whole[1], env);
    return value.replace(PART, (all, escaped, src) => { if (escaped) return all.slice(1); const v = evaluate(src, env); return v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v) : String(v); });
  }
  if (!value || typeof value !== "object" || depth > 5 || !bound(value, depth)) return value;
  if (Array.isArray(value)) return value.map((v) => resolve(v, env, depth + 1));
  const out = {};
  for (const k in value) out[k] = resolve(value[k], env, depth + 1);
  return out;
}
export const hasBindings = (props) => bound(props, 0);
export const isLocal = (binding) => !!binding && typeof binding.action === "string" && binding.action.charCodeAt(0) === 64;

// --- actions -----------------------------------------------------------------
const VERBS = new Set(["set", "toggle", "push", "remove", "clear", "go", "toast", "emit", "ask"]);
function parseActions(src) {
  const p = new Parser(tokenize(src)), out = [];
  while (!p.done()) {
    if (p.take(";")) continue;
    const head = p.k[p.i], next = p.k[p.i + 1];
    const verb = head.t === "id" && VERBS.has(head.v) && next && !(next.t === "op" && ["=", "+=", "-=", "*=", ".", "["].includes(next.v)) ? head.v : "";
    if (verb) p.i++;
    if (verb === "go") out.push({ op: "go", expr: p.expr() });
    else if (verb === "toast") { const expr = p.expr(), tone = p.k[p.i] && p.k[p.i].t === "id" ? p.take().v : "info"; out.push({ op: "toast", expr, tone }); }
    else if (verb === "emit") { const name = p.take(); if (!name || name.t === "op") throw new SyntaxError("emit needs an action name"); out.push({ op: "emit", name: String(name.v), expr: p.done() || p.peek(";") ? null : p.expr() }); }
    else if (verb === "ask") { let name = ""; while (p.k[p.i] && (p.k[p.i].t === "id" || (p.k[p.i].t === "op" && p.k[p.i].v === "."))) name += p.take().v; const expr = p.peek("->") ? ["obj", []] : p.expr(); p.need("->"); out.push({ op: "ask", name, expr, target: p.postfix() }); }
    else if (verb === "toggle" || verb === "clear") out.push({ op: verb, target: p.postfix() });
    else if (verb === "push" || verb === "remove") { const target = p.postfix(); out.push({ op: verb, target, expr: p.expr() }); }
    else { const target = p.postfix(), op = p.take(); if (!op || !["=", "+=", "-=", "*="].includes(op.v)) throw new SyntaxError("Expected an assignment"); out.push({ op: op.v, target, expr: p.expr() }); }
    if (!p.done() && !p.take(";")) throw new SyntaxError("Expected \";\" between actions");
  }
  return out;
}
const ACTIONS = new Map();
function compileActions(src) {
  let prog = ACTIONS.get(src);
  if (prog === undefined) { try { prog = parseActions(src); } catch (err) { prog = { error: err.message }; } if (ACTIONS.size > 2000) ACTIONS.clear(); ACTIONS.set(src, prog); }
  return prog;
}
function place(target, env) { // → [container, key] for an assignable expression
  if (target[0] === "id") return [own(env.scope, target[1]) && !own(env.state, target[1]) ? env.scope : env.state, target[1]];
  if (target[0] === "get") { const obj = run(target[1], env), key = run(target[2], env); if (obj && typeof obj === "object" && !["__proto__", "constructor", "prototype"].includes(String(key))) return [obj, key]; }
  return null;
}
/** The syntax error for an action string (without the leading "@"), or `null` when it parses. */
export function checkActions(src) { const prog = compileActions(String(src)); return Array.isArray(prog) ? null : prog.error; }

/**
 * Run an action string. `env` is `{ state, scope }`; `api` supplies the side effects
 * (`navigate`, `toast`, `emit`, `ask`, `changed`). Returns false when the string does not parse.
 */
export function runActions(src, env, api = {}) {
  const prog = compileActions(String(src).replace(/^@/, ""));
  if (!Array.isArray(prog)) { if (api.error) api.error(prog.error); return false; }
  for (const step of prog) {
    try {
      if (step.op === "go") { api.navigate && api.navigate(String(run(step.expr, env))); continue; }
      if (step.op === "toast") { api.toast && api.toast(String(run(step.expr, env)), step.tone); continue; }
      if (step.op === "emit") { api.emit && api.emit(step.name, step.expr ? run(step.expr, env) : null); continue; }
      const slot = place(step.target, env);
      if (!slot) continue;
      const [box, key] = slot, cur = box[key];
      if (step.op === "ask") { const input = run(step.expr, env); if (api.ask) Promise.resolve(api.ask(step.name, input)).then((data) => { box[key] = data; api.changed && api.changed(); }); continue; }
      if (step.op === "toggle") box[key] = !cur;
      else if (step.op === "clear") box[key] = Array.isArray(cur) ? [] : typeof cur === "number" ? 0 : typeof cur === "boolean" ? false : "";
      else if (step.op === "push") box[key] = list(cur).concat([run(step.expr, env)]);
      else if (step.op === "remove") { const which = run(step.expr, env); box[key] = list(cur).filter((x, i) => (typeof which === "number" ? i !== which : x !== which)); }
      else { const v = run(step.expr, env); box[key] = step.op === "=" ? v : step.op === "+=" ? (typeof cur === "string" ? cur + String(v ?? "") : (Number(cur) || 0) + (Number(v) || 0)) : step.op === "-=" ? (Number(cur) || 0) - (Number(v) || 0) : (Number(cur) || 0) * (Number(v) || 0); }
    } catch (err) { if (api.error) api.error(err.message); }
  }
  api.changed && api.changed();
  return true;
}

/**
 * Development aid: every binding, `when`, `items`, `bind` and "@" action in a scene that does not parse,
 * as messages in the same form as the engine's scene repairs. Code samples and escaped braces are skipped.
 */
export function lint(root) {
  const found = [];
  const scan = (value, where, depth) => {
    if (typeof value === "string") { for (const m of value.matchAll(/(\\)?\{\{([^{}]*)\}\}/g)) { const err = m[1] ? null : check(m[2]); if (err) found.push(`${where}: binding "{{${m[2]}}}" does not parse (${err})`); } }
    else if (value && typeof value === "object" && depth < 5) for (const k in value) scan(value[k], where, depth + 1);
  };
  const walk = (node) => {
    if (!node || typeof node !== "object") return;
    const props = node.props || {};
    if (node.type !== "Code" && node.type !== "Terminal") scan(props, node.id, 0);
    const sources = [["when", node.type === "Show" ? props.when : null], ["items", node.type === "Each" ? props.items : null], ["bind", props.bind]];
    for (const [key, src] of sources) { const err = typeof src === "string" && src ? check(src) : null; if (err) found.push(`${node.id}: ${key} "${src}" does not parse (${err})`); }
    for (const event in node.on || {}) { const b = node.on[event]; if (isLocal(b)) { const err = checkActions(b.action.slice(1)); if (err) found.push(`${node.id}: action "${b.action}" does not parse (${err})`); } }
    (node.children || []).forEach(walk);
  };
  walk(root);
  return found.slice(0, 20);
}

/** Client-side state for one page: plain data, seeded by State nodes. */
export function createStore() {
  const state = {}, seeded = new Set();
  return { state, declare(values) { if (values && typeof values === "object" && !Array.isArray(values)) for (const k in values) if (!seeded.has(k)) { seeded.add(k); state[k] = JSON.parse(JSON.stringify(values[k] ?? null)); } } };
}
