"""Fluidian Gallery.

A tour of the component library and the AI capabilities, written with the
Python SDK.  Start it with ``./fluidian gallery`` and open the printed URL.

Every page works offline.  Without an API key the engine answers from its
built-in Reflex heuristics; with ``OPENAI_API_KEY`` set, the same pages are
served by the model with no change to this file.
"""
import json
import os
from urllib.parse import quote

from fluidian import AIError, App, ui

import sample as S

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with open(os.path.join(ROOT, "spec", "capabilities.json"), encoding="utf-8") as fh:
    CATALOG = json.load(fh)
CAPS = CATALOG["capabilities"]
with open(os.path.join(ROOT, "spec", "components.json"), encoding="utf-8") as fh:
    COMPONENT_COUNT = len(json.load(fh)["components"])

app = App("Fluidian Gallery")
PAGES = []
SECTIONS = ["Start", "Compose", "Input", "Command", "Data", "Design", "Experience", "Trust", "Build", "Library"]
_ANSWERS = {}


# ---------------------------------------------------------------- helpers

def page(route, section, label, icon):
    """Register a gallery page under a navigation section."""
    def register(build):
        PAGES.append({"route": route, "section": section, "label": label, "icon": icon, "build": build})
        return build
    return register


def P(node, **props):
    """Set several props at once."""
    for key, value in props.items():
        node.prop(key, value)
    return node


def ask(ctx, capability, payload):
    """Invoke a capability once and remember the answer, so pages stay instant on revisit."""
    key = capability + json.dumps(payload, sort_keys=True)
    if key not in _ANSWERS:
        try:
            _ANSWERS[key] = ctx.ai(capability, payload)
        except AIError as exc:
            return {"error": str(exc)}
    return _ANSWERS[key]


def card(title, *children, **props):
    return P(ui.card(*children), title=title, **props)


def muted(text, size="sm"):
    return P(ui.text(text), tone="muted", size=size)


def kv(pairs, columns=1):
    return P(ui.key_value(), items=[{"key": k, "value": v} for k, v in pairs], columns=columns)


def powered_by(*capabilities):
    """A row of chips naming the capabilities behind a demo."""
    return P(ui.row(*[P(ui.badge(c), tone="ai", variant="outline", icon="sparkles") for c in capabilities]), gap="xs")


def swatches(colours, height=56):
    """Render a strip of colours as an inline SVG image."""
    width = 60
    rects = "".join('<rect x="%d" y="0" width="%d" height="%d" fill="%s"/>' % (i * width, width, height, c) for i, c in enumerate(colours))
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="none">%s</svg>' % (len(colours) * width, height, rects)
    return P(ui.image("data:image/svg+xml;utf8," + quote(svg, safe="/:=,;'()")), alt="Colour swatches: " + ", ".join(colours), ratio="%d:%d" % (len(colours) * width, height))


# ---------------------------------------------------------------- start

@page("/", "Start", "Overview", "home")
def overview(ctx):
    counts = {}
    for cap in CAPS:
        counts[cap["category"]] = counts.get(cap["category"], 0) + 1
    cards = []
    for cat in CATALOG["categories"]:
        titles = [c["title"] for c in CAPS if c["category"] == cat["id"]][:3]
        cards.append(card(cat["title"], muted(cat["blurb"]), P(ui.row(*[ui.tag(t) for t in titles]), gap="xs"),
                          eyebrow="%d capabilities" % counts.get(cat["id"], 0)))
    return P(ui.page(
        "",
        P(ui.hero(
            "Interfaces that think.",
            P(ui.row(
                P(ui.button("See generative UI"), variant="primary", icon="sparkles", size="lg").on("click", "go", {"route": "/compose"}),
                P(ui.button("Browse all capabilities"), variant="ghost", icon="arrow-right", size="lg").on("click", "go", {"route": "/capabilities"}),
                P(ui.kbd("Ctrl+K")), muted("opens the Intent Bar anywhere"),
            ), gap="sm"),
        ), eyebrow="Fluidian gallery", tone="aurora",
            subtitle="A server-driven UI framework with an AI kernel built in. This gallery is an ordinary Fluidian app written in "
                     "Python: every screen is a few lines of code, rendered by the same runtime you ship to production."),
        P(ui.grid(
            P(ui.stat("AI capabilities", str(len(CAPS))), icon="sparkles", hint="in %d categories" % len(CATALOG["categories"]), tone="ai"),
            P(ui.stat("Components", str(COMPONENT_COUNT)), icon="layers", hint="layout, data, commerce, marketing, AI"),
            P(ui.stat("Language SDKs", "14"), icon="code", hint="one wire protocol"),
            P(ui.stat("Works offline", "100%"), icon="bolt", hint="Reflex engine, no key required"),
        ), columns=4),
        P(ui.section("Fifteen families of AI-native behaviour", P(ui.grid(*cards), columns=3)),
          description="Each capability is declared once in the engine and is available to every SDK."),
    ), width="wide")


@page("/dashboard", "Start", "Live dashboard", "chart")
def dashboard(ctx):
    greeting = ask(ctx, "ambient.greeting", {"name": "Mira", "pending": "4 invoices are overdue"}).get("text", "Welcome back, Mira")
    overdue = [r for r in S.INVOICES if r["status"] == "Overdue"]
    return P(ui.page(
        "Revenue desk",
        P(ui.grid(
            P(ui.stat("Revenue, year to date", "$2.69M"), delta="+18.4%", spark=[r["revenue"] for r in S.REVENUE], icon="dollar", hint="vs last year"),
            P(ui.stat("Orders", "18,238"), delta="+12.1%", spark=[r["orders"] for r in S.REVENUE], icon="cart", hint="vs last year"),
            P(ui.stat("Average order value", "$147.50"), delta="+5.6%", icon="tag", hint="rolling 90 days"),
            P(ui.stat("Overdue invoices", str(len(overdue))), delta="$%s outstanding" % format(sum(r["amount"] for r in overdue), ","),
              trend="down", icon="alert", tone="warning"),
        ), columns=4),
        P(ui.split(
            card("Revenue by month",
                 P(ui.chart("area"), data=S.REVENUE, x="month", y="revenue", height=300).id("revenue-chart")
                 .ai("data.forecast", {"horizon": 3}).ai("data.anomaly"),
                 subtitle="With a three-month forecast and automatic anomaly detection"),
            ui.stack(
                card("What changed", muted("Twelve months of revenue, read by the kernel.").id("revenue-read")
                     .ai("data.insights", {"data": S.REVENUE, "x": "month", "y": "revenue"})),
                card("Suggested next steps", ui.suggestions().id("next-steps")
                     .ai("command.next_actions", {"goal": "collect overdue invoices", "recent": ["opened revenue desk"]})),
            ),
        ), ratio="5:3"),
        card("Receivables", P(ui.table(), columns=S.INVOICE_COLUMNS, rows=S.INVOICES, pageSize=6).id("receivables").ai("data.query"),
             subtitle="Filter in plain language, or click a column to sort"),
    ), subtitle=greeting, width="wide")


@page("/capabilities", "Start", "Capability explorer", "search")
def capabilities(ctx):
    titles = {c["id"]: c["title"] for c in CATALOG["categories"]}
    rows = [{"capability": c["id"], "title": c["title"], "family": titles[c["category"]], "kind": c["kind"], "surface": c["present"],
             "tier": c["tier"], "offline": "Yes" if c["nativeReflex"] else "Model"} for c in CAPS]
    columns = [{"key": "capability", "label": "Capability"}, {"key": "title", "label": "Title"}, {"key": "family", "label": "Family"},
               {"key": "kind", "label": "Kind", "format": "text"}, {"key": "surface", "label": "Surface", "format": "text"},
               {"key": "tier", "label": "Model tier", "format": "text"}, {"key": "offline", "label": "Offline", "format": "text"}]
    kinds = {}
    for c in CAPS:
        kinds[c["kind"]] = kinds.get(c["kind"], 0) + 1
    return P(ui.page(
        "Capability explorer",
        P(ui.grid(
            P(ui.stat("Model capabilities", str(kinds.get("model", 0))), hint="strict JSON-schema outputs", icon="cpu"),
            P(ui.stat("Hybrid capabilities", str(kinds.get("hybrid", 0))), hint="engine computes, model narrates", icon="branch"),
            P(ui.stat("Direct capabilities", str(kinds.get("direct", 0))), hint="deterministic, zero tokens", icon="bolt"),
            P(ui.stat("Surfaces", str(len({c["present"] for c in CAPS}))), hint="ways a result reaches the screen", icon="layers"),
        ), columns=4),
        card("All capabilities", P(ui.table(), columns=columns, rows=rows, pageSize=12, dense=True, striped=True).id("capability-table")
             .ai("data.query", {"placeholder": "Try “kind is direct” or “family contains trust”"})),
    ), subtitle="Every capability the engine exposes, with its family, execution kind and the surface that presents it.", width="wide")


# ---------------------------------------------------------------- compose

@page("/compose", "Compose", "Generative UI", "sparkles")
def compose(ctx):
    return P(ui.page(
        "Generative interfaces",
        P(ui.split(
            ui.generative("Collect feedback after a support call").id("gen-feedback"),
            ui.generative("Onboard a new customer in four steps").id("gen-onboard"),
        ), ratio="1:1"),
        P(ui.split(
            card("From a JSON Schema", P(ui.smart_form("signup"), schema=S.SIGNUP_SCHEMA, submitLabel="Create workspace").id("signup").on("submit", "saved"),
                 subtitle="SmartForm infers controls, labels, order and validation"),
            card("From a data set", P(ui.generative("Monthly revenue and orders"), capability="compose.data_view",
                                      input={"data": S.REVENUE[:8], "title": "Monthly revenue", "question": "how is revenue trending?"}).id("gen-data"),
                 subtitle="The kernel picks the chart, the measures and the table"),
        ), ratio="1:1"),
    ), subtitle="Describe the outcome. The kernel composes a scene from the component registry, validates it against the schema and streams it "
                "into place. Type in the refine bar to change it.", width="wide")


LOGIC_SNIPPET = """ui.state().prop("values",
    {"count": 0, "todos": [], "draft": ""})

ui.text("{{ count }}")
ui.button("Add one").on("click", "@count += 1")

ui.input("draft").prop("bind", "draft")
ui.button("Add").on("click",
    "@push todos {text: draft, done: false}; draft = ''")
ui.each("todos",
    ui.checkbox("done", "{{ todo.text }}")
      .prop("bind", "todo.done"),
).prop("as", "todo")
ui.text("{{ count(todos, 'done') }} of {{ len(todos) }} done")

ui.button("Summarise").on("click",
    "@ask content.summarize {text: join(pluck(todos, 'text'), '. ')} -> summary")
"""


