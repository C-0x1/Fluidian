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
