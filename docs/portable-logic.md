<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Portable logic

Most interaction in an interface changes nothing but the interface: a counter goes up, a tab opens, a row is ticked, a cart total updates. Portable logic lets you express that behaviour **inside the scene, as data**. The runtime interprets it in the browser, so:

- it is instant: no round trip to your application for a click that only changes what is shown;
- it is identical in every language: a Rust scene and a Lua scene with the same strings behave the same;
- it converts losslessly: [`fluidian convert`](convert.md) carries it to every SDK with nothing left to port;
- it works wherever the scene is rendered: on the web, in an installed app, in a native shell, in an embed and in a static export.

It is four ideas: **state**, **bindings**, **structure** and **actions**.

```python
ui.page("Counter",
    ui.state().prop("values", {"count": 0}),
    ui.text("{{ count }}").prop("size", "xl"),
    ui.button("Add one").on("click", "@count += 1"),
    ui.show("count >= 5", ui.callout("That is five or more")))
```

No handler exists for that button in your application. The string `@count += 1` is the behaviour.

## Contents

- [State](#state)
- [Bindings](#bindings)
- [Show and Each](#show-and-each)
- [Two-way binding](#two-way-binding)
- [Actions](#actions)
- [The expression language](#the-expression-language)
- [Functions](#functions)
- [Safety](#safety)
- [When to use a handler instead](#when-to-use-a-handler-instead)
- [A complete example in three languages](#a-complete-example-in-three-languages)

## State

A `State` node declares named values for the page it is on. It renders nothing.

```python
ui.state().prop("values", {"count": 0, "todos": [], "draft": "", "summary": None})
```

- State belongs to the route and lives as long as the page is open: going to another route and back finds it as it was left, and a reload starts from the declared values again.
- A value is seeded once. When your application sends a new scene, existing state is kept, so a server update does not undo what the person did.
- Values are plain data: numbers, strings, booleans, `null`, lists and objects.
- Several `State` nodes on a page are merged; the first declaration of a name wins.

## Bindings

Any string prop can read state with `{{ expression }}`.

```python
ui.stat("Notes", "{{ len(notes) }}")
ui.badge("{{ count(notes, 'done') }} of {{ len(notes) }} done")
ui.progress(0).prop("value", "{{ done / total * 100 }}")
ui.button("Checkout").prop("disabled", "{{ len(cart) == 0 }}")
```

| Rule | Example | Result |
| --- | --- | --- |
| A binding inside text is converted to text | `"{{ count }} items"` | `"3 items"` |
| A prop that is exactly one binding keeps the value's type | `"{{ len(cart) == 0 }}"` | `true`, a boolean |
| A missing value renders as nothing | `"Hi {{ user.name }}"` with no user | `"Hi "` |
| `\{{` writes a literal brace pair | `"Type \\{{ name }}"` | `"Type {{ name }}"` |
| Bindings work inside lists and objects in props | `items=[{"title": "{{ a }}"}]` | each string is resolved |
| `Code` and `Terminal` are never interpolated | a code sample containing `{{ }}` | shown as written |

## Show and Each

`Show` renders its children only while an expression is true.

```python
ui.show("len(cart) > 0", ui.button("Checkout").prop("variant", "primary"))
ui.show("!summary", ui.text("Nothing summarised yet."))
```

`Each` repeats its children for every item of a list. Inside, the item is available under the name given by `as` (default `item`), and its position as `index`.

```python
ui.each("todos",
    ui.row(
        ui.checkbox("done", "{{ todo.text }}").prop("bind", "todo.done"),
        ui.button("").prop("icon", "trash").on("click", "@remove todos index"),
    ),
).prop("as", "todo").prop("empty", "Nothing to do.")
```

| Prop | Meaning |
| --- | --- |
| `items` | An expression that yields a list, or a literal list |
| `as` | Name of the current item in bindings and actions; default `item` |
| `empty` | Text shown when the list is empty |
| `layout` | `stack` (default), `row` or `grid` |

`Each` blocks nest; inner names shadow outer ones. Up to 500 items are rendered.

## Two-way binding

`bind` connects an input to a place in state. The control shows the value and writes back as the person types.

```python
ui.input("draft").prop("bind", "draft")                     # text
ui.checkbox("done", "Ship it").prop("bind", "todo.done")    # boolean, inside an Each
ui.slider("seats").prop("bind", "plan.seats")               # number
ui.select("tier").prop("options", ["Team", "Scale"]).prop("bind", "tier")
```

`bind` accepts a state name or a path into an object or list item.

## Actions

An event binding whose action starts with `@` is run by the runtime instead of being sent to your application. Several actions are separated by `;`.

```python
ui.button("Add").on("click", "@push todos {text: draft, done: false}; draft = ''")
```

| Action | Form | Effect |
| --- | --- | --- |
| Assign | `name = expr` · `set name = expr` | Sets a state value or a path such as `todo.done` or `rows[2].qty` |
| Arithmetic | `count += 1` · `count -= 1` · `total *= 1.2` | `+=` on text appends |
| Toggle | `toggle open` | Flips a boolean |
| Push | `push todos {text: draft}` | Appends to a list |
| Remove | `remove todos index` · `remove tags 'urgent'` | Removes by position (a number) or by value |
| Clear | `clear draft` | Resets to the empty value of its type |
| Navigate | `go '/orders/' + id` | Client-side navigation |
| Notify | `toast 'Saved' success` | A toast; tones are `info`, `success`, `warning`, `danger`, `ai` |
| Call your application | `emit save {id: id}` | Sends the named action to a handler, with a payload |
| Call the AI kernel | `ask content.summarize {text: draft} -> summary` | Invokes a capability and stores the answer in state |

Inside an action, these names are available as well as state:

| Name | Value |
| --- | --- |
| `value` | The control's current value, for `input` and `change` events |
| `payload` | The payload of the event binding, if one was given |
| `form` | The field values of the enclosing form, for `submit` |
| the `as` name and `index` | The current item and its position, inside an `Each` |

`ask` is how a button gets intelligence without a handler:

```python
ui.button("Summarise").prop("variant", "ai").on("click",
    "@ask content.summarize {text: join(pluck(notes, 'text'), '. ')} -> summary")
ui.show("summary", ui.insight("{{ summary.title }}").prop("body", "{{ summary.summary }}"))
```

The call goes through the same kernel pipeline as every other capability: consent, redaction, budget, caching and provenance all apply.

## The expression language

A small, strict language for reading data. It has no statements, no assignment and no way to define functions.

| Kind | Syntax |
| --- | --- |
| Literals | `42`, `3.5`, `'text'`, `"text"`, `true`, `false`, `null` |
| Lists and objects | `[1, 2, count]`, `{text: draft, done: false}` |
| Names and paths | `count`, `user.name`, `rows[0].price`, `todo.tags[index]` |
| Arithmetic | `+`, `-`, `*`, `/`, `%`; `+` joins text |
| Comparison | `==`, `!=`, `<`, `<=`, `>`, `>=` |
| Logic | `&&`, `\|\|`, `!` |
| Choice | `count > 3 ? 'many' : 'few'` |
| Calls | `len(todos)`, `round(total * 1.2, 2)` |
| Grouping | `(a + b) * c` |

An expression that fails to parse, or that reads something that is not there, evaluates to nothing rather than raising an error. In development mode the runtime checks every binding, `when`, `items`, `bind` and `@` action of each scene it receives, and lists the ones that do not parse beside the engine's scene repairs.

## Functions

| Function | Returns |
| --- | --- |
| `len(x)` | Length of a list or text, or number of keys of an object |
| `sum(list)` · `sum(list, 'key')` | Total of the numbers, or of one field |
| `count(list)` · `count(list, 'key')` · `count(list, 'key', value)` | How many items are truthy, have a truthy field, or have a field equal to a value |
| `where(list, 'key')` · `where(list, 'key', value)` | The matching items |
| `without(list, 'key')` · `without(list, 'key', value)` | The items that do not match |
| `pluck(list, 'key')` | One field from every item |
| `first(list)` · `last(list)` | An end of a list |
| `join(list, sep)` | Text; the separator defaults to `", "` |
| `includes(x, value)` | Whether a list contains a value or text contains a fragment |
| `min(…)` · `max(…)` | Smallest or largest of numbers or lists of numbers |
| `round(n, digits)` · `floor(n)` · `ceil(n)` · `abs(n)` | Rounding and magnitude |
| `num(x)` · `str(x)` | Conversion |
| `upper(s)` · `lower(s)` · `trim(s)` | Text |
| `default(x, fallback)` | The fallback when a value is missing or empty |
| `money(n, 'USD')` · `percent(n, digits)` | Formatted text: `$1,234.50`, `12%` |
| `plural(n, 'note')` · `plural(n, 'person', 'people')` | The right word form for a count |

## Safety

Portable logic is data from your application, and it is treated with the same suspicion as any other data.

- Expressions and actions are parsed by a hand-written parser and interpreted over an abstract syntax tree. There is no `eval`, no `Function` and no generated code.
- Only own properties of plain data can be read. `constructor`, `__proto__` and `prototype` are refused, on reads and on writes.
- The language cannot name globals: there is no `window`, `document`, `fetch` or `this`.
- Actions can change page state and can ask the host for five things: navigate, notify, emit an action, call a capability, re-render. They can do nothing else.
- `ask` and `emit` go through the same session token, consent and budget checks as any other request.

These properties are covered by the runtime tests in `tests/runtime/logic.test.mjs`.

## When to use a handler instead

Use a handler in your application when the work needs your server: reading or writing your database, calling another service, enforcing a permission, or anything that must not be decided in the browser. A common shape is portable logic for the interaction and one `emit` at the end:

```python
ui.button("Place order").on("click", "@emit place_order {items: cart, total: sum(cart, 'price')}")
```

```python
@app.on("place_order")
def place_order(ctx, event):
    order = save_order(event.payload)      # your code; the payload is validated here, not trusted
    ctx.navigate("/orders/%s" % order.id)
```

State in the scene and state in your application can be used together: `ctx.state` holds what the server knows, a `State` node holds what the page is doing.

## A complete example in three languages

The same to-do list. The strings are identical; only the builder syntax differs.

**Python**

```python
ui.page("To do",
    ui.state().prop("values", {"todos": [], "draft": ""}),
    ui.row(ui.input("draft").prop("bind", "draft"),
           ui.button("Add").on("click", "@push todos {text: draft, done: false}; draft = ''")),
    ui.each("todos",
        ui.checkbox("done", "{{ todo.text }}").prop("bind", "todo.done")).prop("as", "todo"),
    ui.badge("{{ count(todos, 'done') }} of {{ len(todos) }} done"))
```

**Go**

```go
fl.Page("To do",
	fl.State().Prop("values", fl.M{"todos": fl.A{}, "draft": ""}),
	fl.Row(fl.Input("draft").Prop("bind", "draft"),
		fl.Button("Add").On("click", "@push todos {text: draft, done: false}; draft = ''")),
	fl.Each("todos",
		fl.Checkbox("done", "{{ todo.text }}").Prop("bind", "todo.done")).Prop("as", "todo"),
	fl.Badge("{{ count(todos, 'done') }} of {{ len(todos) }} done"))
```

**Rust**

```rust
ui::page("To do", vec![
    ui::state().prop("values", jobj! {"todos" => jarr![], "draft" => ""}),
    ui::row(vec![ui::input("draft").prop("bind", "draft"),
        ui::button("Add").on("click", "@push todos {text: draft, done: false}; draft = ''")]),
    ui::each("todos", vec![
        ui::checkbox("done", "{{ todo.text }}").prop("bind", "todo.done")]).prop("as", "todo"),
    ui::badge("{{ count(todos, 'done') }} of {{ len(todos) }} done"),
])
```

Try it live: `./fluidian gallery` and open **Portable logic**, or run `./fluidian run examples/portable/app.py`.