@page("/logic", "Compose", "Portable logic", "bolt")
def logic(ctx):
    todos = [{"text": "Send the Q3 board pack", "done": True}, {"text": "Review Ana's pull request", "done": False}, {"text": "Renew the domain", "done": False}]
    counter = card("Counter",
                   P(ui.text("{{ count }}"), size="xl", weight="bold").id("count-value"),
                   P(ui.row(P(ui.button("Subtract"), icon="minus").on("click", "@count -= 1").id("count-sub"), P(ui.button("Add one"), variant="primary", icon="plus").on("click", "@count += 1").id("count-add"),
                            P(ui.button("Reset"), variant="ghost").on("click", "@count = 0").id("count-reset")), gap="sm"),
                   P(ui.show("count >= 5", P(ui.callout("That is five or more"), tone="success", body="This callout is a Show node: it exists only while its expression is true.")), ).id("count-show"),
                   subtitle="The button's action is the string “@count += 1”. No handler runs in your app.")
    todo = card("To-do list",
                P(ui.row(P(ui.input("draft"), placeholder="What needs doing?", bind="draft").id("todo-draft"),
                         P(ui.button("Add"), variant="primary").on("click", "@push todos {text: default(draft, 'Book the venue for the offsite'), done: false}; draft = ''").id("todo-add")), wrap=False, align="end"),
                P(ui.each("todos", P(ui.row(P(ui.checkbox("done", "{{ todo.text }}"), bind="todo.done").id("todo-check"),
                                            P(ui.button(""), icon="trash", variant="ghost", size="sm").on("click", "@remove todos index").id("todo-remove")), justify="between", wrap=False)), **{"as": "todo", "empty": "Nothing to do."}).id("todo-list"),
                P(ui.row(P(ui.badge("{{ count(todos, 'done') }} of {{ len(todos) }} done"), tone="brand").id("todo-count"),
                         P(ui.button("Summarise with AI"), variant="ai", size="sm").on("click", "@ask content.summarize {text: join(pluck(todos, 'text'), '. ')} -> summary").id("todo-ask")), justify="between"),
                ui.show("summary", P(ui.insight("{{ summary.title }}"), body="{{ summary.summary }}", tone="ai").id("todo-summary")),
                subtitle="State, a two-way binding, a repeated row and a call to the AI kernel, all without a server round trip.")
    return P(ui.page(
        "Portable logic",
        P(ui.state(), values={"count": 0, "todos": todos, "draft": "", "summary": None}),
        P(ui.split(ui.stack(counter, todo),
                   ui.stack(card("The whole page, in the Python SDK", P(ui.code(LOGIC_SNIPPET), language="python", title="logic.py"),
                                 subtitle="Because behaviour is data inside the scene, this page is identical in all fourteen SDK languages."),
                            P(ui.callout("Convert it"), tone="ai", body="fluidian convert examples/gallery/app.py --no-follow --route /logic --to all writes this page in the other thirteen languages, then builds each one and checks that it serves the same scene."),
                            card("Expression language", kv([("State", "A State node, read with \\{{ name }}"), ("Actions", "set, +=, -=, toggle, push, remove, clear, go, toast, emit, ask"),
                                                             ("Functions", "len, sum, count, where, pluck, join, round, upper, default, money…"), ("Safety", "Parsed and interpreted; never eval")]))), ), ratio="1:1"),
    ), subtitle="Behaviour written as data: bindings read client state and actions change it, in the runtime. The same scene behaves identically in every SDK language and on every platform.",
        width="wide")


def _wallet():
    return P(ui.screen("Wallet",
                       P(ui.stat("Balance", "$12,480.55"), delta="+2.1%", hint="this month"),
                       P(ui.row(P(ui.button("Send"), variant="primary", icon="arrow-up"), P(ui.button("Request"), icon="arrow-down")), gap="xs", wrap=False),
                       P(ui.toggle("round", "Round up purchases"), checked=True),
                       P(ui.segmented("range"), options=["Week", "Month", "Year"], value="Month"),
                       P(ui.card(P(ui.list(), items=[{"title": "Verano Coffee", "detail": "Today", "meta": "-$4.80", "icon": "coffee"}, {"title": "Salary", "detail": "Yesterday", "meta": "+$4,250", "icon": "briefcase", "tone": "success"}])), title="Recent", padding="sm")),
             subtitle="Mira Okafor", trailing=["bell"], tabs=[{"label": "Home", "icon": "home", "active": True}, {"label": "Pay", "icon": "swap"}, {"label": "You", "icon": "user"}], fab={"icon": "plus"})


@page("/platforms", "Experience", "Platform preview", "smartphone")
def platforms(ctx):
    return P(ui.page(
        "One scene, every platform",
        P(ui.row(P(ui.device_frame(_wallet()), kind="phone", platform="ios", caption="iOS skin", height=640),
                 P(ui.device_frame(_wallet()), kind="phone", platform="android", caption="Android skin", height=640),
                 P(ui.device_frame(_wallet()), kind="phone", platform="ios", theme="midnight", caption="iOS skin · Midnight theme", height=640)), justify="center", gap="xl", align="start"),
        P(ui.grid(card("Automatic", muted("The runtime reads the host platform and applies the matching skin: large titles and grouped surfaces on iOS, Material conventions on Android, the standard look on the web.")),
                  card("Previewable", muted("DeviceFrame renders any scene with any skin and theme, so you can review all three side by side from a laptop.")),
                  card("Packaged", muted("fluidian package builds an installable web app and generates the Xcode and Android Studio shell projects around the same scene."))), columns=3),
    ), subtitle="The wallet below is one function. The frames differ only in the platform they announce.", width="wide")


ART_KINDS = ["bottle", "jar", "tube", "can", "candle", "vase", "mug", "speaker", "headphones", "watch", "phone", "glasses", "lamp", "plant", "fruit", "box", "bag", "card", "dish", "burger", "portrait",
             "mesh", "orbs", "rings", "waves", "grid", "dots", "blocks", "topo", "beams", "facets", "orbit", "aurora", "peaks", "dunes", "coast", "city", "forest", "ui", "cover", "poster", "glyph", "qr", "weather"]
THEME_NAMES = ["iris", "midnight", "aurora", "sunset", "ember", "ocean", "forest", "moss", "rose", "grape", "citrus", "sand", "graphite", "paper", "terminal", "crimson", "candy", "mint", "gold", "sky"]


@page("/art", "Design", "Artwork and themes", "image")
def artwork(ctx):
    tiles = [ui.stack(P(ui.art(kind), hue=(i * 47) % 360, ratio="1:1", seed=i + 1), P(ui.text(kind), size="xs", tone="muted", align="center")).prop("gap", "xs") for i, kind in enumerate(ART_KINDS)]
    swatches_ = [P(ui.theme(P(ui.card(P(ui.row(P(ui.text(name.capitalize()), weight="bold"), P(ui.badge("Aa"), tone="brand")), justify="between"),
                                      P(ui.row(P(ui.button("Primary"), variant="primary", size="sm"), P(ui.badge("AI"), tone="ai", icon="sparkles")), gap="xs"), P(ui.progress(64), showValue=False)), padding="md")), preset=name) for name in THEME_NAMES]
    return P(ui.page(
        "Artwork and themes",
        card("Forty-four kinds of procedural artwork", P(ui.grid(*tiles), columns=11, gap="sm"),
             subtitle="Product shots, landscapes and abstract backdrops drawn as SVG from a kind, a hue and a seed. No image files, no licences."),
        card("Twenty-seven theme presets", P(ui.grid(*swatches_), columns=5, gap="sm"), subtitle="Wrap any part of a page in Theme. Every preset is generated in OKLCH and repaired for WCAG contrast."),
    ), subtitle="A finished look before a designer or a photographer is involved.", width="wide")


@page("/import", "Compose", "Sketch and HTML import", "upload")
def importer(ctx):
    sketch = "# Plans for every team\n[ Starter ] [ Team ] [ Enterprise ]\nEmail: ____\nSeats: ____\n( ) Monthly  ( ) Yearly\n[x] Send me product updates\n[ Start free trial ]"
    html = ('<form action="/subscribe">\n  <h2>Stay in the loop</h2>\n  <label>Name <input name="name" required></label>\n'
            '  <label>Email <input type="email" name="email" required></label>\n  <select name="topic">\n    <option>Product news</option>\n'
            '    <option>Engineering blog</option>\n  </select>\n  <button type="submit">Subscribe</button>\n</form>')
    return P(ui.page(
        "Bring what you already have",
        P(ui.split(
            card("A text wireframe", P(ui.code(sketch), language="text", title="sketch.txt"), eyebrow="Input"),
            card("Becomes a working interface", P(ui.generative("Pricing sign-up"), capability="compose.wireframe", input={"sketch": sketch}).id("gen-sketch"), eyebrow="Output"),
        ), ratio="2:3"),
        P(ui.split(
            card("Legacy HTML", P(ui.code(html), language="html", title="subscribe.html"), eyebrow="Input"),
            card("Becomes native components", P(ui.generative("Newsletter form"), capability="compose.html_import", input={"html": html}).id("gen-html"), eyebrow="Output"),
        ), ratio="2:3"),
    ), subtitle="ASCII wireframes and existing HTML are translated into scenes built from registry components.", width="wide")


