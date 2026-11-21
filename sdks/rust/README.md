# Fluidian for Rust

Build AI-native interfaces from Rust. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Rust 2021 edition |
| Verified with | Rust 1.97 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```toml
# Cargo.toml
[dependencies]
fluidian = { path = "/path/to/fluidian/sdks/rust" }
```

## Quickstart

`examples/quickstart.rs`

```rust
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- cargo run --quiet --example quickstart
use fluidian::{jobj, ui, App};

fn main() {
    let mut app = App::new("Quickstart");

    app.view(|ctx| {
        let mut page = ui::page("Quickstart", vec![
            ui::text(&format!("Count: {}", ctx.state.int("count"))).id("count"),
            ui::button("Add one").id("add").on("click", "increment"),
            ui::text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
            ui::button("Summarise").id("summarise").on("click", "summarise"),
        ]);
        if ctx.state.has("summary") {
            page = page.push(ui::callout(&ctx.state.text("summary", ""), vec![]).id("summary"));
        }
        page
    });

    app.on("increment", |ctx, _| {
        let next = ctx.state.int("count") + 1;
        ctx.state.set("count", next);
        Ok(())
    });
    app.on("set_notes", |ctx, ev| {
        ctx.state.set("notes", &ev.value);
        Ok(())
    });
    app.on("summarise", |ctx, _| {
        let notes = ctx.state.text("notes", "");
        match ctx.ai("content.summarize", jobj! {"text" => notes}) {
            Ok(result) => ctx.state.set("summary", result.get("title")),
            Err(error) => ctx.toast(&format!("Could not summarise: {}", error), "warning"),
        }
        Ok(())
    });
    app.action("reset", "Reset the counter to zero", jobj! {}, |ctx, _| {
        ctx.state.set("count", 0);
        Ok(())
    });

    app.run();
}
```

Run it from the repository root:

```bash
cd sdks/rust && ../../fluidian run -- cargo run --quiet --example quickstart
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Rust

Handlers return `fluidian::Result`, so `?` works on `ctx.ai(...)`. `jobj!` and `jarr!` build JSON literals. Builders consume and return the node.

## Move to or from Rust

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to rust          # from another language to Rust
./fluidian convert my-rust-app/ --to all     # from a Rust project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk rust
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Rust, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
