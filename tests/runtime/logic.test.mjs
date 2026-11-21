// Portable logic: the expression language, bindings and actions that run in the runtime.
import test from "node:test";
import assert from "node:assert/strict";
import { evaluate, check, resolve, hasBindings, isLocal, checkActions, runActions, createStore, lint } from "../../runtime/logic.js";
import { renderScene } from "../../runtime/static.js";
import { node } from "./helpers.mjs";

const env = (state = {}, scope = {}) => ({ state, scope });

test("expressions cover arithmetic, comparison, logic and member access", () => {
  const e = env({ count: 4, user: { name: "Mira", tags: ["a", "b"] }, items: [{ price: 5, done: true }, { price: 7.5, done: false }] });
  assert.equal(evaluate("count * 2 + 1", e), 9);
  assert.equal(evaluate("(count - 1) / 2", e), 1.5);
  assert.equal(evaluate("count >= 4 && user.name == 'Mira'", e), true);
  assert.equal(evaluate("count > 10 || !count", e), false);
  assert.equal(evaluate("count > 3 ? 'many' : 'few'", e), "many");
  assert.equal(evaluate("user.tags[1]", e), "b");
  assert.equal(evaluate("items[0].price + items[1].price", e), 12.5);
  assert.equal(evaluate("'Hello, ' + user.name", e), "Hello, Mira");
  assert.deepEqual(evaluate("{name: user.name, n: count}", e), { name: "Mira", n: 4 });
  assert.deepEqual(evaluate("[1, count, 'x']", e), [1, 4, "x"]);
});

test("the function library works on lists, numbers and text", () => {
  const e = env({ items: [{ price: 5, done: true, name: "tea" }, { price: 7.5, done: false, name: "milk" }], draft: "  hi  ", n: 3.14159 });
  assert.equal(evaluate("len(items)", e), 2);
  assert.equal(evaluate("sum(items, 'price')", e), 12.5);
  assert.equal(evaluate("count(items, 'done')", e), 1);
  assert.deepEqual(evaluate("pluck(items, 'name')", e), ["tea", "milk"]);
  assert.equal(evaluate("join(pluck(items, 'name'), ' + ')", e), "tea + milk");
  assert.equal(evaluate("len(where(items, 'done'))", e), 1);
  assert.equal(evaluate("round(n, 2)", e), 3.14);
  assert.equal(evaluate("upper(trim(draft))", e), "HI");
  assert.equal(evaluate("default(missing, 'fallback')", e), "fallback");
  assert.equal(evaluate("max(2, 9, 4) - min(2, 9, 4)", e), 7);
  assert.equal(evaluate("len(items) + ' ' + plural(len(items), 'note')", e), "2 notes");
  assert.equal(evaluate("plural(1, 'note') + '/' + plural(3, 'person', 'people')", e), "note/people");
  assert.match(String(evaluate("money(1234.5)", e)), /1,234\.50/);
});

test("the interpreter cannot reach outside its data", () => {
  const e = env({ o: { a: 1 }, f: "x" });
  for (const src of ["constructor", "o.constructor", "o.__proto__", "o['__proto__']", "f.constructor('return 1')()", "globalThis", "window", "process",
    "o.toString()", "len.constructor", "this"]) {
    const value = evaluate(src, e);
    assert.ok(value === undefined || value === null, `${src} leaked ${typeof value}`);
  }
  assert.equal(evaluate("1 +", e), undefined, "a syntax error evaluates to undefined");
  assert.ok(check("1 +"), "and is reported by check()");
  assert.equal(check("count + 1"), null);
});

test("bindings resolve inside strings, keep types when whole, and can be escaped", () => {
  const e = env({ count: 3, user: { name: "Mira" }, rows: [1, 2] });
  assert.equal(resolve("{{ count }} of {{ len(rows) }}", e), "3 of 2");
  assert.equal(resolve("{{ count }}", e), 3, "a whole-value binding keeps its type");
  assert.deepEqual(resolve("{{ rows }}", e), [1, 2]);
  assert.equal(resolve("Hi {{ user.name }}{{ missing }}", e), "Hi Mira", "missing values render as nothing");
  assert.equal(resolve("Write \\{{ name }} to bind", e), "Write {{ name }} to bind");
  assert.deepEqual(resolve({ title: "{{ user.name }}", nested: [{ v: "{{ count + 1 }}" }], plain: 1 }, e), { title: "Mira", nested: [{ v: 4 }], plain: 1 });
  assert.equal(hasBindings({ a: "x", b: [{ c: "{{ y }}" }] }), true);
  assert.equal(hasBindings({ a: "x", b: [1, 2] }), false);
});

test("actions change state: set, arithmetic, toggle, push, remove and clear", () => {
  const state = { count: 1, open: false, todos: [{ text: "a" }], draft: "milk", name: "x" };
  const e = env(state);
  assert.equal(runActions("@count += 2; count *= 3", e), true);
  assert.equal(state.count, 9);
  runActions("@count -= 4; open = count == 5", e);
  assert.deepEqual([state.count, state.open], [5, true]);
  runActions("@toggle open", e);
  assert.equal(state.open, false);
  runActions("@push todos {text: draft, done: false}; draft = ''", e);
  assert.deepEqual(state.todos, [{ text: "a" }, { text: "milk", done: false }]);
  assert.equal(state.draft, "");
  runActions("@remove todos 0", e);
  assert.deepEqual(state.todos, [{ text: "milk", done: false }]);
  runActions("@todos[0].done = true; set name = upper(todos[0].text)", e);
  assert.deepEqual([state.todos[0].done, state.name], [true, "MILK"]);
  runActions("@clear todos; clear count; clear name", e);
  assert.deepEqual([state.todos, state.count, state.name], [[], 0, ""]);
});