@page("/states", "Compose", "Empty and loading states", "inbox")
def states(ctx):
    return P(ui.page(
        "States you usually forget",
        P(ui.grid(
            card("An empty table writes its own first step",
                 P(ui.table(), columns=[{"key": "name", "label": "Project"}, {"key": "owner", "label": "Owner"}, {"key": "due", "label": "Due"}], rows=[]).id("empty-projects")
                 .ai("compose.empty_state", {"context": "a list of projects for a design team", "actions": ["create_project", "import_projects"]})),
            card("A skeleton shaped like the content it replaces",
                 P(ui.generative("Customer profile with avatar, three stats and an activity list"), capability="compose.skeleton",
                   input={"description": "customer profile with avatar, three stats and an activity list"}).id("gen-skeleton")),
        ), columns=2),
        P(ui.grid(
            card("Loading with a story", P(ui.thinking("Importing 12,480 rows"), steps=["Reading the file", "Detecting column types", "Checking for duplicates", "Writing rows"], current=2)),
            card("Streaming text", P(ui.stream_text("The importer accepted 12,402 rows. 78 rows were skipped because the email column was empty; they are saved in the downloadable report"), streaming=True)),
            card("Progress with meaning", ui.stack(P(ui.progress(72), label="Detecting column types", tone="brand"), P(ui.progress(38), label="Matching duplicates", tone="ai"),
                                                   P(ui.progress(100), label="Uploading file", tone="success"))),
        ), columns=3),
        P(ui.grid(
            P(ui.empty_state("No invoices match this filter", P(ui.button("Clear filter"), variant="primary"), ui.button("Create invoice")), description="Try a wider date range or remove the region filter.", icon="filter"),
            ui.stack(P(ui.skeleton(), shape="card"), P(ui.skeleton(), shape="text", lines=3)),
        ), columns=2),
    ), subtitle="Empty states, skeletons and progress narration are generated from the context of the surrounding screen.", width="wide")


# ---------------------------------------------------------------- input

@page("/forms", "Input", "Intelligent forms", "edit")
def forms(ctx):
    return P(ui.page(
        "Fields that understand people",
        P(ui.split(
            card("Book a pickup",
                 ui.form("pickup",
                         P(ui.grid(
                             P(ui.input("when"), label="Pickup time", placeholder="next friday 3pm", icon="calendar").id("when").ai("input.natural_date"),
                             P(ui.input("weight"), label="Total weight", placeholder="2.5 tonnes", icon="box").id("weight").ai("input.natural_quantity", {"expect": "mass"}),
                             P(ui.input("phone"), label="Contact phone", placeholder="(415) 555 0134", kind="tel", icon="phone").id("phone").ai("input.format_heal", {"kind": "phone"}),
                             P(ui.input("email"), label="Contact email", placeholder="you@company.com", kind="email", icon="mail").id("email").ai("input.ghost").ai("input.format_heal", {"kind": "email"}),
                             P(ui.input("role"), label="Job title", placeholder="Operations Manager", icon="user").id("role")
                             .ai("input.semantic_validate", {"expectation": "job title"}),
                             P(ui.select("mode"), label="Transport mode", options=["Road", "Rail", "Air", "Sea"]).id("mode")
                             .ai("input.option_rank", {"context": "customer asked for rail freight where possible", "auto": True}),
                         ), columns=2),
                         P(ui.text_area("notes"), label="Notes for the driver", rows=3, placeholder="Gate code, loading dock, fragile items…").id("notes")
                         .ai("input.ghost").ai("input.sensitive_shield"),
                         P(ui.row(P(ui.button("Book pickup"), variant="primary", icon="truck"), ui.button("Save draft")), justify="end"),
                         ).id("pickup").on("submit", "saved"),
                 subtitle="Type the way you would say it"),
            ui.stack(
                card("What each field is doing", P(ui.list(), items=[
                    {"icon": "calendar", "title": "Natural dates", "detail": "“next friday 3pm” becomes an ISO timestamp", "tone": "ai"},
                    {"icon": "box", "title": "Natural quantities", "detail": "Units are parsed and converted to the expected dimension", "tone": "ai"},
                    {"icon": "wand", "title": "Format healing", "detail": "Typos in emails and phone numbers are repaired, not rejected", "tone": "ai"},
                    {"icon": "check", "title": "Semantic validation", "detail": "Checks meaning, not just pattern", "tone": "ai"},
                    {"icon": "list", "title": "Option ranking", "detail": "Choices are reordered for the current context", "tone": "ai"},
                    {"icon": "shield", "title": "Sensitive-data shield", "detail": "Warns before card numbers or secrets are saved", "tone": "ai"}])),
                powered_by("input.natural_date", "input.natural_quantity", "input.format_heal", "input.semantic_validate", "input.option_rank", "input.ghost", "input.sensitive_shield"),
            ),
        ), ratio="3:2"),
    ), subtitle="Inputs parse, heal and coach instead of rejecting. Everything is declared with one .ai() call per field.", width="wide")


@page("/paste", "Input", "Smart paste", "copy")
def paste(ctx):
    return P(ui.page(
        "Paste once, fill everything",
        P(ui.split(
            card("New contact",
                 ui.form("contact",
                         P(ui.grid(P(ui.input("name"), label="Full name").id("c-name"), P(ui.input("title"), label="Job title").id("c-title"),
                                   P(ui.input("company"), label="Company").id("c-company"), P(ui.input("email"), label="Email", kind="email").id("c-email"),
                                   P(ui.input("phone"), label="Phone", kind="tel").id("c-phone"), P(ui.input("city"), label="City").id("c-city"),
                                   P(ui.input("postcode"), label="Postcode").id("c-postcode"), P(ui.input("country"), label="Country").id("c-country")), columns=2),
                         P(ui.input("address"), label="Street address").id("c-address"),
                         P(ui.row(P(ui.button("Save contact"), variant="primary")), justify="end"),
                         ).id("contact").ai("input.smart_paste").on("submit", "saved"),
                 subtitle="Paste an email signature into the bar below the form"),
            ui.stack(card("Try it with this signature", P(ui.code(S.SIGNATURE), language="text", title="clipboard")),
                     P(ui.callout("Nothing is guessed silently"), tone="ai",
                       body="Each filled field is marked, the provenance chip shows what produced it, and a single undo restores the previous values."),
                     powered_by("input.smart_paste", "input.address", "input.infer_fields")),
        ), ratio="3:2"),
    ), subtitle="Unstructured text is mapped onto the fields of the form it is pasted into.", width="wide")


@page("/writing", "Input", "Writing tools", "wand")
def writing(ctx):
    draft = ("Please be advised that you must confirm your delivery address before Friday. Unable to schedule the courier without it. "
             "I am sure you will understand that we cannot hold the parcel.")
    legal = "The licensee shall indemnify the licensor against any and all liabilities arising out of or in connection with the utilisation of the software."
    return P(ui.page(
        "Writing, rewritten in place",
        P(ui.split(
            card("Reply to a customer",
                 P(ui.text_area("reply"), label="Message", rows=5, value=draft).id("reply").ai("input.tone_dial").ai("collab.cooldown"),
                 P(ui.row(P(ui.button("Send"), variant="primary", icon="send"), ui.button("Save draft")), justify="end"),
                 subtitle="Use the wand to change tone; the change is shown as a diff before you accept it"),
            ui.stack(
                card("Release notes, summarised", P(ui.text(S.RELEASE_NOTES), size="sm").id("notes-text").ai("content.summarize", {"sentences": 2})),
            ),
        ), ratio="1:1"),
        P(ui.grid(
            card("Plain language", P(ui.text(legal), size="sm").id("legal").ai("access.plain_language", {"auto": True}), eyebrow="access.plain_language"),
            card("Translation", P(ui.text("Your import has finished. 78 rows need your attention."), size="sm").id("translate-es")
                 .ai("content.translate", {"auto": True, "locale": "es-ES"}), eyebrow="content.translate · es-ES (pseudo-locale offline)"),
            card("Microcopy", P(ui.text("Error: operation failed due to invalid input parameters."), size="sm").id("microcopy")
                 .ai("content.microcopy", {"auto": True, "context": "form validation message", "voice": "friendly and specific"}), eyebrow="content.microcopy"),
        ), columns=3),
        card("A diff you can review", P(ui.diff("We was unable to process you're request at this time, please try again later.",
                                                "We could not process your request. Please try again in a few minutes."), title="Suggested rewrite", mode="inline")),
    ), subtitle="Tone, length, reading level and language are adjusted where the text lives, always with an undo.", width="wide")


# ---------------------------------------------------------------- command

ACTIONS = [
    {"label": "Create an invoice", "detail": "create_invoice · customer, amount, due date", "icon": "plus", "kbd": "C"},
    {"label": "Send a payment reminder", "detail": "send_reminder · invoice", "icon": "mail", "kbd": "R"},
    {"label": "Export the current view", "detail": "export_report · csv, xlsx or pdf", "icon": "download", "kbd": "E"},
    {"label": "Switch to dark theme", "detail": "set_theme · mode", "icon": "moon"},
    {"label": "Open the dashboard page", "detail": "open_page · page", "icon": "chart"},
]


@page("/command", "Command", "Intent bar and plans", "command")
def command(ctx):
    goal = "create an invoice for Globex Marine for $1,200 due next friday then send a reminder for INV-2041"
    plan = ask(ctx, "command.plan", {"goal": goal})
    steps = [{"title": s.get("title", ""), "tool": s.get("action"), "detail": s.get("why", ""), "status": "done" if i == 0 else "pending"}
             for i, s in enumerate(plan.get("steps") or [])]
    last = ctx.state.get("last_action")
    return P(ui.page(
        "Say what you want done",
        P(ui.split(
            ui.stack(
                card("Intent Bar", P(ui.intent_bar(), open=True, suggestions=ACTIONS, placeholder="Try “create an invoice for Globex for $300”").id("intent-demo"),
                     subtitle="Routes natural language to the actions your app registers"),
                P(ui.callout("Last action: %s" % last), tone="success", icon="check").id("last-action") if last else None,
            ),
            ui.stack(
                card("A multi-step goal becomes a reviewable plan", muted("“%s”" % goal, "md"),
                     P(ui.agent_timeline(), steps=steps, title=plan.get("summary", "Plan")).id("plan-steps"),
                     P(ui.approval("Send reminder to Globex Marine"), summary="The second step emails a customer. Outbound messages always pause for approval.",
                       risk="medium", agent="Intent planner", details=[{"key": "Invoice", "value": "INV-2041"}, {"key": "Amount", "value": "$12,400"},
                                                                         {"key": "Recipient", "value": "ap@globex-marine.example"}, {"key": "Template", "value": "Friendly reminder"}]).id("plan-approval")),
                powered_by("command.route", "command.plan", "flow.approval", "command.slash", "command.disambiguate"),
            ),
        ), ratio="1:1"),
    ), subtitle="Apps register plain functions as actions. The kernel maps utterances onto them, fills the arguments and asks before anything risky.", width="wide")


