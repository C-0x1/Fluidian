"""Developer Experience and Multimodal capabilities."""
from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List

from .. import components as C
from ..reflex import data as D
from ..reflex import parse as P
from ..reflex import review as R
from ..reflex import scene as S
from ..reflex import text as T
from .c_compose import scene_in
from .registry import FIELDS, ITEMS, NOTE, REPORT, SCENE, TEXT, Ctx, cap, fields, items, note, scene

LANGS = "enum:python|javascript|typescript|go|rust|java|kotlin|csharp|cpp|ruby|php|dart|elixir|lua"
FORM = {"type": "Page", "props": {"title": "Contact"}, "children": [
    {"type": "Form", "id": "contact", "props": {"name": "contact"}, "on": {"submit": "send"}, "children": [
        {"type": "Input", "id": "email", "props": {"name": "email", "label": "Email", "kind": "email"}},
        {"type": "Button", "id": "send", "props": {"label": "Send message", "variant": "primary"}}]}]}


def _explain_node(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    node = C.find(scene_in(i, c), i.get("target") or "")
    if node is None:
        return note("Unknown node", "No node with that id exists in the scene.", [], 0.9, "warning")
    spec = C.SPEC[node["type"]]
    bullets = ["%s = %s" % (k, json.dumps(v, ensure_ascii=False)[:60]) for k, v in (node.get("props") or {}).items()][:5]
    bullets += ["on %s → %s" % (e, b["action"]) for e, b in (node.get("on") or {}).items()]
    bullets += ["ai: %s" % b["capability"] for b in node.get("ai") or []]
    return note("%s #%s" % (node["type"], node["id"]), spec["summary"], bullets, 0.95, "info")


cap("dev.explain_node", "Explain This Node",
    "Explains any node in the inspector: what the component does, how its props are set, what it is bound to.",
    why="Reading someone else's scene should not require reading the component reference.",
    do="Explain the node's purpose in this screen in one sentence, then list its notable props and bindings.",
    inp={"target": "str", "scene?": "any"}, out=NOTE, present="ask", uses_scene=True, ex={"target": "send", "scene": FORM}, reflex=_explain_node)

cap("dev.ux_review", "Heuristic UX Review",
    "Reviews a scene against usability heuristics and returns scored findings with fixes.",
    why="Design review is the bottleneck of every UI team; a first pass should be instant.",
    do="Review the scene against usability heuristics. Start from the findings in facts, add any you can justify from the outline, and give each a concrete fix.",
    inp={"scene?": "any"}, out=REPORT, present="audit", tier="balanced", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": ""}, "children": [{"type": "Input", "props": {"name": "q", "placeholder": "Type here"}},
                                                                    {"type": "Button", "props": {"label": "OK", "variant": "primary"}},
                                                                    {"type": "Button", "props": {"label": "Delete account", "variant": "primary"}}]}},
    facts=lambda i, c: R.ux_review(scene_in(i, c)), reflex=lambda i, c: R.ux_review(scene_in(i, c)))

cap("dev.test_synth", "Test Synthesis",
    "Generates Autopilot interaction tests from a scene: fill every field, press every action, assert the event.",
    why="UI tests are written last and least; deriving them from the scene makes coverage the default.",
    do="Write interaction test cases for the scene. Each step is type, click, select or expect, targeting element ids from the scene.",
    inp={"scene?": "any"}, out={"cases": [{"name": "str", "steps": [{"do": "enum:type|click|select|expect", "target": "str", "value?": "str"}]}]},
    present="service", uses_scene=True, ex={"scene": FORM},
    reflex=lambda i, c: {"cases": [{"name": t["name"], "steps": [{"do": s["do"], "target": s["target"], "value": s.get("value")} for s in t["steps"]]}
                                   for t in R.synth_tests(scene_in(i, c))]})


