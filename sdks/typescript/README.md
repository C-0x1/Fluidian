# Fluidian for TypeScript

Build AI-native interfaces from TypeScript. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | TypeScript 4.5+, target ES2019 |
| Verified with | TypeScript 7.0 on Node.js 22 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```bash
cd sdks/typescript && tsc -p .          # emits dist/
npm install /path/to/fluidian/sdks/typescript
```

## Quickstart

`src/quickstart.ts`

```ts
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   tsc -p sdks/typescript && fluidian run -- node sdks/typescript/dist/quickstart.js
import { AIError, App, ui } from "./index";

const app = new App("Quickstart");

app.view((ctx) => {
  const page = ui.page(
    "Quickstart",
    ui.text(`Count: ${ctx.state.count ?? 0}`).id("count"),
    ui.button("Add one").id("add").on("click", "increment"),
    ui.textArea("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
    ui.button("Summarise").id("summarise").on("click", "summarise"),
  );
  if ("summary" in ctx.state) page.add(ui.callout(String(ctx.state.summary)).id("summary"));
  return page;
});

app.on("increment", (ctx) => { ctx.state.count = (ctx.state.count ?? 0) + 1; });
app.on("set_notes", (ctx, event) => { ctx.state.notes = event.value; });
app.on("summarise", (ctx) => {
  try {
    ctx.state.summary = ctx.ai("content.summarize", { text: ctx.state.notes ?? "" }).title;
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
tsc -p sdks/typescript
./fluidian run -- node sdks/typescript/dist/quickstart.js
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for TypeScript

Fully typed builders and handlers; no `@types/node` needed. `ctx.ai()` is synchronous and throws `AIError`.

## Move to or from TypeScript

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to typescript          # from another language to TypeScript
./fluidian convert my-typescript-app/ --to all     # from a TypeScript project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk typescript
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into TypeScript, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