@page("/copilot", "Command", "Copilot", "message")
def copilot(ctx):
    messages = [
        {"role": "assistant", "content": "Morning, Mira. Four invoices are overdue for a total of $27,220. Globex Marine is the largest at $12,400."},
        {"role": "user", "content": "Which of them have been reminded already?"},
        {"role": "assistant", "content": "Tessellate Labs and Saffron Kitchens were reminded on 14 November. Globex Marine and Beacon Analytics have not been contacted.",
         "action": "send_reminder", "args": {"invoice": "INV-2041"}},
    ]
    return P(ui.page(
        "A copilot grounded in the screen",
        P(ui.split(
            card("Overdue receivables", P(ui.table(), columns=S.INVOICE_COLUMNS[:5], rows=[r for r in S.INVOICES if r["status"] == "Overdue"], dense=True).id("overdue")
                 .ai("data.narrate"),
                 subtitle="The copilot reads the same scene the user sees"),
            P(ui.copilot(), title="Receivables copilot", messages=messages, suggestions=["Draft reminders for the other two", "Show only EMEA", "Export as CSV"],
              placeholder="Ask about these invoices").id("copilot-demo"),
        ), ratio="3:2"),
        P(ui.grid(
            P(ui.callout("Grounded"), tone="ai", icon="eye", body="Answers cite nodes on the current screen; point at anything with Alt+click to ask about it."),
            P(ui.callout("Actionable"), tone="ai", icon="bolt", body="Replies can propose a registered action. It runs only after the user presses the chip."),
            P(ui.callout("Accountable"), tone="ai", icon="shield", body="Every reply carries provenance: provider, model, latency and a trace id."),
        ), columns=3),
    ), subtitle="The Copilot component needs no wiring: it sees the scene, knows the registered actions and keeps a provenance trail.", width="wide")


# ---------------------------------------------------------------- data

@page("/data", "Data", "Ask your data", "database")
def data(ctx):
    types = ask(ctx, "data.column_types", {"rows": S.INVOICES}).get("columns") or []
    choice = ask(ctx, "data.chart_choose", {"data": S.REGIONS, "question": "compare new and expansion customers by region"})
    formula = ask(ctx, "data.formula", {"description": "amount plus 20% tax", "columns": ["amount"], "rows": S.INVOICES[:3]})
    return P(ui.page(
        "Ask your data",
        P(ui.split(
            card("Receivables", P(ui.table(), columns=S.INVOICE_COLUMNS, rows=S.INVOICES, pageSize=7).id("data-table").ai("data.query").ai("data.pivot"),
                 subtitle="“overdue over 5000, largest first” is a valid filter"),
            ui.stack(
                card("Detected column types", P(ui.table(), dense=True, sortable=False, rows=[{"column": t.get("label"), "type": t.get("type"), "format": t.get("format")} for t in types],
                                               columns=[{"key": "column", "label": "Column"}, {"key": "type", "label": "Type", "format": "text"}, {"key": "format", "label": "Rendered as", "format": "text"}]),
                     eyebrow="data.column_types"),
            ),
        ), ratio="2:1"),
        P(ui.grid(
            card("The right chart, chosen for the question",
                 P(ui.chart(choice.get("kind", "bar")), data=S.REGIONS, x=choice.get("x", "region"), y=choice.get("y") or ["new", "expansion"], height=220, legend=True),
                 muted(choice.get("rationale", "")), P(ui.confidence(choice.get("confidence", 0.8)), variant="bar"), eyebrow="data.chart_choose"),
            card("A formula from a sentence",
                 kv([("You typed", "amount plus 20% tax"), ("Expression", formula.get("expression", "")), ("Preview", ", ".join(format(v, ",.0f") for v in formula.get("preview") or [])),
                     ("Explanation", formula.get("explanation", ""))]), eyebrow="data.formula"),
            card("Entities in free text",
                 P(ui.text("Globex Marine paid $12,400 on 14 November 2026 after Jonas Weber called their Rotterdam office."), size="sm").id("entity-text").ai("data.entities"),
                 eyebrow="data.entities"),
        ), columns=3),
    ), subtitle="Plain-language filters, automatic column typing, chart selection and formulas, all computed by the kernel.", width="wide")


@page("/charts", "Data", "Charts", "trend-up")
def charts(ctx):
    return P(ui.page(
        "Charts that explain themselves",
        P(ui.grid(
            card("Revenue with forecast", P(ui.chart("line"), data=S.REVENUE, x="month", y="revenue", height=230).id("c-line").ai("data.forecast", {"horizon": 3}),
                 eyebrow="Line · data.forecast"),
            card("Customers by region", P(ui.chart("bar"), data=S.REGIONS, x="region", y=["new", "expansion"], stacked=True, legend=True, height=230).id("c-bar"),
                 eyebrow="Stacked bar"),
            card("Revenue by channel", P(ui.chart("donut"), data=S.CHANNELS, x="channel", y="share", legend=True, height=230, format="percent").id("c-donut"),
                 eyebrow="Donut"),
            card("Refunds per month", P(ui.chart("bar"), data=S.REVENUE, x="month", y="refunds", height=230).id("c-refunds").ai("data.anomaly"),
                 eyebrow="Bar · data.anomaly"),
            card("Latency against payload size", P(ui.chart("scatter"), data=S.LATENCY, x="payload", y="latency", height=230).id("c-scatter").ai("access.describe_chart"),
                 eyebrow="Scatter · access.describe_chart"),
            card("Orders over the year", P(ui.chart("area"), data=S.REVENUE, x="month", y="orders", height=230).id("c-area").ai("data.insights"),
                 eyebrow="Area · data.insights"),
        ), columns=3),
    ), subtitle="Forecast bands, anomaly markers, written descriptions and insights are attached to a chart with one line each.", width="wide")


@page("/story", "Data", "Data stories", "file")
def story(ctx):
    return P(ui.page(
        "From rows to a narrative",
        P(ui.generative("2026 revenue, told as a story"), capability="data.story", input={"rows": S.REVENUE, "title": "2026 revenue"}).id("gen-story"),
        P(ui.generative("Key metrics for this data set"), capability="data.kpi", input={"rows": S.REVENUE}).id("gen-kpi"),
    ), subtitle="The engine computes the facts, the kernel arranges them into a report with headline numbers, a chart and commentary.", width="wide")


# ---------------------------------------------------------------- design

THEME_PROMPTS = ["Calm fintech at night", "Sunny citrus market", "Forest trail at dawn"]


def theme_card(ctx, prompt):
    theme = ask(ctx, "design.theme_prompt", {"prompt": prompt})
    tokens = {t["name"]: t["value"] for t in theme.get("tokens") or []}
    strip = [tokens[k] for k in ("--fl-bg", "--fl-surface", "--fl-surface-2", "--fl-border", "--fl-text-3", "--fl-text-2", "--fl-text", "--fl-brand", "--fl-accent")
             if str(tokens.get(k, "")).startswith("#")]
    return card(theme.get("name", prompt), swatches(strip or [theme.get("brand", "#2a6df4"), theme.get("accent", "#7a5af8")]),
                kv([("Brand", theme.get("brand", "")), ("Accent", theme.get("accent", "")), ("Scheme", "Dark" if theme.get("dark") else "Light"),
                    ("Radius", "%s px" % theme.get("radius", "")), ("Density", theme.get("density", "")), ("Typeface", theme.get("font", ""))], 2),
                muted(theme.get("rationale", "")), eyebrow="“%s”" % prompt)


@page("/theme", "Design", "Theme studio", "palette")
def theme(ctx):
    palette = ask(ctx, "design.palette", {"seed": "#2a6df4"})
    healed = ask(ctx, "design.contrast_heal", {"pairs": [
        {"name": "Muted text on white", "fg": "#9db8ff", "bg": "#ffffff"}, {"name": "Placeholder on field", "fg": "#b8bcc4", "bg": "#f6f7f9"},
        {"name": "Link on tinted panel", "fg": "#5aa2ff", "bg": "#eaf2ff"}, {"name": "Body text on white", "fg": "#1c2330", "bg": "#ffffff"}]}).get("pairs") or []
    types = [ask(ctx, "design.type_pair", {"mood": m}) for m in ("editorial and authoritative", "friendly product", "technical and precise")]
    return P(ui.page(
        "Theme studio",
        P(ui.grid(*[theme_card(ctx, p) for p in THEME_PROMPTS]), columns=3),
        P(ui.split(
            card("A full ramp from one seed colour", swatches([s["value"] for s in palette.get("ramp") or []]),
                 kv([("Seed", "#2a6df4"), ("Complementary", palette.get("complementary", "")), ("Analogous", ", ".join(palette.get("analogous") or [])),
                     ("Triadic", ", ".join(palette.get("triadic") or [])), ("Neutral", palette.get("neutral", ""))], 2), eyebrow="design.palette · OKLCH"),
            card("Contrast, repaired automatically",
                 P(ui.table(), dense=True, sortable=False, rows=[{"pair": h["name"], "before": "%.2f : 1" % h["ratio"], "result": "Pass" if h["passes"] else "Fixed",
                                                                  "colour": h.get("fixed") or h["fg"], "after": "%.2f : 1" % (h.get("fixedRatio") or h["ratio"])} for h in healed],
                   columns=[{"key": "pair", "label": "Pair"}, {"key": "before", "label": "Before"}, {"key": "result", "label": "WCAG AA"},
                            {"key": "colour", "label": "Foreground"}, {"key": "after", "label": "After"}]), eyebrow="design.contrast_heal"),
        ), ratio="1:1"),
        card("Type pairings by mood", P(ui.table(), dense=True, sortable=False,
                                        rows=[{"mood": t.get("mood", ""), "heading": str(t.get("heading", "")).split(",")[0].strip("' "), "body": str(t.get("body", "")).split(",")[0].strip("' "),
                                               "scale": t.get("scale", ""), "why": t.get("why", "")} for t in types],
                                        columns=[{"key": "mood", "label": "Mood", "format": "text"}, {"key": "heading", "label": "Headings"}, {"key": "body", "label": "Body"},
                                                 {"key": "scale", "label": "Scale"}, {"key": "why", "label": "Rationale"}]), eyebrow="design.type_pair"),
    ), subtitle="Themes are generated as design tokens in the OKLCH colour space, then checked and repaired for contrast before they reach the screen.", width="wide")


