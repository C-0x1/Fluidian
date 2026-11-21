"""Reflex review: UX heuristics, accessibility audit, lint, synthetic personas, test synthesis."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .. import components as C
from . import text as T

Node = Dict[str, Any]
INPUTS = {"Input", "TextArea", "Select", "RadioGroup", "Slider", "TagInput", "Rating", "Search", "Segmented", "FileDrop"}
CHECKS = {"Checkbox", "Toggle"}
_VAGUE = {"ok", "okay", "submit", "click here", "yes", "no", "go", "continue", "done", "here", "more", "button", "send"}
_DESTRUCTIVE = re.compile(r"\b(delete|remove|destroy|erase|wipe|revoke|terminate|cancel subscription|discard|purge|reset)\b", re.IGNORECASE)


def _finding(fid: str, severity: str, title: str, detail: str, target: Optional[str] = None, fix: Optional[str] = None) -> Dict[str, Any]:
    return {"id": fid, "severity": severity, "title": title, "detail": detail, "target": target, "fix": fix}


def _score(findings: List[Dict[str, Any]]) -> float:
    cost = {"error": 12, "warning": 6, "info": 2}
    return float(max(0, 100 - sum(cost[f["severity"]] for f in findings)))


def _report(findings: List[Dict[str, Any]], subject: str) -> Dict[str, Any]:
    errors = sum(1 for f in findings if f["severity"] == "error")
    warnings = sum(1 for f in findings if f["severity"] == "warning")
    if not findings:
        summary = "No %s issues found." % subject
    else:
        summary = "%d %s finding%s: %d blocking, %d to improve." % (len(findings), subject, "" if len(findings) == 1 else "s", errors, warnings)
    return {"score": _score(findings), "summary": summary, "findings": findings[:40]}


def suggest_label(text: str) -> str:
    low = (text or "").strip().lower()
    table = {"ok": "Confirm", "okay": "Confirm", "submit": "Save changes", "yes": "Yes, continue", "no": "No, go back",
             "click here": "Open details", "here": "Open details", "more": "Show more", "go": "Continue", "send": "Send message",
             "done": "Finish", "button": "Continue", "continue": "Continue to next step", "delete": "Delete permanently",
             "cancel": "Cancel", "add": "Add item", "new": "Create new", "edit": "Edit details", "remove": "Remove"}
    if low in table:
        return table[low]
    if len(low.split()) > 4:
        return T.friendly_error(text, "Check the highlighted fields and try again.")
    return T.sentence_case(text)


def ux_review(scene: Node) -> Dict[str, Any]:
    """Heuristic evaluation against established usability principles."""
    out: List[Dict[str, Any]] = []
    nodes = list(C.walk(scene))
    if not C.primary_text(scene) and not any(n["type"] in ("Heading", "Hero") for n, _, _ in nodes):
        out.append(_finding("ux.orientation", "warning", "No page title", "People cannot tell where they are without a title or heading.",
                            scene.get("id"), "Give the page a title that names the task."))
    for node, depth, parent in nodes:
        kind, props, nid = node["type"], node.get("props") or {}, node.get("id")
        kids = node.get("children") or []
        if kind in C.CONTAINERS:
            primaries = [k for k in kids if k["type"] == "Button" and (k.get("props") or {}).get("variant") == "primary"]
            if len(primaries) > 1:
                out.append(_finding("ux.single-primary", "warning", "Competing primary actions",
                                    "%d primary buttons share one region (%s)." % (len(primaries), ", ".join(C.primary_text(p) for p in primaries)),
                                    primaries[1].get("id"), "Keep one primary action; demote the others to secondary."))
        if kind == "Form":
            fields = [n for n, _, _ in C.walk(node) if n["type"] in INPUTS | CHECKS]
            grouped = any(n["type"] in ("Section", "Steps", "Tabs", "Disclosure") for n, _, _ in C.walk(node))
            if len(fields) > 7 and not grouped:
                out.append(_finding("ux.long-form", "warning", "Long form without structure",
                                    "%d fields in one block increase abandonment." % len(fields), nid,
                                    "Group related fields into sections or split the form into steps."))
            if not any(n["type"] == "Button" for n, _, _ in C.walk(node)):
                out.append(_finding("ux.no-submit", "warning", "Form has no visible submit action",
                                    "People expect an explicit way to finish.", nid, "Add a primary button labelled with the outcome."))
        if kind in INPUTS - {"Search", "Segmented"} and not props.get("label"):
            sev = "warning" if props.get("placeholder") else "error"
            out.append(_finding("ux.label", sev, "Field without a label",
                                "Placeholder text disappears on input and is not a label." if props.get("placeholder") else "The field's purpose is not stated.",
                                nid, "Add label “%s”." % T.sentence_case(str(props.get("placeholder") or props.get("name") or "Field").replace("_", " "))))
        if kind == "Button":
            label = str(props.get("label") or "")
            if label.strip().lower() in _VAGUE:
                out.append(_finding("ux.vague-action", "info", "Vague button label “%s”" % label,
                                    "Labels should describe the outcome.", nid, "Rename to “%s”." % suggest_label(label)))
            if (props.get("variant") == "danger" or _DESTRUCTIVE.search(label)) and not any(
                    a["type"] in ("Modal", "Approval") for a, _, _ in nodes):
                out.append(_finding("ux.destructive", "warning", "Destructive action without confirmation",
                                    "“%s” has no confirmation step or undo path in this scene." % label, nid,
                                    "Confirm with an Approval card or offer undo."))
        if kind == "Table":
            rows = props.get("rows") if isinstance(props.get("rows"), list) else []
            if not rows and not props.get("empty"):
                out.append(_finding("ux.empty", "info", "Table has no empty state", "An empty table should explain why and what to do next.",
                                    nid, "Provide an EmptyState or the `empty` message."))
            if len(rows) > 50 and not props.get("pageSize"):
                out.append(_finding("ux.long-table", "info", "Long table without pagination", "%d rows render at once." % len(rows), nid, "Set pageSize or add a filter."))
        if kind == "Chart" and not props.get("title") and not (parent and C.primary_text(parent)):
            out.append(_finding("ux.chart-title", "info", "Chart without a title", "A title states what the reader should conclude.", nid, "Add a title that names the measure."))
        if kind == "Card" and depth > 0:
            ancestors = 0
            walker = parent
            while walker is not None and ancestors < 4:
                ancestors += 1 if walker["type"] == "Card" else 0
                walker = next((p for n, _, p in nodes if n is walker), None)
            if ancestors >= 2:
                out.append(_finding("ux.nesting", "info", "Deeply nested cards", "Cards inside cards inside cards flatten the hierarchy.", nid, "Use sections or dividers inside a single card."))
    top = scene.get("children") or []
    if len(top) > 9:
        out.append(_finding("ux.density", "info", "Crowded page", "%d top-level regions compete for attention." % len(top), scene.get("id"), "Group regions into tabs or move secondary content behind disclosure."))
    labels = [str((n.get("props") or {}).get("label") or "") for n, _, _ in nodes if n["type"] == "Button"]
    multi = [lab for lab in labels if len(lab.split()) > 1]
    titled = [lab for lab in multi if all(w[:1].isupper() for w in lab.split() if len(w) > 3)]
    if multi and titled and len(titled) != len(multi):
        out.append(_finding("ux.casing", "info", "Inconsistent capitalisation", "Button labels mix Title Case and sentence case.", None, "Use sentence case everywhere."))
    tones = {(n.get("props") or {}).get("tone") for n, _, _ in nodes if n["type"] in ("Callout", "Banner")}
    if len(tones) > 2:
        out.append(_finding("ux.alarm", "info", "Too many competing notices", "%d differently coloured notices are visible together." % len(tones), None, "Show the most important notice; queue the rest."))
    return _report(out, "usability")


def a11y_audit(scene: Node) -> Dict[str, Any]:
    """Accessibility checks aligned with WCAG 2.2 success criteria."""
    out: List[Dict[str, Any]] = []
    last_level = 0
    for node, _, _ in C.walk(scene):
        kind, props, nid = node["type"], node.get("props") or {}, node.get("id")
        if kind == "Image" and not str(props.get("alt") or "").strip():
            out.append(_finding("a11y.1.1.1", "error", "Image without alternative text", "Screen readers announce nothing for this image.", nid, "Describe the image, or set an empty alt if it is decorative."))
        if kind in INPUTS and not props.get("label") and kind not in ("Search",):
            out.append(_finding("a11y.3.3.2", "error", "Form control without a label", "The control has no accessible name.", nid, "Add a visible label."))
        if kind in CHECKS and not str(props.get("label") or "").strip():
            out.append(_finding("a11y.4.1.2", "error", "Checkbox without a name", "Assistive technology cannot state what this toggles.", nid, "Add a label."))
        if kind == "Button" and not str(props.get("label") or "").strip():
            out.append(_finding("a11y.4.1.2", "error", "Icon-only button without a name", "The button has an icon but no accessible label.", nid, "Add a label; it can be visually hidden."))
        if kind == "Heading":
            try:
                level = int(props.get("level") or 2)
            except (TypeError, ValueError):
                level = 2
            if last_level and level > last_level + 1:
                out.append(_finding("a11y.1.3.1", "warning", "Heading level skipped", "Level %d follows level %d." % (level, last_level), nid, "Use level %d here." % (last_level + 1)))
            last_level = level
        if kind == "Link" and str(props.get("label") or "").strip().lower() in ("click here", "here", "more", "read more", "link", "this"):
            out.append(_finding("a11y.2.4.4", "warning", "Link text is not descriptive", "“%s” means nothing out of context." % props.get("label"), nid, "Describe the destination in the link text."))
        if kind == "Table" and not props.get("caption"):
            out.append(_finding("a11y.1.3.1", "info", "Table without a caption", "A caption lets screen-reader users decide whether to read the table.", nid, "Add a caption."))
        if kind == "Chart" and not props.get("title"):
            out.append(_finding("a11y.1.1.1", "warning", "Chart without a text alternative", "The chart conveys data visually only.", nid, "Add a title and attach data.describe_chart for a description."))
        if kind in ("Modal", "Drawer") and not str(props.get("title") or "").strip():
            out.append(_finding("a11y.2.4.6", "warning", "Dialog without a title", "Dialogs need a name announced on open.", nid, "Add a title."))
        if kind == "Badge" and props.get("tone") in ("success", "danger", "warning") and len(str(props.get("label") or "")) <= 1:
            out.append(_finding("a11y.1.4.1", "warning", "Status conveyed by colour alone", "The badge has no text that carries the status.", nid, "Add a status word."))
        if kind == "Icon" and props.get("tone") in ("danger", "warning", "success"):
            out.append(_finding("a11y.1.4.1", "info", "Icon colour carries meaning", "Pair the icon with text so the meaning survives without colour.", nid, None))
    return _report(out, "accessibility")


def synth_labels(scene: Node) -> List[Dict[str, Any]]:
    """Propose accessible names for controls that lack one."""
    out = []
    for node, _, _ in C.walk(scene):
        kind, props = node["type"], node.get("props") or {}
        has = str(props.get("label") or props.get("alt") or "").strip()
        if has or kind not in INPUTS | CHECKS | {"Button", "Image", "Icon"}:
            continue
        if kind == "Image":
            src = str(props.get("src") or "")
            name = re.sub(r"[-_]+", " ", re.sub(r"\.\w+$", "", src.rsplit("/", 1)[-1].split("?")[0])) if not src.startswith("data:") else ""
            value, conf = (T.sentence_case(name) if name else str(props.get("caption") or "Illustration")), (0.5 if name else 0.3)
        elif kind == "Button":
            icon = str(props.get("icon") or "")
            verbs = {"plus": "Add", "x": "Close", "trash": "Delete", "edit": "Edit", "search": "Search", "settings": "Open settings",
                     "download": "Download", "upload": "Upload", "refresh": "Refresh", "send": "Send", "copy": "Copy", "more": "More options",
                     "filter": "Filter", "menu": "Open menu", "mic": "Start dictation", "bell": "Notifications", "help": "Help"}
            value, conf = verbs.get(icon, T.sentence_case(icon.replace("-", " ")) or "Action"), (0.85 if icon in verbs else 0.4)
        else:
            base = str(props.get("placeholder") or props.get("name") or kind)
            value, conf = T.sentence_case(re.sub(r"[_\-]+", " ", base).rstrip("…. ")), (0.8 if props.get("placeholder") or props.get("name") else 0.3)
        out.append({"name": node["id"], "value": value, "confidence": conf})
    return out


def focus_order(scene: Node) -> List[Dict[str, Any]]:
    """Logical keyboard order: dialogs first, then reading order, with the primary action last in its group."""
    interactive = INPUTS | CHECKS | {"Button", "Link", "Tabs", "IntentBar", "Copilot", "Mic", "Disclosure", "Suggestions", "Table"}
    ordered: List[Node] = []

    def visit(node: Node) -> None:
        kids = list(node.get("children") or [])
        buttons = [k for k in kids if k["type"] == "Button"]
        if len(buttons) > 1 and len(buttons) == len(kids):
            kids.sort(key=lambda k: 1 if (k.get("props") or {}).get("variant") == "primary" else 0)
        if node["type"] in interactive and not (node.get("props") or {}).get("disabled"):
            ordered.append(node)
        for k in kids:
            visit(k)

    dialogs = [n for n, _, _ in C.walk(scene) if n["type"] in ("Modal", "Drawer") and (n.get("props") or {}).get("open")]
    for d in dialogs:
        visit(d)
    if not dialogs:
        visit(scene)
    return [{"label": C.primary_text(n) or n["type"], "value": n["id"], "detail": n["type"], "score": float(i + 1)} for i, n in enumerate(ordered)]


def scene_lint(scene: Node, actions: Optional[List[str]] = None) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    for node, _, parent in C.walk(scene):
        kind, props, nid = node["type"], node.get("props") or {}, node.get("id")
        spec = C.SPEC[kind]
        for key in props:
            if key not in spec["props"]:
                out.append(_finding("lint.unknown-prop", "warning", "Unknown prop %s.%s" % (kind, key), "The component ignores this prop.", nid, "Remove it or check the spelling."))
        if kind == "Tab" and (parent is None or parent["type"] != "Tabs"):
            out.append(_finding("lint.orphan-tab", "error", "Tab outside Tabs", "A Tab only renders inside a Tabs container.", nid, "Wrap it in Tabs."))
        if kind == "Tabs" and any(k["type"] != "Tab" for k in node.get("children") or []):
            out.append(_finding("lint.tabs-children", "error", "Tabs contains non-Tab children", "Only Tab nodes are rendered.", nid, "Wrap each child in a Tab."))
        if kind in C.CONTAINERS and kind not in ("Tab", "Form", "Generative", "Hero", "Page", "Card", "EmptyState", "Callout", "Insight") and not node.get("children"):
            out.append(_finding("lint.empty-container", "info", "Empty %s" % kind, "The container renders nothing.", nid, "Remove it or add content."))
        if kind in ("Tabs", "Disclosure", "Modal", "Drawer", "Tour") and C.is_auto_id(nid):
            out.append(_finding("lint.stateful-id", "info", "Stateful component without an explicit id", "%s keeps interface state; a stable id preserves it across re-renders." % kind, nid, "Call .id(\"…\")."))
        if kind == "Form":
            names: Dict[str, int] = {}
            for n, _, _ in C.walk(node):
                name = (n.get("props") or {}).get("name")
                if n is not node and isinstance(name, str) and n["type"] in INPUTS | CHECKS:
                    names[name] = names.get(name, 0) + 1
            for name, count in names.items():
                if count > 1:
                    out.append(_finding("lint.duplicate-name", "error", "Duplicate field name “%s”" % name, "%d fields share the name; only one value will be submitted." % count, nid, "Give each field a unique name."))
        if actions is not None:
            for event, binding in (node.get("on") or {}).items():
                if binding.get("action") not in actions:
                    out.append(_finding("lint.unknown-action", "error", "Unknown action “%s”" % binding.get("action"), "No handler is registered for this action.", nid, "Register the handler or fix the name."))
        for event in (node.get("on") or {}):
            if spec["events"] and event not in spec["events"]:
                out.append(_finding("lint.unknown-event", "warning", "%s never emits “%s”" % (kind, event), "Supported events: %s." % ", ".join(spec["events"]), nid, None))
    return _report(out, "structural")


def persona_walkthrough(scene: Node, persona: str) -> Dict[str, Any]:
    """Simulate a first visit by a described persona and report friction."""
    p = (persona or "").lower()
    traits = {
        "novice": bool(re.search(r"\b(new|novice|first[- ]time|beginner|non[- ]technical|unfamiliar)\b", p)),
        "hurried": bool(re.search(r"\b(busy|hurry|hurried|impatient|quick|rushed|executive|on the go)\b", p)),
        "mobile": bool(re.search(r"\b(mobile|phone|small screen|one[- ]handed|commut)", p)),
        "screenreader": bool(re.search(r"\b(screen ?reader|blind|voiceover|nvda|low vision)\b", p)),
        "keyboard": bool(re.search(r"\b(keyboard|power user|expert|developer|motor)\b", p)),
        "nonnative": bool(re.search(r"\b(non[- ]native|second language|esl|translat)", p)),
    }
    nodes = list(C.walk(scene))
    fields = [n for n, _, _ in nodes if n["type"] in INPUTS | CHECKS]
    required = [n for n in fields if (n.get("props") or {}).get("required")]
    primary = next((i for i, (n, _, _) in enumerate(nodes) if n["type"] == "Button" and (n.get("props") or {}).get("variant") == "primary"), None)
    copy = " ".join(str(v) for n, _, _ in nodes for k, v in (n.get("props") or {}).items() if k in ("title", "subtitle", "content", "body", "label", "description", "help", "text") and isinstance(v, str))
    grade = T.reading_grade(copy)
    out: List[Dict[str, Any]] = []
    if primary is None:
        out.append(_finding("persona.no-goal", "warning", "No obvious next step", "I cannot find a clearly primary action, so I am unsure how to finish.", scene.get("id"), "Mark one action as primary."))
    elif primary > 25 and (traits["hurried"] or traits["mobile"]):
        out.append(_finding("persona.buried-action", "warning", "The main action is far down", "I have to scroll past %d elements before I can act." % primary, nodes[primary][0].get("id"), "Move the primary action above the fold or make it sticky."))
    if len(fields) > 6 and (traits["hurried"] or traits["mobile"] or traits["novice"]):
        out.append(_finding("persona.effort", "warning", "This asks for a lot up front", "%d fields (%d required) is more than I want to fill in right now." % (len(fields), len(required)), None, "Ask only for what is needed now; defer the rest."))
    if grade > 9 and (traits["novice"] or traits["nonnative"]):
        out.append(_finding("persona.language", "warning", "The wording is hard to follow", "The copy reads at grade %.0f; I would need to re-read parts." % grade, None, "Apply plain-language mode (target grade 6–8)."))
    if traits["screenreader"]:
        for f in a11y_audit(scene)["findings"]:
            if f["severity"] == "error":
                out.append(_finding("persona." + f["id"], "error", f["title"], "With a screen reader this blocks me: " + f["detail"], f["target"], f["fix"]))
    if traits["keyboard"] and not any(n["type"] in ("IntentBar", "Search") or (n.get("props") or {}).get("kbd") for n, _, _ in nodes):
        out.append(_finding("persona.shortcuts", "info", "No keyboard accelerators", "I look for a command bar or shortcuts and find none.", None, "Add an IntentBar or shortcut hints."))
    if traits["mobile"]:
        wide = [n for n, _, _ in nodes if n["type"] == "Table" and len((n.get("props") or {}).get("columns") or []) > 5]
        for n in wide:
            out.append(_finding("persona.wide-table", "warning", "Table too wide for my screen", "%d columns will need sideways scrolling." % len(n["props"]["columns"]), n.get("id"), "Prioritise three columns and move the rest into a detail view."))
    if traits["novice"] and not any(n["type"] in ("Tour", "Callout", "EmptyState") or (n.get("props") or {}).get("help") for n, _, _ in nodes):
        out.append(_finding("persona.guidance", "info", "No guidance for a first visit", "Nothing explains what this screen is for.", None, "Add helper text or a short tour."))
    report = _report(out, "persona")
    active = [k for k, v in traits.items() if v] or ["general"]
    report["summary"] = "As %s (%s): %s" % (persona.strip() or "a typical user", ", ".join(active), report["summary"])
    return report


_SAMPLES = {"email": "ada@example.com", "password": "correct-horse-battery", "url": "https://example.com", "tel": "+1 415 555 0132",
            "number": "42", "date": "2027-01-15", "time": "09:30", "search": "invoice", "text": "Sample text"}


def synth_tests(scene: Node) -> List[Dict[str, Any]]:
    """Generate Autopilot scripts that exercise the scene's interactions."""
    cases: List[Dict[str, Any]] = []
    forms = [n for n, _, _ in C.walk(scene) if n["type"] == "Form"]
    for form in forms or [scene]:
        steps: List[Dict[str, Any]] = []
        for node, _, _ in C.walk(form):
            kind, props = node["type"], node.get("props") or {}
            if kind in ("Input", "TextArea", "Search"):
                steps.append({"do": "type", "target": node["id"], "value": _SAMPLES.get(str(props.get("kind") or "text"), "Sample text")})
            elif kind in ("Checkbox", "Toggle"):
                steps.append({"do": "click", "target": node["id"]})
            elif kind == "Select" and props.get("options"):
                first = props["options"][0]
                steps.append({"do": "select", "target": node["id"], "value": first.get("value", first.get("label")) if isinstance(first, dict) else first})
        submit = next((n for n, _, _ in C.walk(form) if n["type"] == "Button" and (n.get("props") or {}).get("variant") == "primary"), None)
        if submit is not None:
            steps.append({"do": "click", "target": submit["id"]})
            steps.append({"do": "expect", "target": submit["id"], "value": "event:%s" % ((submit.get("on") or {}).get("click", {}).get("action") or (form.get("on") or {}).get("submit", {}).get("action") or "submit")})
        if steps:
            cases.append({"name": "fills and submits %s" % (C.primary_text(form) or form["type"]).lower(), "steps": steps})
    for node, _, _ in C.walk(scene):
        if node["type"] == "Tabs" and len(node.get("children") or []) > 1:
            cases.append({"name": "switches tabs", "steps": [{"do": "click", "target": node["children"][1]["id"]},
                                                              {"do": "expect", "target": node["children"][1]["id"], "value": "visible"}]})
        if node["type"] == "Button" and node.get("on") and (node.get("props") or {}).get("variant") != "primary":
            cases.append({"name": "triggers %s" % (C.primary_text(node) or "action").lower(),
                          "steps": [{"do": "click", "target": node["id"]}, {"do": "expect", "target": node["id"], "value": "event:%s" % node["on"].get("click", {}).get("action", "")}]})
    return cases[:20]


