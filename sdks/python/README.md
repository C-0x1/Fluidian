# Fluidian for Python

Build AI-native interfaces from Python. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Python 3.9+ |
| Verified with | CPython 3.13 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

Nothing to install inside a checkout: the CLI puts `sdks/python` on `PYTHONPATH` for the app process.
To use it elsewhere:

```bash
pip install ./sdks/python
```

## Quickstart

`examples/quickstart.py`

```python
"""Quickstart: a counter, an AI-assisted notes field and an AI summary.

    fluidian run -- python3 sdks/python/examples/quickstart.py
"""
from fluidian import AIError, App, ui

app = App("Quickstart")


@app.view
def view(ctx):
    page = ui.page(
        "Quickstart",
        ui.text("Count: %d" % ctx.state.get("count", 0)).id("count"),
        ui.button("Add one").id("add").on("click", "increment"),
        ui.text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
        ui.button("Summarise").id("summarise").on("click", "summarise"),
    )
    if "summary" in ctx.state:
        page.add(ui.callout(str(ctx.state["summary"])).id("summary"))
    return page


@app.on("increment")
def increment(ctx, event):
    ctx.state["count"] = ctx.state.get("count", 0) + 1


@app.on("set_notes")
def set_notes(ctx, event):
    ctx.state["notes"] = event.value


@app.on("summarise")
def summarise(ctx, event):
    try:
        ctx.state["summary"] = ctx.ai("content.summarize", {"text": ctx.state.get("notes", "")})["title"]
    except AIError as exc:
        ctx.toast("Could not summarise: %s" % exc, "warning")


@app.action("reset", "Reset the counter to zero", {})
def reset(ctx, event):
    ctx.state["count"] = 0


app.run()
```

Run it from the repository root:

```bash
./fluidian run -- python3 sdks/python/examples/quickstart.py
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Python

`ctx.state` is a plain `dict`. `ctx.ai()` returns a `dict` and raises `AIError`. Handlers are registered with decorators.

## Move to or from Python

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to python          # from another language to Python
./fluidian convert my-python-app/ --to all     # from a Python project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk python
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Python, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