@page("/restyle", "Design", "Restyle live", "droplet")
def restyle(ctx):
    prompt = ctx.state.get("theme_prompt", THEME_PROMPTS[0])
    slug = "".join(ch if ch.isalnum() else "-" for ch in prompt.lower())
    return P(ui.page(
        "One sentence restyles the whole product",
        P(ui.toolbar(
            P(ui.segmented("prompt"), options=THEME_PROMPTS, value=prompt).id("theme-choice").on("change", "set_theme_prompt"),
            P(ui.button("Reset to default"), variant="ghost", icon="refresh", href="/restyle"),
        )),
        muted("Applied theme: “%s”" % prompt).id("theme-" + slug).ai("design.theme_prompt", {"prompt": prompt}),
        P(ui.grid(
            P(ui.stat("Active customers", "4,812"), delta="+6.2%", spark=[31, 33, 34, 38, 41, 40, 44, 48], icon="users"),
            P(ui.stat("Net revenue retention", "118%"), delta="+3 pts", icon="trend-up"),
            P(ui.stat("Open tickets", "37"), delta="-12", icon="inbox"),
        ), columns=3),
        P(ui.split(
            card("Orders", P(ui.chart("area"), data=S.REVENUE, x="month", y="orders", height=240)),
            card("Invite a teammate",
                 P(ui.input("invite"), label="Work email", placeholder="name@company.com", icon="mail"),
                 P(ui.select("role"), label="Role", options=["Admin", "Editor", "Viewer"], value="Editor"),
                 P(ui.toggle("digest", "Send a weekly digest"), checked=True),
                 P(ui.row(P(ui.badge("Beta"), tone="brand"), P(ui.badge("Synced"), tone="success", dot=True), P(ui.badge("2 pending"), tone="warning")), gap="xs"),
                 P(ui.row(P(ui.button("Send invite"), variant="primary", icon="send"), ui.button("Copy link")), justify="end")),
        ), ratio="3:2"),
    ), subtitle="design.theme_prompt returns a complete token set. The runtime applies it without a reload, and contrast is healed before it lands.", width="wide")


# ---------------------------------------------------------------- experience

@page("/access", "Experience", "Accessibility", "eye")
def access(ctx):
    audit = ask(ctx, "access.audit", {"scene": S.FLAWED_SCENE})
    findings = audit.get("findings") or []
    tone = {"error": "danger", "warning": "warning", "info": "info"}
    return P(ui.page(
        "Accessibility, audited and repaired",
        P(ui.split(
            card("Screen under review",
                 P(ui.image(ask(ctx, "design.illustrate", {"prompt": "abstract checkout banner", "width": 640, "height": 150}).get("url", "")), ratio="64:15"),
                 P(ui.input("f1"), placeholder="Email"), P(ui.input("f2"), placeholder="Card number"),
                 muted("By proceeding you acknowledge the aforementioned stipulations.", "xs"),
                 P(ui.row(P(ui.button("Click here"), variant="primary"), P(ui.button("Click here"), variant="primary"), P(ui.button(""), icon="trash")), gap="sm"),
                 subtitle="A checkout form with the usual problems"),
            card("Audit report",
                 P(ui.row(P(ui.stat("Score", "%s / 100" % audit.get("score", "–")), tone="warning", icon="shield"),
                          P(ui.stat("Findings", str(len(findings))), icon="alert", hint="each with a suggested fix")), gap="md"),
                 P(ui.list(), items=[{"icon": "alert" if f.get("severity") != "info" else "info", "tone": tone.get(f.get("severity"), "warning"), "title": f.get("title", ""),
                                      "detail": " ".join(x for x in (f.get("detail"), f.get("fix")) if x), "badge": f.get("severity")} for f in findings[:7]]),
                 subtitle=audit.get("summary", ""), eyebrow="access.audit"),
        ), ratio="2:3"),
        P(ui.grid(
            card("Charts get a written description", P(ui.chart("line"), data=S.REVENUE[:8], x="month", y="orders", height=150).id("a11y-chart").ai("access.describe_chart"), eyebrow="access.describe_chart"),
            card("Dense text gets a plain version", P(ui.text("Prior to utilising the service, users are required to authenticate and verify that sufficient funds are available."), size="sm").id("a11y-plain")
                 .ai("access.plain_language", {"auto": True}), eyebrow="access.plain_language"),
            card("Reading order, linearised", P(ui.steps(), orientation="vertical", current=4, items=[{"title": "Page title", "detail": "Checkout"}, {"title": "Form fields", "detail": "Email, then card number"},
                                                                                                      {"title": "Legal notice"}, {"title": "Primary action", "detail": "Pay now"}]), eyebrow="access.focus_order"),
        ), columns=3),
    ), subtitle="The audit runs on the scene itself, so every finding points at a node and carries a fix the kernel can apply.", width="wide")


@page("/adaptive", "Experience", "Adaptive interface", "users")
def adaptive(ctx):
    locale = ask(ctx, "adapt.locale_morph", {"locale": "de-DE"})
    events = [{"t": t, "kind": kind, "target": target} for t, kind, target in [
        (0, "click", "save"), (180, "click", "save"), (340, "click", "save"), (520, "click", "save"), (2400, "error", "amount"), (5200, "error", "amount"),
        (7800, "nav", "/invoices"), (9100, "nav", "/settings"), (10300, "nav", "/invoices"), (11800, "click", "save"), (11950, "click", "save"), (12100, "click", "save")]]
    ask(ctx, "trust.consent", {"scope": "personalization", "grant": True})
    load = ask(ctx, "adapt.frustration", {"events": events})
    text = "Prior to commencing the reconciliation, ensure that you have obtained sufficient documentation and verify the ledger balance."
    words = lambda name: "".join(" " + ch.lower() if ch.isupper() else ch for ch in str(name)).replace("_", " ").strip().capitalize()
    notes = locale.get("notes") or ""
    return P(ui.page(
        "An interface that adapts to the person",
        P(ui.grid(
            card("While you were away", muted("Back after 3 hours 10 minutes.").id("resume").ai("adapt.resume", {"awayMinutes": 190, "changes": [
                "INV-2049 from Juniper Health was paid", "Two invoices became overdue", "Kenji assigned you the APAC review", "The importer build passed QA"]}), eyebrow="adapt.resume"),
            card("Right now", muted("Quarter close is 6 working days away.").id("now").ai("adapt.time_context", {"name": "Mira", "items": [
                "Approve payroll run by 17:00", "Quarter close checklist: 7 of 12 done", "Team stand-up moved to 09:30 tomorrow"]}), eyebrow="adapt.time_context"),
            card("Signals, not surveillance", kv([("Detected state", str(load.get("state", "")).title()), ("Confidence", "%d%%" % round(100 * float(load.get("confidence") or 0))),
                                                  ("Signals used", "Rapid repeat clicks, validation errors, back-and-forth navigation")]),
                 P(ui.list(), dense=True, items=[{"icon": "sparkles", "tone": "ai", "title": words(d.get("kind", "")), "detail": d.get("reason") or d.get("value") or ""}
                                                 for d in (load.get("directives") or [])[:3]]) if load.get("directives") else None, eyebrow="adapt.frustration"),
        ), columns=3),
        P(ui.split(
            card("The same explanation at two reading levels",
                 P(ui.grid(ui.stack(P(ui.badge("Original"), variant="outline"), P(ui.text(text), size="sm")),
                           ui.stack(P(ui.badge("Grade 6"), tone="ai"), P(ui.text(text), size="sm").id("level-6").ai("adapt.reading_level", {"auto": True, "grade": 6}))), columns=2),
                 eyebrow="adapt.reading_level"),
            card("Locale-aware fields", kv([(words(f.get("name", "")), str(f.get("value", ""))) for f in (locale.get("fields") or [])[:6]], 2),
                 muted(notes if isinstance(notes, str) else " ".join(notes)), eyebrow="adapt.locale_morph · de-DE"),
        ), ratio="3:2"),
    ), subtitle="Expertise, pace, locale and context change what is shown. Behavioural signals are summarised in the browser before anything is sent.", width="wide")


@page("/content", "Experience", "Content and guidance", "message")
def content(ctx):
    return P(ui.page(
        "Content that writes and explains itself",
        P(ui.split(
            card("Frequently asked questions, from the release notes",
                 P(ui.generative("FAQ for the importer release"), capability="content.faq", input={"text": S.RELEASE_NOTES}).id("gen-faq")),
            ui.stack(
                card("What changed between two versions of a screen", muted("Billing settings, last week against today").id("whats-new").ai("content.whats_new", {
                    "before": {"type": "Page", "props": {"title": "Billing"}, "children": [
                        {"type": "Stat", "id": "seats", "props": {"label": "Seats", "value": "10"}}, {"type": "Stat", "id": "storage", "props": {"label": "Storage", "value": "5 GB"}},
                        {"type": "Button", "id": "upgrade", "props": {"label": "Upgrade"}}]},
                    "after": {"type": "Page", "props": {"title": "Billing"}, "children": [
                        {"type": "Stat", "id": "seats", "props": {"label": "Seats", "value": "25"}}, {"type": "Stat", "id": "storage", "props": {"label": "Storage", "value": "50 GB"}},
                        {"type": "Toggle", "id": "yearly", "props": {"name": "yearly", "label": "Bill yearly"}}, {"type": "Table", "id": "audit", "props": {"caption": "Audit log", "rows": []}},
                        {"type": "Button", "id": "upgrade", "props": {"label": "Change plan"}}]}}), eyebrow="content.whats_new"),
                card("A consent notice people can read", P(ui.text("We process your usage data to improve the product and may share aggregated statistics with partners. "
                                                                   "You can withdraw consent at any time in settings."), size="sm").id("consent").ai("content.consent"), eyebrow="content.consent"),
            ),
        ), ratio="1:1"),
        P(ui.grid(
            card("Icon suggestions", P(ui.text("Export the report as a spreadsheet"), size="sm").id("icon-text").ai("design.icon_match"), eyebrow="design.icon_match"),
            card("Emoji that fit the message", P(ui.text("The launch went great, thank you all!"), size="sm").id("emoji-text").ai("content.emoji"), eyebrow="content.emoji"),
            card("Truncation that keeps the meaning", P(ui.text("Quarterly Revenue Report for the International Sales Department (draft)"), size="sm")
                 .id("truncate").ai("content.truncate", {"auto": True, "max": 42}), eyebrow="content.truncate · 42 characters"),
        ), columns=3),
    ), subtitle="FAQs, change summaries, consent notices and tours are derived from the content already in your product.", width="wide")