_BANNED = {"simply": "Drop it; nothing is simple to everyone.", "just": "Usually removable.", "obviously": "If it were obvious it would not need saying.",
           "easy": "Describe the steps instead.", "easily": "Describe the steps instead.", "please": "Use sparingly; once per flow.",
           "oops": "Say what happened.", "whoops": "Say what happened.", "invalid": "Say what a correct value looks like.",
           "abort": "Prefer “cancel” or “stop”.", "kill": "Prefer “stop” or “end”.", "dummy": "Prefer “placeholder”."}
_TERMS = [("log in", "sign in"), ("login", "sign in"), ("log out", "sign out"), ("e-mail", "email"), ("username", "user name"),
          ("ok", "OK"), ("cancelled", "canceled")]


def voice_lint(texts: List[str], voice: str = "") -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    joined = " \n ".join(texts).lower()
    for i, text in enumerate(texts):
        low = text.lower()
        for word, why in _BANNED.items():
            if re.search(r"\b%s\b" % word, low):
                out.append(_finding("voice.word", "info", "Avoid “%s”" % word, "“%s” — %s" % (T.clip(text, 60), why), str(i), None))
        if text.count("!") > 0 and "playful" not in voice.lower():
            out.append(_finding("voice.exclaim", "info", "Exclamation mark", "“%s” — reserve exclamation marks for real celebration." % T.clip(text, 60), str(i), text.replace("!", ".")))
        if re.search(r"\b(was|were|been|is|are)\s+\w+ed\s+by\b", low):
            out.append(_finding("voice.passive", "info", "Passive voice", "“%s” — name who does what." % T.clip(text, 60), str(i), None))
        if len(text.split()) > 1 and text.isupper():
            out.append(_finding("voice.caps", "warning", "All capitals", "“%s” reads as shouting and is slower to scan." % T.clip(text, 60), str(i), T.sentence_case(text)))
        if text.strip().lower() in ("click here", "here"):
            out.append(_finding("voice.link", "warning", "Non-descriptive link", "Say where the link goes.", str(i), None))
    for a, b in _TERMS:
        if re.search(r"\b%s\b" % re.escape(a), joined) and re.search(r"\b%s\b" % re.escape(b.lower()), joined) and a != b.lower():
            out.append(_finding("voice.terms", "warning", "Mixed terminology", "Both “%s” and “%s” appear; choose one." % (a, b), None, "Use “%s” throughout." % b))
    return _report(out, "voice")


