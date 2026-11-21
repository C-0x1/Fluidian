"""Conformance application: exercises every SDK feature against the shared transcript."""
from fluidian import AIError, App, ui

from conformance_scene import conformance_scene

app = App("Conformance")


@app.view
def view(ctx):
    page = ui.page(
        "Conformance",
        ui.text("Count: %d" % ctx.state.get("count", 0)).id("count"),
        ui.text("Hello, %s!" % ctx.state.get("name", "world")).id("greeting"),
        ui.text("Route: %s" % ctx.route).id("route"),
    ).id("root")
    if "summary" in ctx.state:
        page.add(ui.text("Summary: %s" % ctx.state["summary"]).id("summary"))
    if "last" in ctx.state:
        page.add(ui.text("Last: %s" % ctx.state["last"]).id("last"))
    page.add(ui.button("Increment").id("inc").on("click", "increment"))
    page.add(conformance_scene())
    return page


@app.on("increment")
def increment(ctx, event):
    ctx.state["count"] = ctx.state.get("count", 0) + 1


@app.on("set_name")
def set_name(ctx, event):
    ctx.state["name"] = event.value


@app.on("submit")
def submit(ctx, event):
    f = event.form
    ctx.toast("Saved %s (%s × %s)" % (f["email"], f["plan"], f["seats"]), "success")


@app.on("ask_ai")
def ask_ai(ctx, event):
    ctx.state["summary"] = ctx.ai("content.summarize", {"text": "Fluidian"})["title"]


@app.on("fail_ai")
def fail_ai(ctx, event):
    try:
        ctx.ai("content.summarize", {})
    except AIError as exc:
        ctx.toast("AI unavailable: %s" % exc, "warning")


@app.on("go")
def go(ctx, event):
    ctx.navigate(event.payload["route"])


@app.on("boom")
def boom(ctx, event):
    raise RuntimeError("boom")


@app.action("add_item", "Add an item to the list", {"title": "string title"})
def add_item(ctx, event):
    ctx.state["last"] = event.payload["title"]


app.run()