@page("/collab", "Experience", "Collaboration", "users")
def collab(ctx):
    decisions = ask(ctx, "collab.decisions", {"messages": S.THREAD}).get("decisions") or []
    joined = " ".join(m["content"] for m in S.THREAD)
    return P(ui.page(
        "Collaboration with a memory",
        P(ui.split(
            card("Importer release", P(ui.thread(), messages=S.THREAD).id("thread").ai("collab.thread_summary").ai("collab.reply", {"message": S.THREAD[-1]["content"]}),
                 subtitle="#launch-importer · 5 messages"),
            ui.stack(
                card("Decisions extracted", P(ui.list(), items=[{"icon": "flag", "tone": "ai", "title": d.get("decision", ""), "meta": d.get("owner") or "", "detail": ("Due " + d["due"]) if d.get("due") else None}
                                                                for d in decisions]), eyebrow="collab.decisions"),
                card("Before you send that", P(ui.text_area("heated"), rows=2, value="This is the THIRD time the build is late. Totally unacceptable!!").id("heated").ai("collab.cooldown"),
                     eyebrow="collab.cooldown"),
            ),
        ), ratio="1:1"),
        card("A recap for someone who missed it", P(ui.generative("Recap of the importer thread"), capability="collab.recap", input={"text": joined}).id("gen-recap"), eyebrow="collab.recap"),
    ), subtitle="Threads are summarised, decisions and owners are pulled out, and replies are drafted in context.", width="wide")


@page("/flow", "Experience", "Workflows and approvals", "branch")
def flow(ctx):
    rule = ask(ctx, "flow.rules", {"text": "when an invoice is overdue by 7 days, send a reminder to the customer"})
    ops = {"gte": "≥", "gt": ">", "lte": "≤", "lt": "<", "eq": "=", "contains": "contains"}
    conditions = ["%s %s %s" % (str(c.get("field", "")).replace("_", " "), ops.get(c.get("op"), c.get("op")), c.get("value")) for c in rule.get("conditions") or [] if isinstance(c, dict)]
    return P(ui.page(
        "Workflows with a human in the loop",
        P(ui.steps(), current=2, items=[{"title": "Goal", "detail": "Close the quarter"}, {"title": "Plan", "detail": "6 steps"}, {"title": "Approve", "detail": "2 need sign-off"},
                                        {"title": "Run", "detail": "Agent executes"}, {"title": "Report", "detail": "Audit trail"}]),
        P(ui.split(
            ui.stack(
                P(ui.approval("Issue refund of $1,320 to Saffron Kitchens"), risk="high", agent="Billing agent", summary="Refunds above $1,000 require a second approver. The customer reported a duplicate charge on 12 November.",
                  details=[{"key": "Invoice", "value": "INV-2051"}, {"key": "Method", "value": "Original card"}, {"key": "Policy", "value": "Refunds over $1,000"}, {"key": "Evidence", "value": "Two identical charges"}]).id("refund"),
                card("A rule written as a sentence", kv([("Sentence", "When an invoice is overdue by 7 days, send a reminder to the customer"), ("Trigger", str(rule.get("trigger", ""))),
                                                          ("Conditions", "; ".join(conditions) or "—"),
                                                          ("Action", str(rule.get("action", ""))), ("Confidence", "%d%%" % round(100 * float(rule.get("confidence") or 0)))]), eyebrow="flow.rules"),
            ),
            card("Quarter close, run by an agent", P(ui.agent_timeline(), title="6 steps · 2 awaiting approval", steps=[
                {"title": "Reconcile bank statement", "tool": "ledger.reconcile", "status": "done", "duration": "4.1 s", "detail": "1,284 entries matched, 3 flagged"},
                {"title": "Chase overdue invoices", "tool": "send_reminder", "status": "done", "duration": "1.2 s", "detail": "4 reminders drafted"},
                {"title": "Issue refund to Saffron Kitchens", "tool": "billing.refund", "status": "running", "detail": "Waiting for approval"},
                {"title": "Post accruals", "tool": "ledger.post", "status": "pending"},
                {"title": "Generate the board report", "tool": "export_report", "status": "pending"},
                {"title": "Archive the period", "tool": "ledger.lock", "status": "pending", "detail": "Irreversible — always asks first"}]).id("agent")
                 .ai("flow.timeline"), subtitle="Every tool call is visible, timed and reversible where possible"),
        ), ratio="1:1"),
    ), subtitle="Goals are decomposed into steps, risky steps pause for approval, and the whole run leaves an audit trail.", width="wide")


# ---------------------------------------------------------------- trust

@page("/trust", "Trust", "Trust and safety", "shield")
def trust(ctx):
    redacted = ask(ctx, "trust.redact", {"text": S.CUSTOMER_NOTE})
    shield = ask(ctx, "trust.injection_shield", {"text": S.UNTRUSTED_REVIEW})
    why = ask(ctx, "trust.explain", {"decision": "Flagged INV-2048 for review", "evidence": [
        "The amount is 4.2 times this customer's average", "The delivery address was changed the same day", "First order above $10,000 from this account"]})
    grounded = ask(ctx, "trust.grounding", {"actions": ["list_orders"], "scene": {"type": "Page", "props": {"title": "Orders"}, "children": [
        {"type": "Button", "id": "new", "props": {"label": "New order", "colour": "red"}, "on": {"click": "create_order"}},
        {"type": "Sparkline3D", "id": "fancy", "props": {"values": [1, 2, 3]}}, {"type": "Table", "id": "orders", "props": {"rows": []}, "on": {"rowClick": "list_orders"}}]}})
    budget = ask(ctx, "trust.budget", {})
    session = budget.get("session") or {}
    return P(ui.page(
        "Trust is part of the pipeline",
        P(ui.split(
            card("Personal data never leaves in the clear",
                 P(ui.diff(S.CUSTOMER_NOTE, redacted.get("text", "")), mode="split", title="What you wrote · what the model receives"),
                 P(ui.row(*[P(ui.tag("%s → %s" % (f.get("kind", ""), f.get("placeholder", ""))), tone="ai") for f in redacted.get("findings") or []]), gap="xs"),
                 muted("Placeholders are reversible: the response is restored before it is shown, so people still see real values."), eyebrow="trust.redact"),
            card("Prompt-injection shield",
                 P(ui.row(P(ui.stat("Injection risk", "%d%%" % round(100 * float(shield.get("risk") or 0))), tone="danger", icon="alert"),
                          P(ui.stat("Verdict", str(shield.get("verdict", "")).capitalize()), icon="shield")), gap="md"),
                 P(ui.list(), dense=True, items=[{"icon": "flag", "tone": "danger", "title": str(p).capitalize()} for p in shield.get("patterns") or []]),
                 P(ui.code(str(shield.get("wrapped", ""))[:260]), language="text", title="Untrusted content is fenced before it reaches the model"), eyebrow="trust.injection_shield"),
        ), ratio="1:1"),
        P(ui.grid(
            card("Provenance on every result",
                 P(ui.provenance(), provider="openai", model="balanced tier", confidence=0.92, generatedAt="Today 16:42", note="trace 7f3a9c"),
                 P(ui.row(P(ui.provenance(), compact=True, provider="reflex"), P(ui.provenance(), compact=True, provider="cache"),
                          P(ui.provenance(), compact=True, provider="openai", model="fast tier", confidence=0.81)), gap="xs"), eyebrow="trust.provenance"),
            card("Confidence, shown honestly", ui.stack(P(ui.confidence(0.93), variant="bar"), P(ui.confidence(0.64), variant="dots"), P(ui.confidence(0.31), variant="ring")),
                 eyebrow="trust.confidence"),
            P(ui.insight(why.get("title", "Why")), body=why.get("body", ""), bullets=why.get("bullets") or [], confidence=why.get("confidence"), tone="info", source="trust.explain"),
        ), columns=3),
        P(ui.grid(
            card("Generated UI is grounded in the registry",
                 P(ui.list(), dense=True, items=[{"icon": "wand", "tone": "warning", "title": fix} for fix in (grounded.get("fixes") or [])[:5]]),
                 muted("Unknown components, props and actions are removed before a scene is rendered."), eyebrow="trust.grounding"),
            card("Budgets that degrade gracefully",
                 P(ui.progress(session.get("used", 0)), max=max(1, session.get("limit", 1)), label="Session token budget", tone="ai"),
                 kv([("Session limit", format(session.get("limit", 0), ",") + " tokens"), ("Used", format(session.get("used", 0), ",")),
                     ("When exhausted", "Capabilities fall back to Reflex instead of failing"), ("Degraded now", "Yes" if budget.get("degraded") else "No")], 2), eyebrow="trust.budget"),
        ), columns=2),
    ), subtitle="Redaction, injection defence, moderation, grounding, provenance and budgets run on every call, for every SDK, with no extra code.", width="wide")


PIPELINE = [
    ("Policy", "Is this capability allowed for this app and user?"), ("Consent", "Has the user agreed to this kind of processing?"),
    ("Validate input", "Payload is checked against the capability's schema"), ("Redact", "Personal data is replaced with reversible placeholders"),
    ("Shield", "Untrusted text is scored and fenced"), ("Moderate", "Content policy check, cached per text"),
    ("Cache", "Exact match first, then semantic similarity"), ("Coalesce", "Identical in-flight requests share one call"),
    ("Budget", "Session and global token ceilings"), ("Route", "Pick the tier and model, with a fallback chain"),
    ("Reason or Reflex", "Model with strict structured output, or the local heuristic"), ("Validate output", "Schema check, then one self-repair attempt"),
    ("Ground", "Scenes are checked against the component registry"), ("Restore", "Placeholders are swapped back"),
    ("Record", "Provenance, telemetry and the audit ledger"),
]