test("actions reach the outside world only through the host API", async () => {
  const calls = [], state = { id: 7, summary: null };
  const api = { navigate: (r) => calls.push(["go", r]), toast: (t, tone) => calls.push(["toast", t, tone]), emit: (n, p) => calls.push(["emit", n, p]),
    ask: (cap, input) => { calls.push(["ask", cap, input]); return Promise.resolve({ title: "Done" }); }, changed: () => calls.push(["changed"]) };
  runActions("@go '/orders/' + id; toast 'Saved' success; emit save {id: id}; ask content.summarize {text: 'x'} -> summary", env(state), api);
  assert.deepEqual(calls.slice(0, 4), [["go", "/orders/7"], ["toast", "Saved", "success"], ["emit", "save", { id: 7 }], ["ask", "content.summarize", { text: "x" }]]);
  await new Promise((r) => setTimeout(r, 0));
  assert.deepEqual(state.summary, { title: "Done" }, "the answer lands in the named state key");
  assert.ok(calls.filter((c) => c[0] === "changed").length >= 2, "the host is told to re-render, again when the answer arrives");
});

test("malformed actions are refused without touching state", () => {
  const state = { count: 1 }, errors = [];
  assert.equal(runActions("@count +", env(state), { error: (m) => errors.push(m) }), false);
  assert.equal(state.count, 1);
  assert.equal(errors.length, 1);
  assert.ok(checkActions("count +"));
  assert.equal(checkActions("count += 1; toggle open"), null);
  runActions("@__proto__.polluted = 1; constructor.prototype.polluted = 1", env(state));
  assert.equal({}.polluted, undefined, "prototype pollution is not possible");
});

test("a store seeds each key once and copies its seed", () => {
  const seed = { todos: [{ text: "a" }], count: 0 }, store = createStore();
  store.declare(seed);
  store.state.todos.push({ text: "b" });
  store.state.count = 5;
  store.declare(seed);
  assert.equal(store.state.count, 5, "a re-render does not reset state");
  assert.equal(seed.todos.length, 1, "the scene's own data is never mutated");
  assert.equal(isLocal({ action: "@count += 1" }), true);
  assert.equal(isLocal({ action: "save" }), false);
});

test("State, Show and Each shape the rendered scene", () => {
  const scene = node("Page", { title: "Notes" }, [
    node("State", { values: { notes: [{ text: "Tide tables", done: true }, { text: "Batteries", done: false }], show: false } }, [], { id: "st" }),
    node("Text", { content: "{{ count(notes, 'done') }} of {{ len(notes) }} done" }, [], { id: "summary" }),
    node("Each", { items: "notes", as: "note" }, [node("Text", { content: "{{ index + 1 }}. {{ note.text }}" }, [], { id: "row" })], { id: "list" }),
    node("Show", { when: "show" }, [node("Text", { content: "hidden text" }, [], { id: "hidden" })], { id: "gate" }),
    node("Show", { when: "len(notes) > 1" }, [node("Text", { content: "visible text" }, [], { id: "shown" })], { id: "gate2" }),
    node("Code", { source: "ui.text(\"{{ count }}\")", plain: true }, [], { id: "code" }),
  ], { id: "page" });
  const html = renderScene(scene);
  assert.ok(html.includes("1 of 2 done"));
  assert.ok(html.includes("1. Tide tables") && html.includes("2. Batteries"));
  assert.ok(!html.includes("hidden text"));
  assert.ok(html.includes("visible text"));
  assert.ok(html.includes("{{ count }}"), "code samples are shown as written, never evaluated");
});

test("lint reports logic that does not parse, and nothing else", () => {
  const bad = node("Page", { title: "Total {{ count + }}" }, [
    node("Button", { label: "Fine {{ count }}" }, [], { id: "b", on: { click: { action: "@count +" }, hover: { action: "save" } } }),
    node("Show", { when: "a &&" }, [], { id: "s" }),
    node("Each", { items: "rows[" }, [], { id: "e" }),
    node("Input", { name: "x", bind: "user." }, [], { id: "i" }),
    node("Code", { source: "{{ never checked + }}" }, [], { id: "c" }),
    node("Text", { content: "\\{{ escaped + }}" }, [], { id: "t" }),
    node("List", { items: [{ title: "{{ nested * }}" }] }, [], { id: "l" }),
  ], { id: "p" });
  const found = lint(bad);
  assert.deepEqual(found.map((line) => line.split(":")[0]), ["p", "b", "s", "e", "i", "l"]);
  assert.ok(found[0].includes('binding "{{ count + }}" does not parse'));
  assert.ok(found[1].includes('action "@count +" does not parse'));
  const good = node("Page", { title: "{{ len(rows) }} rows" }, [node("Each", { items: "rows", as: "row" }, [node("Text", { content: "{{ row.name }}" }, [], { id: "x", on: { click: { action: "@toggle row.open; go '/x'" } } })], { id: "e" })], { id: "p" });
  assert.deepEqual(lint(good), []);
});