def perf_hints(scene: Node) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    st = C.stats(scene)
    if st["nodes"] > 1200:
        out.append(_finding("perf.nodes", "warning", "Very large scene", "%d nodes are sent on every update." % st["nodes"], None, "Paginate collections or move regions behind tabs."))
    if st["depth"] > 14:
        out.append(_finding("perf.depth", "info", "Deep nesting", "Depth %d adds layout cost and makes diffs larger." % st["depth"], None, "Flatten wrapper containers."))
    auto = 0
    for node, _, _ in C.walk(scene):
        kind, props = node["type"], node.get("props") or {}
        if kind == "Table" and isinstance(props.get("rows"), list) and len(props["rows"]) > 200 and not props.get("pageSize"):
            out.append(_finding("perf.table", "warning", "Unpaginated table", "%d rows render at once." % len(props["rows"]), node.get("id"), "Set pageSize to 25–50."))
        if kind == "Chart" and isinstance(props.get("data"), list) and len(props["data"]) > 600:
            out.append(_finding("perf.chart", "info", "Dense chart", "%d points exceed what the eye can separate." % len(props["data"]), node.get("id"), "Aggregate before plotting."))
        if kind == "Image" and not props.get("ratio"):
            out.append(_finding("perf.cls", "info", "Image without a ratio", "The layout will shift when the image loads.", node.get("id"), "Set ratio, e.g. 16:9."))
        if kind == "Generative" and props.get("auto", True):
            auto += 1
        auto += len(node.get("ai") or [])
    if auto > 30:
        out.append(_finding("perf.ai-fanout", "warning", "Many automatic AI bindings", "%d bindings may fire on load." % auto, None, "Trigger on interaction, or rely on the cache and request coalescing."))
    return _report(out, "performance")