@page("/kernel", "Trust", "Inside the kernel", "cpu")
def kernel(ctx):
    router = ask(ctx, "perf.router", {})
    try:
        telemetry = ctx.ai("perf.telemetry", {})
    except AIError:
        telemetry = {}
    totals = telemetry.get("totals") or {}
    half = (len(PIPELINE) + 1) // 2
    line = lambda rows, offset: P(ui.timeline(), items=[{"title": "%d · %s" % (offset + i + 1, t), "detail": d, "tone": "ai" if t in ("Reason or Reflex", "Cache") else "brand"} for i, (t, d) in enumerate(rows)])
    return P(ui.page(
        "Inside the AI kernel",
        P(ui.grid(
            P(ui.stat("Calls this session", str(totals.get("calls", 0))), icon="bolt"),
            P(ui.stat("Answered by Reflex", str(totals.get("reflex", 0))), icon="cpu", hint="no network, no tokens"),
            P(ui.stat("Cache hits", str(totals.get("cacheHits", 0))), icon="database"),
            P(ui.stat("Errors", str(totals.get("errors", 0))), icon="alert", tone="success" if not totals.get("errors") else "danger"),
        ), columns=4),
        P(ui.split(
            card("Every call takes the same fifteen steps", P(ui.grid(line(PIPELINE[:half], 0), line(PIPELINE[half:], half)), columns=2)),
            ui.stack(
                card("Model routing", P(ui.table(), dense=True, sortable=False, rows=[{"tier": t.get("tier"), "model": t.get("model"), "fallbacks": len(t.get("chain") or []) - 1} for t in (router.get("tiers") or [])[:6]],
                                        columns=[{"key": "tier", "label": "Tier", "format": "text"}, {"key": "model", "label": "Preferred model", "format": "text"}, {"key": "fallbacks", "label": "Fallbacks"}]),
                     subtitle="Live mode" if router.get("live") else "Offline mode · Reflex answers every call", eyebrow="perf.router"),
                card("Busiest capabilities", P(ui.table(), dense=True, sortable=False, rows=sorted(telemetry.get("capabilities") or [], key=lambda r: -r.get("calls", 0))[:6],
                                               columns=[{"key": "id", "label": "Capability"}, {"key": "calls", "label": "Calls"}, {"key": "p50", "label": "p50 ms"}, {"key": "p95", "label": "p95 ms"},
                                                        {"key": "cacheHits", "label": "Cached"}]), eyebrow="perf.telemetry"),
            ),
        ), ratio="1:1"),
    ), subtitle="One pipeline serves every capability and every SDK. Press Ctrl+. on any page to open the trace panel.", width="wide")


# ---------------------------------------------------------------- build

@page("/dev", "Build", "Developer tools", "terminal")
def dev(ctx):
    review = ask(ctx, "dev.ux_review", {"scene": S.FLAWED_SCENE})
    scaffold = ask(ctx, "dev.scaffold", {"description": "contact form with name, email and message", "language": "go"})
    form = {"type": "Page", "props": {"title": "Contact"}, "children": [{"type": "Form", "id": "contact", "props": {"name": "contact"}, "on": {"submit": "send"}, "children": [
        {"type": "Input", "id": "email", "props": {"name": "email", "label": "Email", "kind": "email"}}, {"type": "TextArea", "id": "message", "props": {"name": "message", "label": "Message"}},
        {"type": "Button", "id": "send", "props": {"label": "Send", "variant": "primary"}}]}]}
    cases = ask(ctx, "dev.test_synth", {"scene": form}).get("cases") or []
    trace = 'Traceback (most recent call last):\n  File "app.py", line 42, in submit\n    total = sum(row["amount"] for row in rows)\nTypeError: unsupported operand type(s) for +: \'int\' and \'str\''
    tone = {"error": "danger", "warning": "warning", "info": "info"}
    return P(ui.page(
        "Tools for the people building the interface",
        P(ui.split(
            card("Describe an app, get runnable code", muted("“contact form with name, email and message” · Go", "md"),
                 P(ui.code(scaffold.get("code", "")), language=scaffold.get("language", "go"), title=scaffold.get("run", "")), eyebrow="dev.scaffold · 14 target languages"),
            ui.stack(
                card("UX review of a scene",
                     P(ui.list(), dense=True, items=[{"icon": "alert", "tone": tone.get(f.get("severity"), "warning"), "title": f.get("title", ""), "detail": f.get("fix") or f.get("detail"),
                                                      "badge": f.get("severity")} for f in (review.get("findings") or [])[:5]]),
                     subtitle="%s · score %s" % (review.get("summary", ""), review.get("score", "–")), eyebrow="dev.ux_review"),
                card("Tests synthesised from the scene",
                     P(ui.list(), dense=True, items=[{"icon": "check", "tone": "success", "title": case.get("name", ""),
                                                      "detail": " → ".join("%s %s" % (s.get("do", ""), s.get("target", "")) for s in case.get("steps") or [])} for case in cases[:4]]),
                     eyebrow="dev.test_synth"),
            ),
        ), ratio="1:1"),
        card("Errors, explained where they happen", P(ui.code(trace), language="python", title="stderr").id("trace").ai("dev.error_explain", {"error": trace, "language": "python"}),
             eyebrow="dev.error_explain"),
    ), subtitle="Scaffolding, porting between languages, scene linting, UX review and test synthesis are capabilities like any other.", width="wide")


@page("/multimodal", "Build", "Voice, vision and sound", "mic")
def multimodal(ctx):
    art = [(p, ask(ctx, "design.illustrate", {"prompt": p, "width": 640, "height": 360})) for p in ("calm ocean waves at dusk", "mountain range at sunrise", "city skyline in the rain")]
    return P(ui.page(
        "Beyond the keyboard",
        P(ui.grid(*[P(ui.image(a.get("url", "")), alt=a.get("alt", p), ratio="16:9", caption="“%s”" % p) for p, a in art]), columns=3),
        P(ui.split(
            card("Dictate and listen",
                 P(ui.text_area("memo"), label="Voice memo", rows=3, value="Remind Jonas to send the Globex reminder before noon and move the QA review to Thursday.").id("memo").ai("modal.speak"),
                 P(ui.row(P(ui.mic("dictation"), target="memo", label="Dictate"), muted("Speech is transcribed and inserted at the cursor.")), gap="sm"),
                 muted("Actions heard in this memo").id("memo-actions").ai("content.summarize", {"text": "Remind Jonas to send the Globex reminder before noon. Move the QA review to Thursday.", "sentences": 2}),
                 eyebrow="modal.dictate · modal.speak"),
            card("A receipt becomes a filled form",
                 ui.form("expense",
                         P(ui.file_drop("receipt"), label="Drop a receipt or invoice", accept="image/*,.pdf", hint="Images are read by a vision model in live mode").id("receipt"),
                         P(ui.grid(P(ui.input("merchant"), label="Merchant", value="Harbour Coffee Roasters"), P(ui.input("total"), label="Total", value="$18.40"),
                                   P(ui.input("date"), label="Date", value="2026-11-18"), P(ui.select("category"), label="Category", options=["Meals", "Travel", "Software"], value="Meals")), columns=2),
                         ).id("expense").ai("modal.vision_form"),
                 eyebrow="modal.vision_form"),
        ), ratio="1:1"),
        card("Hear the shape of the data", P(ui.chart("line"), data=S.REVENUE, x="month", y="revenue", height=170).id("sonify").ai("modal.sonify"), eyebrow="modal.sonify · press play on the chart"),
    ), subtitle="Illustrations are procedural offline and generated in live mode. Dictation, read-aloud, vision and sonification use the same attachment model.", width="wide")


SDKS = [
    ("Python", "fluidian", "python3 app.py"), ("JavaScript", "fluidian", "node app.js"), ("TypeScript", "fluidian", "node dist/app.js"), ("Go", "github.com/fluidian/fluidian/sdks/go", "go run ."),
    ("Rust", "fluidian", "cargo run --quiet"), ("Java", "dev.fluidian:fluidian", "java -cp out Main"), ("Kotlin", "dev.fluidian:fluidian", "java -jar app.jar"), ("C#", "Fluidian", "dotnet run"),
    ("C++", "fluidian/fluidian.hpp", "./app"), ("Ruby", "fluidian", "ruby app.rb"), ("PHP", "fluidian/fluidian", "php app.php"), ("Dart", "fluidian", "dart run app.dart"),
    ("Elixir", ":fluidian", "elixir app.exs"), ("Lua", "fluidian", "lua app.lua"),
]


@page("/languages", "Build", "Fourteen languages", "code")
def languages(ctx):
    tabs = [ui.tab(name, P(ui.code(src), language=lang, title="counter.%s" % {"python": "py", "typescript": "ts", "rust": "rs", "go": "go", "cpp": "cpp", "kotlin": "kt", "elixir": "exs"}[lang]))
            for name, (lang, src) in S.COUNTER.items()]
    return P(ui.page(
        "One protocol, fourteen languages",
        P(ui.split(
            card("The same app in the language you already use", P(ui.tabs(*tabs), variant="pill", active=2).id("lang-tabs")),
            card("Every SDK passes the same conformance transcript",
                 P(ui.table(), dense=True, sortable=False, rows=[{"language": n, "package": p, "run": r} for n, p, r in SDKS],
                   columns=[{"key": "language", "label": "Language"}, {"key": "package", "label": "Package", "format": "text"}, {"key": "run", "label": "fluidian run -- …", "format": "text"}])),
        ), ratio="1:1"),
    ), subtitle="Apps speak JSON Lines over stdio. AI features live in the engine, so every language gets all of them on day one.", width="wide")


# ---------------------------------------------------------------- library

