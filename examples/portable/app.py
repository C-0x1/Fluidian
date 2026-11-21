"""Field Notes: one small application, written once, that runs in every SDK language.

Run it:

    ./fluidian run examples/portable/app.py

Convert it to the other thirteen languages and verify each result:

    ./fluidian convert examples/portable/app.py --to all --probe

What makes it portable:

* the notes screen keeps its behaviour in the scene itself (a ``State`` node,
  ``{{ }}`` bindings and ``@`` actions), so it behaves identically wherever the
  scene is rendered;
* the trips screen uses ordinary server-side handlers, which the converter
  reproduces by observing them, or leaves as clearly marked stubs.
"""
from fluidian import App, ui

app = App("Field Notes")

NAV = [
    {"label": "Notes", "icon": "book", "route": "/"},
    {"label": "Trips", "icon": "map", "route": "/trips"},
    {"label": "About", "icon": "info", "route": "/about"},
]
NOTES = [
    {"text": "Tide tables for the north shore", "done": True},
    {"text": "Charge the camera batteries", "done": False},
    {"text": "Pack the waterproof notebook", "done": False},
]
TRIPS = [
    {"name": "Skerry Point", "when": "12 to 14 June", "kind": "coast", "hue": 205, "route": "/trips/skerry-point", "notes": 14},
    {"name": "Larch Hollow", "when": "3 to 5 July", "kind": "forest", "hue": 150, "route": "/trips/larch-hollow", "notes": 9},
    {"name": "Kettle Ridge", "when": "22 to 25 August", "kind": "peaks", "hue": 28, "route": "/trips/kettle-ridge", "notes": 21},
]


def shell(route, *children):
    nav = [dict(item, active=item["route"] == route) for item in NAV]
    return ui.theme(
        ui.shell("Field Notes", *children).prop("tagline", "Portable example").prop("nav", nav).id("shell"),
    ).prop("preset", "forest").id("root")


def notes(ctx):
    add = "@push notes {text: default(draft, 'Check the weather window'), done: false}; draft = ''"
    summarise = "@ask content.summarize {text: join(pluck(notes, 'text'), '. ')} -> summary"
    return shell("/", ui.page(
        "Notes",
        ui.state().prop("values", {"notes": NOTES, "draft": "", "summary": None}),
        ui.grid(
            ui.stat("Notes", "{{ len(notes) }}").prop("icon", "book").id("stat-notes"),
            ui.stat("Done", "{{ count(notes, 'done') }}").prop("icon", "check").prop("tone", "success").id("stat-done"),
            ui.stat("Open", "{{ len(notes) - count(notes, 'done') }}").prop("icon", "clock").id("stat-open"),
        ).prop("columns", 3),
        ui.card(
            ui.row(
                ui.input("draft").prop("placeholder", "Add a note").prop("bind", "draft").id("draft"),
                ui.button("Add").prop("variant", "primary").prop("icon", "plus").on("click", add).id("add"),
            ).prop("wrap", False).prop("align", "end"),
            ui.each(
                "notes",
                ui.row(
                    ui.checkbox("done", "{{ note.text }}").prop("bind", "note.done"),
                    ui.button("").prop("icon", "trash").prop("variant", "ghost").prop("size", "sm").on("click", "@remove notes index"),
                ).prop("justify", "between").prop("wrap", False),
            ).prop("as", "note").prop("empty", "No notes yet.").id("list"),
            ui.row(
                ui.badge("{{ count(notes, 'done') }} of {{ len(notes) }} done").prop("tone", "brand").id("progress"),
                ui.button("Summarise").prop("variant", "ai").prop("size", "sm").on("click", summarise).id("summarise"),
            ).prop("justify", "between"),
            ui.show("summary", ui.insight("{{ summary.title }}").prop("body", "{{ summary.summary }}").prop("tone", "ai")).id("summary"),
        ).prop("title", "Before you leave").prop("subtitle", "State, bindings and actions live in the scene; no handler runs for any of this."),
    ).prop("subtitle", "A checklist that works the same in fourteen languages.").prop("width", "narrow"))


def trips(ctx):
    cards = []
    for trip in TRIPS:
        cards.append(ui.card(
            ui.art(trip["kind"]).prop("hue", trip["hue"]).prop("ratio", "16:9").prop("label", trip["name"]),
            ui.row(
                ui.badge("%d notes" % trip["notes"]).prop("tone", "brand"),
                ui.button("Open").prop("variant", "primary").prop("size", "sm").on("click", "go", {"route": trip["route"]}),
            ).prop("justify", "between"),
        ).prop("title", trip["name"]).prop("subtitle", trip["when"]))
    return shell("/trips", ui.page(
        "Trips",
        ui.grid(*cards).prop("columns", 3),
        ui.row(
            ui.button("Share the list").prop("icon", "share").on("click", "share"),
            ui.button("Plan a trip").prop("variant", "ai").prop("icon", "sparkles").on("click", "plan_trip"),
        ),
    ).prop("subtitle", "Opening a trip is a server-side handler; the converter reproduces it from what it observes."))


def trip(ctx, entry):
    return shell("/trips", ui.page(
        entry["name"],
        ui.breadcrumbs().prop("items", [{"label": "Trips", "route": "/trips"}, {"label": entry["name"]}]),
        ui.hero(entry["name"], ui.button("Back to trips").prop("icon", "arrow-left").on("click", "go", {"route": "/trips"}))
        .prop("subtitle", "%s · %d notes" % (entry["when"], entry["notes"])).prop("tone", "glow").prop("eyebrow", "Trip"),
        ui.art(entry["kind"]).prop("hue", entry["hue"]).prop("ratio", "21:9").prop("label", entry["name"]),
    ).prop("width", "narrow"))


def about(ctx):
    return shell("/about", ui.page(
        "About",
        ui.callout("Written once").prop("tone", "ai").prop(
            "body", "This application is a single Python file. Every other language version in this folder was produced by fluidian convert "
                    "and checked against this one, scene by scene."),
        ui.key_value().prop("items", [
            {"key": "Screens", "value": "%d" % (3 + len(TRIPS))},
            {"key": "Portable behaviour", "value": "State, Show, Each, bindings, @ actions"},
            {"key": "Handlers", "value": "go, share, plan_trip, export_notes"},
        ]),
    ).prop("width", "narrow"))


@app.view
def view(ctx):
    route = (ctx.route or "/").rstrip("/") or "/"
    entry = next((t for t in TRIPS if t["route"] == route), None)
    if entry:
        return trip(ctx, entry)
    return {"/": notes, "/trips": trips, "/about": about}.get(route, notes)(ctx)


@app.on("go")
def go(ctx, event):
    ctx.navigate(event.payload["route"])


@app.on("share")
def share(ctx, event):
    ctx.toast("Link copied to the clipboard", "success")


@app.on("plan_trip")
def plan_trip(ctx, event):
    ctx.state["plans"] = ctx.state.get("plans", 0) + 1
    ctx.toast("Plan %d started" % ctx.state["plans"])


@app.action("export_notes", "Export every note as a file", {"format": "string csv or json"})
def export_notes(ctx, event):
    ctx.state["exports"] = ctx.state.get("exports", 0) + 1


app.run()