def spacing_audit(scene: Node) -> Dict[str, Any]:
    out: List[Dict[str, Any]] = []
    gaps: Dict[str, int] = {}
    for node, _, parent in C.walk(scene):
        props = node.get("props") or {}
        if node["type"] in ("Stack", "Grid", "Row"):
            gap = str(props.get("gap") or "md")
            gaps[gap] = gaps.get(gap, 0) + 1
        if node["type"] == "Spacer":
            out.append(_finding("rhythm.spacer", "info", "Manual spacer", "Spacers bypass the spacing scale.", node.get("id"), "Use the parent's gap instead."))
        if parent is not None and parent["type"] in ("Stack", "Grid") and node["type"] in ("Stack", "Grid"):
            order = ["none", "xs", "sm", "md", "lg", "xl"]
            outer, inner = str((parent.get("props") or {}).get("gap") or "md"), str(props.get("gap") or "md")
            if order.index(inner) > order.index(outer):
                out.append(_finding("rhythm.inverted", "warning", "Inner gap larger than outer gap", "Related items (%s) sit further apart than unrelated groups (%s)." % (inner, outer), node.get("id"), "Make inner spacing tighter than outer spacing."))
    if len(gaps) > 4:
        out.append(_finding("rhythm.scale", "info", "Too many spacing steps", "%d different gaps are in use." % len(gaps), None, "Limit a screen to three steps of the scale."))
    return _report(out, "spacing")