@page("/components", "Library", "Components", "layers")
def components(ctx):
    return P(ui.page(
        "Component library",
        P(ui.grid(
            card("Buttons", P(ui.row(P(ui.button("Primary"), variant="primary"), ui.button("Secondary"), P(ui.button("Ghost"), variant="ghost"), P(ui.button("Danger"), variant="danger"),
                                     P(ui.button("Ask AI"), variant="ai", icon="sparkles")), gap="xs"),
                 P(ui.row(P(ui.button("Download"), icon="download", size="sm"), P(ui.button("Saving"), loading=True, size="sm"), P(ui.button("Disabled"), disabled=True, size="sm"),
                          P(ui.button("Search"), kbd="/", size="sm")), gap="xs")),
            card("Badges, tags and avatars",
                 P(ui.row(P(ui.badge("Paid"), tone="success", dot=True), P(ui.badge("Pending"), tone="warning"), P(ui.badge("Overdue"), tone="danger"), P(ui.badge("Draft"), variant="outline"),
                          P(ui.badge("AI"), tone="ai", icon="sparkles")), gap="xs"),
                 P(ui.row(ui.tag("importer"), P(ui.tag("billing"), tone="brand"), P(ui.tag("p1"), tone="danger", removable=True), P(ui.avatar("Mira Okafor"), status="online"),
                          ui.avatar("Jonas Weber"), ui.avatar("Ana Lima"), P(ui.avatar("Kenji Sato"), size="lg")), gap="xs")),
            card("Keys and links", P(ui.row(ui.kbd("Ctrl+K"), ui.kbd("Ctrl+."), ui.kbd("Alt+Click"), ui.link("Documentation", "/languages"), P(ui.link("Source", "https://github.com/fluidian/fluidian"), external=True)), gap="sm"),
                 P(ui.breadcrumbs(), items=[{"label": "Workspace", "route": "/"}, {"label": "Billing", "route": "/dashboard"}, {"label": "INV-2041"}])),
        ), columns=3),
        P(ui.grid(
            ui.stack(P(ui.callout("Import finished"), tone="success", body="12,402 rows were added."), P(ui.callout("Duplicates are not merged yet"), tone="warning", body="Deduplication arrives on the 14th."),
                     P(ui.callout("Card declined"), tone="danger", body="Ask the customer for another payment method."), P(ui.banner("A new version is available."), tone="brand", dismissible=True)),
            card("Tabs and disclosure", P(ui.tabs(ui.tab("Activity", P(ui.timeline(), items=[
                {"title": "Invoice sent", "time": "09:14", "detail": "INV-2041 to Globex Marine", "tone": "brand", "icon": "send"},
                {"title": "Reminder scheduled", "time": "11:02", "tone": "warning", "icon": "clock"}, {"title": "Payment received", "time": "15:40", "detail": "$12,400 by bank transfer", "tone": "success", "icon": "check"}])),
                ui.tab("Details", muted("Details panel")), P(ui.tab("Files", muted("Files panel")), badge="3")), variant="pill"),
                 P(ui.disclosure("Advanced options", muted("Rarely used settings stay out of the way.")), hint="3 settings")),
            card("Structured content", kv([("Customer", "Globex Marine"), ("Terms", "Net 30"), ("Currency", "USD"), ("Owner", "Mira Okafor")], 2),
                 P(ui.steps(), current=1, items=[{"title": "Draft"}, {"title": "Sent"}, {"title": "Paid"}]),
                 P(ui.tree(), items=[{"label": "contracts", "children": [{"label": "globex-msa.pdf"}, {"label": "globex-sow-2026.pdf"}]}, {"label": "invoices", "children": [{"label": "INV-2041.pdf"}]}])),
        ), columns=3),
        P(ui.grid(
            card("Lists", P(ui.list(), items=[{"avatar": "Globex Marine", "title": "Globex Marine", "detail": "3 open invoices", "badge": "Overdue", "meta": "$12,400"},
                                              {"avatar": "Orbit Outfitters", "title": "Orbit Outfitters", "detail": "1 open invoice", "badge": "Pending", "meta": "$18,250"},
                                              {"avatar": "Juniper Health", "title": "Juniper Health", "detail": "Paid in full", "badge": "Paid", "meta": "$4,300"}])),
            card("Code and quotes", P(ui.code('ui.table().prop("rows", invoices).ai("data.query")'), language="python", title="one line of AI"),
                 P(ui.blockquote("Make the right thing the easy thing."), cite="Design principle")),
            card("Progress and skeletons", P(ui.progress(64), label="Quarter close", tone="brand"), P(ui.progress(30), label="Importing", indeterminate=True), P(ui.skeleton(), shape="text", lines=3)),
        ), columns=3),
    ), subtitle="%d components share one set of design tokens and twenty-seven themes, and every one of them accepts AI attachments." % COMPONENT_COUNT, width="wide")


@page("/inputs", "Library", "Inputs", "edit")
def inputs(ctx):
    return P(ui.page(
        "Inputs",
        ui.form("all-inputs", P(ui.grid(
            card("Text", P(ui.input("name"), label="Full name", value="Mira Okafor", icon="user"), P(ui.input("amount"), label="Amount", value="1,250.00", prefix="$", suffix="USD"),
                 P(ui.input("site"), label="Website", placeholder="example.com", prefix="https://", help="Used on invoices"), P(ui.text_area("bio"), label="About", rows=3, value="Finance lead. Likes clean ledgers.")),
            card("Choice", P(ui.select("plan"), label="Plan", options=["Starter", "Team", "Enterprise"], value="Team"),
                 P(ui.radio_group("billing"), label="Billing", options=["Monthly", "Yearly"], value="Yearly", layout="horizontal"), P(ui.segmented("view"), label="View", options=["List", "Board", "Calendar"], value="Board"),
                 P(ui.checkbox("terms", "I accept the terms"), checked=True), P(ui.toggle("alerts", "Email me about overdue invoices"), checked=True)),
            card("Range and rich", P(ui.slider("seats"), label="Seats", min=1, max=50, value=18, unit="seats"), P(ui.rating("csat"), label="Satisfaction", value=4, max=5),
                 P(ui.tag_input("labels"), label="Labels", value=["billing", "q4"], suggestions=["importer", "priority"], placeholder="Add a label"),
                 P(ui.search("find"), placeholder="Search invoices", kbd="/"), P(ui.file_drop("attachment"), label="Attach a file", hint="PDF or image, up to 10 MB")),
        ), columns=3)).id("all-inputs").on("submit", "saved"),
    ), subtitle="Fifteen input controls with consistent labelling, help text, validation and keyboard behaviour.", width="wide")


@page("/board", "Library", "Board and priorities", "grid")
def board(ctx):
    items = [{"title": "Excel support in importer", "detail": "Ships Friday · 2 customers waiting", "badge": "p1"}, {"title": "Overdue reminder emails", "detail": "Copy review pending"},
             {"title": "Role-based dashboards", "detail": "2 approvals needed"}, {"title": "Audit log export", "detail": "Requested by compliance, due in 3 weeks"}]
    return P(ui.page(
        "Board",
        P(ui.board(), columns=S.BOARD).id("kanban").on("select", "saved"),
        P(ui.split(
            card("Suggested order for today", P(ui.list(), items=items, dense=True).id("today").ai("ambient.priority"), eyebrow="ambient.priority"),
            card("Sprint health", P(ui.progress(5), max=8, label="Cards finished or in review", tone="success"),
                 kv([("In progress", "2 cards"), ("Blocked", "None"), ("Oldest card", "Role-based dashboards · 4 days")])),
        ), ratio="3:2"),
    ), subtitle="A kanban board, with the kernel suggesting what to pick up first.", width="wide")


@page("/tour", "Library", "Guided tour", "flag")
def tour(ctx):
    return P(ui.page(
        "Guided tours",
        P(ui.grid(
            P(ui.stat("Open invoices", "23"), icon="file", delta="+4").id("tour-open"),
            P(ui.stat("Overdue", "4"), icon="alert", tone="warning", delta="$27,220").id("tour-overdue"),
            P(ui.stat("Collected this month", "$184,300"), icon="dollar", delta="+9.1%").id("tour-collected"),
        ), columns=3),
        card("Receivables", P(ui.table(), columns=S.INVOICE_COLUMNS[:5], rows=S.INVOICES[:5], dense=True).id("tour-table").ai("data.query")),
        muted("The kernel can also write a tour from the live scene.").id("tour-seed").ai("content.tour", {"audience": "new finance user"}),
        P(ui.tour(), active=True, current=1, steps=[
            {"target": "tour-open", "title": "Everything that is still open", "body": "This number includes drafts. Click it to see the list."},
            {"target": "tour-overdue", "title": "Start here each morning", "body": "Overdue invoices are sorted by amount. The kernel drafts reminders for you to approve."},
            {"target": "tour-table", "title": "Filter by typing", "body": "Try “pending over 5000”. No query language to learn."}]).id("the-tour"),
    ), subtitle="Tours spotlight real nodes by id. content.tour can write the steps from the live scene.", width="wide")


# ---------------------------------------------------------------- app wiring

def not_found(route):
    return ui.page("Not found", P(ui.empty_state("There is no page at %s" % route, P(ui.button("Back to the overview"), variant="primary").on("click", "go", {"route": "/"})),
                                   description="Pick a page from the navigation on the left.", icon="search"))


@app.view
def view(ctx):
    route = (ctx.route or "/").split("?")[0].rstrip("/") or "/"
    entry = next((p for p in PAGES if p["route"] == route), None)
    PAGES.sort(key=lambda p: SECTIONS.index(p["section"]))  # stable: pages keep their order within a section
    nav = [{"label": p["label"], "icon": p["icon"], "route": p["route"], "section": p["section"], "active": p is entry} for p in PAGES]
    body = entry["build"](ctx) if entry else not_found(route)
    return P(ui.shell("Fluidian", body), tagline="Gallery", nav=nav, user={"name": "Mira Okafor", "role": "Finance lead"}).id("shell")


@app.on("go")
def go(ctx, event):
    payload = event.payload if isinstance(event.payload, dict) else {}
    ctx.navigate(payload.get("route") or "/")


@app.on("saved")
def saved(ctx, event):
    ctx.toast("Saved", "success")


@app.on("set_theme_prompt")
def set_theme_prompt(ctx, event):
    if event.value in THEME_PROMPTS:
        ctx.state["theme_prompt"] = event.value


def remember(ctx, text):
    ctx.state["last_action"] = text
    ctx.toast(text[:1].upper() + text[1:], "success")


@app.action("create_invoice", "Create a new invoice for a customer", {"customer": "string customer name", "amount": "number amount in USD", "due": "date due date"})
def create_invoice(ctx, event):
    args = event.payload if isinstance(event.payload, dict) else {}
    amount = args.get("amount")
    remember(ctx, "created an invoice for %s%s%s" % (args.get("customer") or "a customer", " for $%s" % format(amount, ",") if isinstance(amount, (int, float)) else "",
                                                     ", due %s" % args["due"] if args.get("due") else ""))


@app.action("send_reminder", "Send a payment reminder for an invoice", {"invoice": "string invoice number such as INV-2041"})
def send_reminder(ctx, event):
    args = event.payload if isinstance(event.payload, dict) else {}
    remember(ctx, "queued a reminder for %s" % (args.get("invoice") or "the selected invoice"))


@app.action("export_report", "Export the current view as a file", {"format": "string one of csv, xlsx, pdf"})
def export_report(ctx, event):
    args = event.payload if isinstance(event.payload, dict) else {}
    remember(ctx, "exported the view as %s" % str(args.get("format") or "csv").upper())


@app.action("open_page", "Open a page of the gallery", {"page": "string page name such as dashboard, forms, theme or trust"})
def open_page(ctx, event):
    args = event.payload if isinstance(event.payload, dict) else {}
    wanted = str(args.get("page") or "").strip("/ ").lower()
    match = next((p for p in PAGES if wanted and (wanted == p["route"].strip("/") or wanted in p["label"].lower())), None)
    if match:
        ctx.navigate(match["route"])
    else:
        ctx.toast("There is no page called “%s”." % (wanted or "that"), "warning")


if __name__ == "__main__":
    app.run()
