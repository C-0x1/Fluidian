# Fluidian for JavaScript

Build AI-native interfaces from JavaScript. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Node.js 14+ (CommonJS) |
| Verified with | Node.js 22 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```bash
npm install /path/to/fluidian/sdks/javascript   # then: require("fluidian")
```

## Quickstart

`examples/quickstart.js`

```js
"use strict";
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- node sdks/javascript/examples/quickstart.js
const { App, AIError, ui } = require("../index.js");

const app = new App("Quickstart");

app.view((ctx) => {
  const page = ui.page(
    "Quickstart",
    ui.text(`Count: ${ctx.state.count || 0}`).id("count"),
    ui.button("Add one").id("add").on("click", "increment"),
    ui.textArea("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
    ui.button("Summarise").id("summarise").on("click", "summarise"),
  );
  if ("summary" in ctx.state) page.add(ui.callout(String(ctx.state.summary)).id("summary"));
  return page;
});

app.on("increment", (ctx) => { ctx.state.count = (ctx.state.count || 0) + 1; });
app.on("set_notes", (ctx, event) => { ctx.state.notes = event.value; });
app.on("summarise", (ctx) => {
  try {
    ctx.state.summary = ctx.ai("content.summarize", { text: ctx.state.notes || "" }).title;
  } catch (err) {
    if (!(err instanceof AIError)) throw err;
    ctx.toast(`Could not summarise: ${err.message}`, "warning");
  }
});
app.action("reset", "Reset the counter to zero", {}, (ctx) => { ctx.state.count = 0; });

app.run();
```

Run it from the repository root:

```bash
./fluidian run -- node sdks/javascript/examples/quickstart.js
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for JavaScript

`ctx.state` is a plain object. `ctx.ai()` is synchronous: the SDK reads the reply from stdin, so handlers need no `await`. It throws `AIError`.

## Move to or from JavaScript

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to javascript          # from another language to JavaScript
./fluidian convert my-javascript-app/ --to all     # from a JavaScript project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk javascript
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into JavaScript, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