def _rows_post(out: Dict[str, Any], i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    if isinstance(out.get("rows"), str):
        try:
            parsed = json.loads(out["rows"])
        except ValueError:
            parsed = []
        out["rows"] = parsed if isinstance(parsed, list) else []
    out["count"] = len(out.get("rows") or [])
    return out


cap("dev.fixtures", "Fixture Generator",
    "Produces realistic, deterministic sample data for a list of fields or a JSON Schema.",
    why="Screens designed against “Lorem ipsum” break on real names, long emails and large numbers.",
    do="Generate realistic rows for the fields as a JSON array string. Values must be plausible, varied and internally consistent.",
    inp={"fields": "any", "count?": "int", "seed?": "str"}, out={"rows": "json", "count": "int"}, present="service", post=_rows_post,
    ex={"fields": ["name", "email", "plan", "mrr"], "count": 3},
    reflex=lambda i, c: (lambda rows: {"rows": json.dumps(rows), "count": len(rows)})(D.fixtures(i["fields"], int(i.get("count") or 5), i.get("seed") or "fluidian")))


def _transpose(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    from .. import codegen
    sc = scene_in(i, c)
    return {"language": i["language"], "code": codegen.emit_scene(sc, i["language"]), "nodes": C.stats(sc)["nodes"]}


cap("dev.transpose", "Scene-to-Code in 14 Languages",
    "Emits idiomatic SDK code for any scene in any of the fourteen supported languages.",
    why="A scene designed in the playground, generated by a model or captured from production should be one step from source code.",
    inp={"scene?": "any", "language": LANGS}, out={"language": "str", "code": "str", "nodes": "int"}, present="service",
    ex={"scene": FORM, "language": "go"}, direct=_transpose)


def _scaffold(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    from .. import codegen
    sc, why = S.compose_intent(i["description"])
    sc = C.normalize(sc)[0]
    return {"language": i["language"], "code": codegen.emit_app(sc, i["language"], S._intent_title(i["description"])),
            "run": codegen.RUN_HINT.get(i["language"], ""), "rationale": why}


cap("dev.scaffold", "App Scaffolder",
    "Generates a complete, runnable starter application in a chosen language from a description.",
    why="The first ten minutes with a framework decide whether there is an eleventh.",
    inp={"description": "str", "language": LANGS}, out={"language": "str", "code": "str", "run": "str", "rationale": "str"},
    present="service", ex={"description": "contact form with name, email and message", "language": "python"}, direct=_scaffold)


def _port(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    from .. import codegen
    target = i["to"]
    sc = C.normalize({"type": "Page", "props": {"title": "Ported app"}, "children": [{"type": "Text", "props": {"content": "Port the view body here."}}]})[0]
    return {"code": codegen.emit_app(sc, target, "Ported app"),
            "notes": ["Offline: produced the %s application skeleton; handler logic needs the Reason path to be ported automatically." % target,
                      "State lives in ctx.state in every SDK; handler names are unchanged across languages."]}


cap("dev.port", "Cross-Language Porting",
    "Ports a Fluidian application — view and handlers — from one supported language to another.",
    why="Teams change stacks; the interface definition should move with them.",
    do="Port the application to the target language using that language's Fluidian SDK idioms. Preserve action names, state keys and behaviour exactly.",
    inp={"source": "str", "from": LANGS, "to": LANGS}, out={"code": "str", "notes": ["str"]}, present="service", tier="deep", max_out=3000,
    untrusted=["source"], ex={"source": "app.on('increment', (ctx) => { ctx.state.count = (ctx.state.count || 0) + 1 })", "from": "javascript", "to": "rust"},
    reflex=_port)


def _docs(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    spec = C.SPEC.get(i["component"])
    if spec is None:
        return {"markdown": "Unknown component `%s`." % i["component"]}
    lines = ["### %s" % spec["type"], "", spec["summary"], "", "| Prop | Type | Default | Description |", "|---|---|---|---|"]
    for name, p in spec["props"].items():
        lines.append("| `%s`%s | %s | %s | %s |" % (name, " (arg)" if p["arg"] else "", p["kind"].replace("|", " \\| "), p["default"] or "—", p["doc"]))
    if spec["events"]:
        lines += ["", "Events: " + ", ".join("`%s`" % e for e in spec["events"])]
    return {"markdown": "\n".join(lines)}


cap("dev.docs", "Component Docs Author",
    "Writes reference documentation for a component from its registry entry.",
    why="Documentation generated from the source of truth cannot drift from it.",
    inp={"component": "str"}, out={"markdown": "str"}, present="service", ex={"component": "Button"}, direct=_docs)


def _err(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    e = i["error"]
    low = e.lower()
    table = [(r"unknown component", "A node uses a component type that is not in the catalogue.", ["Check the spelling against `fluidian components`.", "Custom markup belongs in Markdown or Code."]),
             (r"unknown action|no handler|unhandled", "An event is bound to an action with no registered handler.", ["Register it with app.on(\"name\", handler).", "Names are case-sensitive."]),
             (r"json|parse|unexpected token|decode", "A protocol line was not valid JSON.", ["Print logs to stderr; stdout is reserved for the protocol.", "Run `fluidian run --trace` to see the offending line."]),
             (r"api key|401|unauthor", "The provider rejected the API key.", ["Set OPENAI_API_KEY in the environment that starts the engine.", "Run `fluidian doctor --live`."]),
             (r"model.*(not found|does not exist)|404", "The configured model is not available to this account.", ["Run `fluidian doctor --live` to list reachable models.", "Override with FLUIDIAN_MODEL_FAST / _BALANCED / _DEEP."]),
             (r"429|rate limit|quota", "The provider is rate limiting or the quota is exhausted.", ["The kernel retries with backoff, then serves Reflex results.", "Lower traffic with the cache or raise the limit."]),
             (r"budget", "The session or global token budget is exhausted.", ["Raise FLUIDIAN_SESSION_TOKEN_BUDGET.", "Results degrade to the Reflex path until the budget resets."]),
             (r"consent", "The capability needs consent that has not been granted.", ["Call trust.consent with the scope, or use the consent prompt.", "Remove the scope from consent_required if it does not apply."]),
             (r"address already in use|eaddrinuse", "Another process is using the port.", ["Pass --port, or stop the other process."]),
             (r"timed? ?out|timeout", "The application or provider did not answer in time.", ["Check that the app flushes stdout after each line.", "Raise FLUIDIAN_TIMEOUT for slow models."])]
    lines = [ln.strip() for ln in e.strip().splitlines() if ln.strip()]
    headline = next((ln for ln in reversed(lines) if re.match(r"^[A-Za-z_.]*(Error|Exception|Warning|panic)\b", ln)), lines[-1] if lines else e)
    where = re.search(r'File "([^"]+)", line (\d+)|\bat .*?\(?([\w./\\-]+):(\d+)(?::\d+)?\)?', e)
    place = ("%s line %s" % (where.group(1) or where.group(3), where.group(2) or where.group(4))) if where else ""
    runtime = [
        (r"unsupported operand type\(s\) for .*'int' and 'str'|unsupported operand type\(s\) for .*'str' and 'int'|can only concatenate str",
         "A number and a string are being combined. One of the values is still text, usually because it came from a form or a file.",
         ["Convert before the arithmetic: float(row[\"amount\"]).", "Use data.column_types to detect numeric columns that arrive as text.", "Validate the field with input.natural_quantity so it is stored as a number."]),
        (r"keyerror|has no attribute|undefined is not|cannot read propert(y|ies) of (undefined|null)|nonetype",
         "The code reads a field that is missing from the value it received.",
         ["Read optional values defensively: event.form.get(\"name\") or state.get(\"count\", 0).", "Check the event payload with `fluidian run --trace`.", "Give the node a stable id so the event targets what you expect."]),
        (r"modulenotfounderror|no module named|cannot find module|could not resolve|unresolved import",
         "The SDK or a dependency is not on the import path of the app process.",
         ["Install the SDK for this language or point the path at the checkout.", "Run `fluidian doctor` to see which toolchains and SDKs were found."]),
        (r"indexerror|out of range|out of bounds", "The code indexes past the end of a list.",
         ["Guard against empty data before reading the first or last item.", "Render an EmptyState when the list has no rows."]),
        (r"zerodivisionerror|division by zero|divide by zero", "A calculation divides by zero.",
         ["Return 0 or a dash when the denominator is 0.", "data.formula guards generated expressions against empty denominators."]),
        (r"recursionerror|maximum call stack|stack overflow", "A function calls itself without reaching a stopping condition.",
         ["Check that a handler does not trigger the event it is handling.", "Calling ctx.navigate inside the view re-enters the view."]),
    ]
    for pattern, body, steps in runtime + table:
        if re.search(pattern, low):
            return note(T.clip(headline, 90), body + (" Raised at %s." % place if place else ""), steps, 0.8, "warning")
    return note(T.clip(headline, 90), "No known pattern matched. Run with --trace and inspect the last protocol message.", ["Run `fluidian doctor` to check the installation."], 0.3, "warning")


cap("dev.error_explain", "Error Explainer",
    "Explains framework, protocol and provider errors and lists the steps that fix them.",
    why="Stack traces describe where code stopped, not what to do about it.",
    do="Explain the error's cause in one sentence and list up to three specific fixes for a Fluidian application.",
    inp={"error": "str", "language?": "str"}, out=NOTE, present="annotate", ex={"error": "ProviderError: The model `gpt-9` does not exist (HTTP 404)"}, reflex=_err)

cap("dev.persona_sim", "Synthetic Persona Walkthrough",
    "Walks a described persona through a screen and reports where they would struggle, in their own words.",
    why="Usability testing finds problems late and rarely; a simulated first pass costs nothing.",
    do="Role-play the persona's first visit to this scene. Report each point of friction as a finding in the first person, with the fix.",
    inp={"persona": "str", "scene?": "any"}, out=REPORT, present="audit", tier="balanced", uses_scene=True,
    ex={"persona": "a first-time, non-technical user on a phone", "scene": FORM},
    facts=lambda i, c: R.persona_walkthrough(scene_in(i, c), i["persona"]), reflex=lambda i, c: R.persona_walkthrough(scene_in(i, c), i["persona"]))

cap("dev.scene_lint", "Scene Lint",
    "Checks a scene for structural mistakes: unknown props, orphan tabs, duplicate field names, unbound actions.",
    why="Declarative UI fails silently; lint makes the failure loud at development time.",
    inp={"scene?": "any", "actions?": ["str"]}, out=REPORT, present="audit", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "T", "colour": "red"}, "children": [{"type": "Tab", "props": {"label": "Orphan"}}]}},
    direct=lambda i, c: R.scene_lint(scene_in(i, c), i.get("actions") if isinstance(i.get("actions"), list) else ([a.get("name") for a in c.actions] or None)))


def _diff(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    a, b = C.normalize(C.from_transport(i["before"]))[0], C.normalize(C.from_transport(i["after"]))[0]
    changes = C.diff(a, b)
    words = {"added": "added", "removed": "removed", "changed": "updated", "replaced": "replaced"}
    return {"changes": [{"op": ch["op"], "id": ch["id"], "type": ch["type"], "text": ch.get("text") or ""} for ch in changes],
            "narrative": "; ".join("%s %s%s" % (words[ch["op"]], ch["type"], " “%s”" % ch["text"] if ch.get("text") else "") for ch in changes[:8]) or "No differences."}


cap("dev.diff_narrate", "Scene Diff Narrator",
    "Computes the structural difference between two scenes and narrates it for reviews and time-travel debugging.",
    why="JSON diffs of UI trees are unreadable; reviewers need “the Save button moved into the toolbar”.",
    inp={"before": "any", "after": "any"},
    out={"changes": [{"op": "enum:added|removed|changed|replaced", "id": "str", "type": "str", "text": "str"}], "narrative": "str"},
    present="service", ex={"before": FORM, "after": {"type": "Page", "props": {"title": "Contact us"}, "children": []}}, direct=_diff)


def _names(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    keys = T.keywords(i["description"], 4) or ["item"]
    verb = next((w for w in T.words(i["description"]) if w in ("create", "delete", "update", "send", "export", "import", "invite", "archive", "approve", "open", "save", "cancel", "refund")), "")
    nouns = [k for k in keys if k != verb]
    base = "_".join(([verb] if verb else []) + nouns[:2])
    alts = [base, "_".join(nouns[:2] + ([verb] if verb else [])), "_".join(([verb] if verb else ["handle"]) + nouns[:1])]
    return items([{"label": a, "value": a, "score": round(1 - n * 0.2, 2)} for n, a in enumerate(dict.fromkeys(a for a in alts if a))])


cap("dev.name", "Naming Assistant",
    "Suggests clear snake_case names for actions, ids and fields from a description.",
    why="Naming is the hard part of programming and the first thing a model can take off your plate.",
    do="Suggest three snake_case names, verb first for actions, most conventional first.",
    inp={"description": "str", "kind?": "str"}, out=ITEMS, present="suggest", max_out=120,
    ex={"description": "send the invoice reminder email", "kind": "action"}, reflex=_names)

cap("dev.perf_hint", "Render Cost Advisor",
    "Flags scenes that will be slow or janky: unpaginated tables, dense charts, layout-shifting images, AI fan-out.",
    why="Performance problems are cheapest to fix before the data is real.",
    inp={"scene?": "any"}, out=REPORT, present="audit", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Big"}, "children": [{"type": "Image", "props": {"src": "/a.png", "alt": "A"}},
                                                                       {"type": "Table", "props": {"rows": [{"n": n} for n in range(260)], "columns": [{"key": "n", "label": "N"}]}}]}},
    direct=lambda i, c: R.perf_hints(scene_in(i, c)))

# --- multimodal ------------------------------------------------------------------------
def _clean_speech(text: str) -> str:
    words = [w for w in (text or "").split() if w.lower().strip(",.") not in ("um", "uh", "er", "erm", "hmm")]
    out = re.sub(r"\b(\w+)( \1\b)+", r"\1", " ".join(words), flags=re.IGNORECASE)
    out = out.strip()
    if out and out[-1] not in ".!?":
        out += "."
    return out[:1].upper() + out[1:]


cap("modal.dictate", "Dictation",
    "Transcribes speech and cleans it into written text: fillers removed, punctuation added, repeats collapsed.",
    why="Speaking is three times faster than typing, but raw transcripts are not writing.",
    inp={"audio?": "str", "transcript?": "str", "language?": "str"}, out={"text": "str", "source": "str"}, present="media",
    binds=["Mic", "TextArea", "Input"], consent="microphone", ex={"transcript": "um so the the invoice is uh late again"},
    direct=lambda i, c: (lambda t: {"text": _clean_speech(t["text"]), "source": t["source"]})(
        c.kernel.media.transcribe(i) if (c.kernel and i.get("audio")) else {"text": i.get("transcript") or "", "source": "transcript"}))

cap("modal.speak", "Read Aloud",
    "Speaks any text with the speech model, falling back to the browser's built-in voice offline.",
    why="Listening is how many people prefer — or need — to consume text.",
    inp={"text": "str", "voice?": "str"}, out={"audio": "str", "fallback": "enum:none|browser", "text": "str"}, present="media",
    binds=["Text", "Markdown", "Insight", "Copilot"], ex={"text": "Revenue is up eighteen percent this quarter."},
    direct=lambda i, c: c.kernel.media.speak(i) if c.kernel else {"audio": "", "fallback": "browser", "text": i["text"]})

cap("modal.vision_form", "Document-to-Form",
    "Reads a photographed receipt, card or document and fills the form fields it finds.",
    why="Retyping what a camera can already see is the purest form of busywork.",
    do="Read the document image (or its text) and extract a value for each listed field. Omit fields that are not present.",
    inp={"fields": ["any"], "image?": "str", "text?": "str"}, out=FIELDS, present="fill", binds=["FileDrop", "Form"], vision=True,
    untrusted=["text"], ex={"fields": ["company", "amount", "date"], "text": "Tidewater Coffee Ltd\nTotal: $18.40\n2026-11-02"},
    reflex=lambda i, c: fields(P.smart_paste(i.get("text") or "", i["fields"]), None if i.get("text") else "Reading images requires the Reason path."))

cap("modal.screenshot_scene", "Screenshot-to-Scene",
    "Rebuilds a screenshot or mock-up as a live scene using catalogue components.",
    why="Design hand-off is a translation step; vision models can do the first draft of the translation.",
    do="Recreate the interface in the image (or description) as a scene. Match structure and text; use catalogue components and ignore exact styling.",
    inp={"image?": "str", "description?": "str"}, out=SCENE, present="compose", tier="deep", binds=["Generative", "FileDrop"], vision=True, max_out=3000,
    ex={"description": "orders table with a search box and a New order button"},
    reflex=lambda i, c: scene(*S.compose_intent(i.get("description") or "empty page")))

cap("modal.describe_image", "Image Understanding",
    "Describes what an image shows and extracts the details relevant to the task at hand.",
    why="Images uploaded to business software are data that nobody can search or summarise.",
    do="Describe the image in one sentence, then list the details relevant to the context as bullets.",
    inp={"image?": "str", "context?": "str"}, out=NOTE, present="annotate", binds=["Image", "FileDrop"], vision=True,
    ex={"context": "damage claim photo"},
    reflex=lambda i, c: note("Image attached", "A description needs the vision model; connect an API key to enable it.",
                             [("Context: " + i["context"])] if i.get("context") else [], 0.1, "neutral"))


def _digitize(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    pts = [{"label": m.group(1).strip(), "value": float(m.group(2).replace(",", ""))}
           for m in re.finditer(r"([A-Za-z][\w ]{0,20}?)\s*[:=]?\s*(-?\d[\d,]*\.?\d*)", i.get("hint") or "")]
    return {"kind": "bar", "points": pts, "confidence": 0.5 if pts else 0.0}


cap("modal.chart_digitize", "Chart Digitizer",
    "Recovers the underlying data from a chart image so it can be re-plotted, queried or exported.",
    why="Half the world's data is trapped in screenshots of charts.",
    do="Read the chart and return its kind and data points as label/value pairs. Estimate values from the axis; state your confidence.",
    inp={"image?": "str", "hint?": "str"}, out={"kind": "str", "points": [{"label": "str", "value": "num"}], "confidence": "num"},
    present="service", binds=["FileDrop", "Image"], vision=True, ex={"hint": "Jan 10, Feb 14, Mar 19"}, reflex=_digitize)

cap("modal.audio_actions", "Audio-to-Action-Items",
    "Turns a meeting transcript into a recap card with decisions and owned next steps.",
    why="The value of a meeting is its follow-ups, and they are rarely written down.",
    do="Compose a recap Card: two-sentence summary, a Decisions list and a Next steps list with owners. Use only the transcript.",
    inp={"transcript": "str"}, out=SCENE, present="compose", binds=["Generative", "Mic"], untrusted=["transcript"],
    ex={"transcript": "We agreed to ship mapping first. Mira will write the guide by Friday. Dedup needs to wait."},
    reflex=lambda i, c: scene(S.recap(i["transcript"]), "Summary, decisions and follow-ups extracted from the transcript."))


def _sonify(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    vals = [float(v) for v in i["values"]][:64]
    lo, hi = (min(vals), max(vals)) if vals else (0.0, 1.0)
    span = (hi - lo) or 1.0
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]  # major pentatonic over two octaves
    notes = [{"t": round(n * 0.22, 2), "freq": round(220.0 * 2 ** (scale[int(round((v - lo) / span * (len(scale) - 1)))] / 12.0), 2), "dur": 0.2}
             for n, v in enumerate(vals)]
    return {"notes": notes, "legend": "Higher pitch means a higher value; range %s to %s over %.1f seconds." % (D.fmt(lo), D.fmt(hi), len(vals) * 0.22)}


cap("modal.sonify", "Data Sonification",
    "Maps a data series to pitch so a trend can be heard: rising values rise in tone.",
    why="Charts are a visual medium; sound makes trends available to people who cannot see them.",
    inp={"values": ["num"]}, out={"notes": [{"t": "num", "freq": "num", "dur": "num"}], "legend": "str"}, present="media", binds=["Chart"],
    ex={"values": [10, 12, 13, 15, 40, 17, 19]}, direct=_sonify)


def _ink(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    pts: List[Dict[str, float]] = [p for stroke in (i.get("strokes") or []) for p in stroke if isinstance(p, dict)]
    if len(pts) < 2:
        return {"shape": "scribble", "confidence": 0.1, "bounds": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}}
    xs, ys = [float(p["x"]) for p in pts], [float(p["y"]) for p in pts]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    path = sum(math.hypot(xs[k] - xs[k - 1], ys[k] - ys[k - 1]) for k in range(1, len(pts)))
    gap = math.hypot(xs[-1] - xs[0], ys[-1] - ys[0])
    diag = math.hypot(w, h) or 1.0
    turns = 0
    for k in range(2, len(pts)):
        a = math.atan2(ys[k - 1] - ys[k - 2], xs[k - 1] - xs[k - 2])
        b = math.atan2(ys[k] - ys[k - 1], xs[k] - xs[k - 1])
        d = abs((b - a + math.pi) % (2 * math.pi) - math.pi)
        turns += 1 if d > math.radians(50) else 0
    closed = gap < 0.2 * diag and path > 2 * diag
    if closed:
        shape, conf = ("rectangle", 0.75) if 3 <= turns <= 6 else ("ellipse", 0.7)
    elif path < 1.15 * gap:
        shape, conf = "line", 0.85
    elif turns == 1 and ys.index(max(ys)) not in (0, len(ys) - 1):
        shape, conf = "check", 0.6
    elif turns in (2, 3) and path < 1.8 * gap:
        shape, conf = "arrow", 0.5
    else:
        shape, conf = "scribble", 0.4
    return {"shape": shape, "confidence": conf, "bounds": {"x": min(xs), "y": min(ys), "w": w, "h": h}}


cap("modal.ink", "Ink Interpretation",
    "Recognises hand-drawn strokes as lines, rectangles, ellipses, arrows or checks for sketch-based input.",
    why="Pen and touch users think in strokes; software should meet them there.",
    inp={"strokes": [[{"x": "num", "y": "num"}]]},
    out={"shape": "enum:line|rectangle|ellipse|arrow|check|scribble", "confidence": "num", "bounds": {"x": "num", "y": "num", "w": "num", "h": "num"}},
    present="service", ex={"strokes": [[{"x": 0, "y": 0}, {"x": 100, "y": 0}, {"x": 100, "y": 60}, {"x": 0, "y": 60}, {"x": 0, "y": 2}]]}, direct=_ink)
