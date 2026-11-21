"""Adaptive Personalisation and Accessibility Intelligence capabilities."""
from __future__ import annotations

import re
from typing import Any, Dict

from .. import components as C
from ..reflex import behavior as B
from ..reflex import data as D
from ..reflex import review as R
from ..reflex import scene as S
from ..reflex import text as T
from .c_compose import scene_in
from .registry import DIRECTIVES, ITEMS, NOTE, REPORT, SCENE, TEXT, Ctx, cap, directives, fields, items, note, scene, FIELDS

EV = [{"t": n * 350, "kind": "click", "target": "save"} for n in range(5)] + \
     [{"t": 4000 + n * 600, "kind": "error", "target": "email"} for n in range(3)]


def _ev(i: Dict[str, Any], c: Ctx):
    return i.get("events") or c.signals


cap("adapt.expertise", "Expertise Sensing",
    "Infers whether someone is a novice, intermediate or expert from how they interact, and adapts hints and density.",
    why="One interface cannot serve first-day and thousandth-day users unless it knows which is present.",
    do="From the interaction profile classify expertise as novice, intermediate or expert and return adaptation directives with reasons.",
    inp={"events?": ["any"]}, out=DIRECTIVES, present="observe", consent="personalization", ex={"events": EV},
    facts=lambda i, c: B.profile(_ev(i, c)), reflex=lambda i, c: directives(B.expertise(_ev(i, c))))

cap("adapt.frustration", "Frustration Radar",
    "Detects rage clicks, repeated errors and back-and-forth navigation, then offers help at the point of friction.",
    why="Frustrated users rarely file tickets; they leave. The interface can notice first.",
    do="From the interaction profile judge whether the person is calm, struggling or frustrated; return directives that relieve the specific friction.",
    inp={"events?": ["any"]}, out=DIRECTIVES, present="observe", consent="personalization", ex={"events": EV},
    facts=lambda i, c: B.profile(_ev(i, c)), reflex=lambda i, c: directives(B.frustration(_ev(i, c))))

cap("adapt.predict_focus", "Predictive Focus",
    "Predicts the next control a person will use so the app can pre-focus, prefetch or pre-warm it.",
    why="The fastest interaction is the one the interface prepared for.",
    do="Rank the most likely next targets from the action sequence, with a probability-like score for each.",
    inp={"events?": ["any"], "candidates?": ["str"]}, out=ITEMS, present="observe", consent="personalization",
    ex={"events": [{"t": n, "kind": "click", "target": t} for n, t in enumerate("list open edit list open edit list open".split())]},
    reflex=lambda i, c: items(B.predict_focus(_ev(i, c), i.get("candidates"))))

cap("adapt.nav_reorder", "Behavioural Navigation",
    "Reorders navigation by each person's actual frequency and recency of use.",
    why="Static menus optimise for the org chart; people need their own top five.",
    do="Order the navigation items by observed use, most valuable first, noting the evidence for each.",
    inp={"items": ["str"], "events?": ["any"]}, out=ITEMS, present="observe", binds=["Shell"], consent="personalization",
    ex={"items": ["Overview", "Orders", "Reports"], "events": [{"t": 1, "kind": "nav", "target": "Reports"}, {"t": 2, "kind": "nav", "target": "Reports"}, {"t": 3, "kind": "nav", "target": "Orders"}]},
    reflex=lambda i, c: items(B.nav_reorder(i["items"], _ev(i, c))))

cap("adapt.cognitive_load", "Cognitive Load Governor",
    "Estimates how demanding a screen is right now and proposes what to collapse or highlight.",
    why="Density that helps an expert at 10am overwhelms the same person mid-incident.",
    do="Estimate cognitive load as clear, busy or overloaded from scene statistics and hesitation signals; return directives to reduce it.",
    inp={"events?": ["any"], "scene?": "any"}, out=DIRECTIVES, present="observe", uses_scene=True, ex={"events": EV},
    facts=lambda i, c: {"scene": C.stats(scene_in(i, c)), "profile": B.profile(_ev(i, c))},
    reflex=lambda i, c: directives(B.cognitive_load(C.stats(scene_in(i, c)), _ev(i, c))))

cap("adapt.preferences", "Preference Distillation",
    "Learns stable preferences — theme, density, view, input style — from choices made during use.",
    why="Settings pages are where preferences go to be forgotten; behaviour already states them.",
    do="Derive durable preferences from repeated choices in the signals. Return one directive per preference with its evidence.",
    inp={"events?": ["any"]}, out=DIRECTIVES, present="observe", consent="personalization",
    ex={"events": [{"t": 1, "kind": "click", "target": "theme", "meta": "theme:dark"}, {"t": 2, "kind": "click", "target": "density", "meta": "density:compact"}]},
    reflex=lambda i, c: directives(B.preferences(_ev(i, c))))


def _lens(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    sc, role = scene_in(i, c), (i.get("role") or "").lower()
    ranked = S.priorities(sc)
    want = {"executive": ("Stat", "Chart", "Insight"), "engineer": ("Table", "Code", "Timeline", "KeyValue"),
            "support": ("Thread", "List", "Timeline", "Form"), "finance": ("Table", "Stat", "Chart")}
    prefer = next((v for k, v in want.items() if k in role), ("Stat", "Table"))
    by_id = {n["id"]: n for n in sc.get("children") or []}
    order = sorted(ranked, key=lambda r: (0 if any(t["type"] in prefer for t, _, _ in C.walk(by_id[r["id"]])) else 1, -r["score"]))
    kids = [by_id[r["id"]] for r in order]
    lead = S.N("Callout", title="View for %s" % (i.get("role") or "you"), body="Reordered to lead with %s." % ", ".join(prefer).lower(), tone="ai")
    return scene(S.N(sc["type"] if sc["type"] in C.CONTAINERS else "Page", lead, *kids, **(sc.get("props") or {})),
                 "Same content, resequenced for what a %s looks at first." % (i.get("role") or "reader"))


cap("adapt.role_lens", "Role Lens",
    "Reframes one screen for different readers — an executive summary, an engineer's detail, a support view.",
    why="The same data answers different questions for different roles; building each view by hand does not scale.",
    do="Recompose the scene for the given role: lead with what that role decides on, demote the rest. Keep all data accurate; add nothing new.",
    inp={"role": "str", "scene?": "any"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"], uses_scene=True, max_out=2600,
    ex={"role": "executive", "scene": {"type": "Page", "props": {"title": "Incident 42"}, "children": [
        {"type": "Code", "props": {"source": "trace…"}}, {"type": "Stat", "props": {"label": "Customers affected", "value": "312"}}]}},
    reflex=_lens)

cap("adapt.reading_level", "Reading-Level Adaptation",
    "Rewrites copy to a target reading level while keeping every fact.",
    why="Half of adults read below grade 8; most product copy is written above it.",
    do="Rewrite the text at the target grade level. Short sentences, common words, same facts and numbers.",
    inp={"text": "str", "grade?": "int"}, out=TEXT, present="transform", binds=["Text", "Markdown", "Callout"], untrusted=["text"],
    ex={"text": "In order to utilize the export functionality, you must authenticate prior to initiating the request.", "grade": 6},
    reflex=lambda i, c: {"text": T.simplify(i["text"]), "rationale": "Grade %.1f → %.1f." % (T.reading_grade(i["text"]), T.reading_grade(T.simplify(i["text"])))})

_FMT = {"US": ("MM/DD/YYYY", "1,234.56", "12-hour", "$1,234.56", "Sunday"), "GB": ("DD/MM/YYYY", "1,234.56", "24-hour", "£1,234.56", "Monday"),
        "DE": ("DD.MM.YYYY", "1.234,56", "24-hour", "1.234,56 €", "Monday"), "FR": ("DD/MM/YYYY", "1 234,56", "24-hour", "1 234,56 €", "Monday"),
        "JP": ("YYYY/MM/DD", "1,234.56", "24-hour", "¥1,235", "Sunday"), "BR": ("DD/MM/YYYY", "1.234,56", "24-hour", "R$ 1.234,56", "Sunday"),
        "ES": ("DD/MM/YYYY", "1.234,56", "24-hour", "1.234,56 €", "Monday"), "IN": ("DD-MM-YYYY", "1,23,456.78", "12-hour", "₹1,23,456.78", "Sunday")}


def _locale(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    region = (i.get("locale") or c.locale).split("-")[-1].upper()
    f = _FMT.get(region, _FMT["US"])
    return {"fields": [{"name": n, "value": v, "confidence": 0.9 if region in _FMT else 0.4} for n, v in
                       zip(("dateFormat", "numberFormat", "clock", "currencyExample", "weekStart"), f)],
            "notes": "Conventions for %s." % region}


cap("adapt.locale_morph", "Locale Morph",
    "Adapts dates, numbers, currency, clock and week start to a locale's conventions.",
    why="Translation without format adaptation still reads as foreign — and 03/04 is a real bug.",
    do="Return the conventions for the locale as fields: dateFormat, numberFormat, clock, currencyExample, weekStart.",
    inp={"locale": "str"}, out=FIELDS, present="service", ex={"locale": "de-DE"}, reflex=_locale)


def _time_ctx(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    h = c.now.hour
    part = "morning" if h < 12 else ("afternoon" if h < 18 else "evening")
    name = i.get("name")
    plan = {"morning": "Start with what changed overnight.", "afternoon": "Here is what still needs attention today.",
            "evening": "A short wrap-up before you finish."}[part]
    bullets = [str(x) for x in (i.get("items") or [])][:4]
    return note("Good %s%s" % (part, ", " + name if name else ""), plan, bullets, 0.8, "info")


cap("adapt.time_context", "Time-Aware Surfaces",
    "Frames a screen for the time of day: a morning briefing, an afternoon focus list, an evening wrap-up.",
    why="The same dashboard means different things at 9am and 6pm.",
    do="Write a short greeting and one-line framing appropriate to the local time, then list the given items in the most useful order.",
    inp={"name?": "str", "items?": ["str"]}, out=NOTE, present="annotate", binds=["Page", "Hero", "Card"],
    ex={"name": "Mira", "items": ["3 invoices overdue", "Renewal call at 14:00"]}, reflex=_time_ctx)


def _density(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    st = C.stats(scene_in(i, c))
    ctx = (i.get("context") or "").lower()
    mode = "compact" if (st["nodes"] > 120 or re.search(r"(monitor|trading|ops|power|desktop|wide)", ctx)) else (
        "spacious" if (st["nodes"] < 25 or re.search(r"(touch|mobile|kiosk|novice|reading)", ctx)) else "comfortable")
    return {"state": mode, "confidence": 0.7, "directives": [{"kind": "density", "target": None, "value": mode,
            "reason": "%d elements on screen%s." % (st["nodes"], (" and context “%s”" % i["context"]) if i.get("context") else "")}]}


cap("adapt.density", "Density Morphing",
    "Chooses compact, comfortable or spacious density from content volume, input mode and context.",
    why="Density is not a preference toggle; it depends on the task, the device and the amount of data.",
    do="Choose compact, comfortable or spacious for this scene and context, with the reason.",
    inp={"context?": "str", "scene?": "any"}, out=DIRECTIVES, present="theme", uses_scene=True, ex={"context": "touch kiosk"}, reflex=_density)


def _focus(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    sc, task = scene_in(i, c), i.get("task") or ""
    kids = sc.get("children") or []
    if not kids:
        return {"keep": [], "hide": [], "rationale": "Nothing to hide."}
    hits = {h["index"]: h["score"] for h in D.search(task, [" ".join(C.primary_text(n) + " " + n["type"] for n, _, _ in C.walk(k)) for k in kids], len(kids))}
    keep = [k["id"] for idx, k in enumerate(kids) if hits.get(idx, 0) > 0.05] or [S.priorities(sc)[0]["id"]]
    return {"keep": keep, "hide": [k["id"] for k in kids if k["id"] not in keep],
            "rationale": "Kept the %d region%s related to “%s”." % (len(keep), "" if len(keep) == 1 else "s", task)}


cap("adapt.focus_mode", "Focus Mode",
    "Hides everything unrelated to the task at hand and brings it back on request.",
    why="Attention is the scarcest resource on any screen.",
    do="Given the task, return the ids of top-level regions to keep and to hide. Use only ids from the scene.",
    inp={"task": "str", "scene?": "any"}, out={"keep": ["str"], "hide": ["str"], "rationale": "str"}, present="service", uses_scene=True,
    ex={"task": "update billing address", "scene": {"type": "Page", "props": {"title": "Account"}, "children": [
        {"type": "Card", "id": "billing", "props": {"title": "Billing address"}}, {"type": "Card", "id": "team", "props": {"title": "Team members"}}]}},
    reflex=_focus)


def _resume(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    changes = [str(x) for x in (i.get("changes") or [])]
    mins = float(i.get("awayMinutes") or 0)
    away = "%d min" % mins if mins < 90 else "%.0f h" % (mins / 60)
    ranked = sorted(changes, key=lambda t: -B.priority_of(t)[1])
    return note("While you were away (%s)" % away, "%d thing%s changed; the most important is first." % (len(changes), "" if len(changes) == 1 else "s")
                if changes else "Nothing changed.", ranked[:4], 0.75, "info")


cap("adapt.resume", "Session Resume Brief",
    "Summarises what changed while someone was away and where they left off.",
    why="Returning to a tool costs minutes of re-orientation; a brief makes it seconds.",
    do="Write a two-line brief of what changed while the person was away, most important first, as up to four bullets.",
    inp={"changes": ["str"], "awayMinutes?": "num"}, out=NOTE, present="annotate", binds=["Page", "Card"],
    ex={"changes": ["Invoice #204 was paid", "Payment failed for Globex", "2 new comments on the Q3 plan"], "awayMinutes": 95}, reflex=_resume)

# --- accessibility ------------------------------------------------------------
cap("access.alt_text", "Alt-Text Author",
    "Writes concise, purposeful alternative text for images, using vision when an image is supplied.",
    why="Most images on the web ship without alt text because writing it is nobody's job.",
    do="Write alt text under 125 characters that conveys the image's purpose in context. No “image of”. Return an empty string if it is decorative.",
    inp={"image?": "str", "context?": "str", "filename?": "str"}, out={"alt": "str", "decorative": "bool", "confidence": "num"},
    present="transform", binds=["Image"], vision=True, max_out=160, ex={"filename": "team-offsite-2026.jpg", "context": "About us page"},
    reflex=lambda i, c: {"alt": T.sentence_case(re.sub(r"[-_]+", " ", re.sub(r"\.\w+$", "", (i.get("filename") or "").rsplit("/", 1)[-1])))
                         or T.clip(i.get("context") or "", 80), "decorative": not (i.get("filename") or i.get("context")), "confidence": 0.35})

cap("access.label_audit", "Accessible Name Synthesis",
    "Finds controls without an accessible name and proposes one for each.",
    why="An unlabeled control is invisible to assistive technology; fixing it should be one click.",
    do="For every control in the scene without a label, propose a short accessible name. Return the element id as name and the label as value.",
    inp={"scene?": "any"}, out=FIELDS, present="audit", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Search"}, "children": [{"type": "Input", "id": "q", "props": {"name": "query", "placeholder": "Search orders…"}},
                                                                         {"type": "Button", "id": "go", "props": {"label": "", "icon": "search"}}]}},
    reflex=lambda i, c: fields(R.synth_labels(scene_in(i, c)), "Proposed names for unlabeled controls."))

cap("access.plain_language", "Plain-Language Mode",
    "Rewrites interface copy in plain language: common words, short sentences, active voice.",
    why="Plain language is an accessibility requirement and a conversion tactic at once.",
    do="Rewrite in plain language. Keep meaning, names and numbers. Prefer short active sentences.",
    inp={"text": "str"}, out=TEXT, present="transform", binds=["Text", "Markdown", "Callout", "Banner"], untrusted=["text"],
    ex={"text": "Subsequently, numerous users were unable to authenticate due to the fact that the configuration was erroneous."},
    reflex=lambda i, c: {"text": T.simplify(i["text"], 16), "rationale": "Replaced formal vocabulary and shortened sentences."})


def _narrate(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    sc = scene_in(i, c)
    st = C.stats(sc)["byType"]
    parts = ["%s." % (C.primary_text(sc) or "Untitled screen")]
    for kind, phrase in (("Stat", "%d key figure%s"), ("Table", "%d table%s"), ("Chart", "%d chart%s"), ("Form", "%d form%s"), ("Button", "%d action%s")):
        if st.get(kind):
            parts.append(phrase % (st[kind], "" if st[kind] == 1 else "s"))
    primary = next((C.primary_text(n) for n, _, _ in C.walk(sc) if n["type"] == "Button" and (n.get("props") or {}).get("variant") == "primary"), "")
    text = parts[0] + (" It has " + ", ".join(parts[1:]) + "." if len(parts) > 1 else "") + (" The main action is “%s”." % primary if primary else "")
    return {"text": text, "rationale": "Orientation first, then structure, then the main action."}


cap("access.narrate", "Screen Narration",
    "Produces a short spoken-style orientation of a screen: what it is, what it contains, what to do first.",
    why="Screen-reader users hear a page linearly; a ten-second overview restores the glance sighted users get.",
    do="Write a spoken overview in under 60 words: the screen's purpose, its main regions and the primary action.",
    inp={"scene?": "any"}, out=TEXT, present="media", uses_scene=True, binds=["Page"],
    ex={"scene": {"type": "Page", "props": {"title": "Invoices"}, "children": [{"type": "Table", "props": {"rows": [], "columns": []}},
                                                                             {"type": "Button", "props": {"label": "New invoice", "variant": "primary"}}]}},
    reflex=_narrate)

cap("access.focus_order", "Focus Order Reasoner",
    "Computes a logical keyboard focus order: dialogs first, reading order next, primary action last in its group.",
    why="Tab order silently breaks whenever layout changes; it should be derived, not maintained.",
    do="Return interactive elements in the order keyboard focus should visit them, using ids from the scene.",
    inp={"scene?": "any"}, out=ITEMS, present="service", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "T"}, "children": [{"type": "Input", "id": "a", "props": {"name": "a", "label": "A"}},
                                                                       {"type": "Button", "id": "b", "props": {"label": "Go", "variant": "primary"}}]}},
    reflex=lambda i, c: items(R.focus_order(scene_in(i, c))))

cap("access.linearize", "Step-by-Step Linearizer",
    "Restructures a dense screen into a single-column, one-thing-at-a-time sequence.",
    why="Cognitive accessibility often means the same content, one decision at a time.",
    do="Recompose the scene as ordered steps, each a titled section with the original controls. Keep every field and action.",
    inp={"scene?": "any"}, out=SCENE, present="compose", tier="balanced", uses_scene=True, binds=["Generative"], max_out=2600,
    ex={"scene": {"type": "Page", "props": {"title": "Profile"}, "children": [
        {"type": "Card", "props": {"title": "Identity"}, "children": [{"type": "Input", "props": {"name": "name", "label": "Name"}}]},
        {"type": "Card", "props": {"title": "Contact"}, "children": [{"type": "Input", "props": {"name": "email", "label": "Email"}}]}]}},
    reflex=lambda i, c: scene(*S.linearize(scene_in(i, c))))

cap("access.captions", "Live Captions",
    "Cleans raw speech-to-text into readable captions with punctuation and speaker turns.",
    why="Raw transcripts are technically captions and practically unreadable.",
    do="Turn the raw transcript into caption lines of at most 12 words with punctuation. Do not add or remove meaning.",
    inp={"transcript": "str"}, out={"lines": ["str"]}, present="media", untrusted=["transcript"], consent="microphone",
    ex={"transcript": "so today we are going to look at the new invoice flow and then um talk about what is next"},
    reflex=lambda i, c: {"lines": [T.sentence_case(" ".join(w)) for w in (lambda ws: [ws[k:k + 10] for k in range(0, len(ws), 10)])(
        [w for w in (i.get("transcript") or "").split() if w.lower() not in ("um", "uh", "er", "like")])]})

cap("access.audit", "Accessibility Audit",
    "Audits a scene against WCAG 2.2 success criteria and proposes a fix for every finding.",
    why="Accessibility regressions are cheapest to catch before a screen ships.",
    do="Audit the scene for accessibility barriers. Reference the WCAG criterion in each finding id, target the element id and give a concrete fix.",
    inp={"scene?": "any"}, out=REPORT, present="audit", tier="balanced", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Gallery"}, "children": [{"type": "Image", "props": {"src": "/a.png"}},
                                                                           {"type": "Link", "props": {"label": "click here", "href": "/x"}}]}},
    facts=lambda i, c: R.a11y_audit(scene_in(i, c)), reflex=lambda i, c: R.a11y_audit(scene_in(i, c)))


def _dys(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    sents = T.sentences(T.simplify(i.get("text") or "", 14))
    return {"text": "\n".join("• " + s for s in sents), "rationale": "One idea per line, short sentences, no dense paragraphs."}


cap("access.readability", "Readability Restructure",
    "Reformats dense paragraphs into short, scannable lines suited to readers with dyslexia or attention differences.",
    why="Walls of text exclude more people than low contrast does.",
    do="Restructure the text as short bullet lines, one idea each, in plain words. Keep all facts.",
    inp={"text": "str"}, out=TEXT, present="transform", binds=["Text", "Markdown"], untrusted=["text"],
    ex={"text": "Your subscription renews automatically on the first of each month, and you can cancel at any time from the billing page, which also lists past invoices."},
    reflex=_dys)


def _motion(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    sc = scene_in(i, c)
    flagged = [n for n, _, _ in C.walk(sc) if n["type"] in ("StreamText", "Thinking", "Skeleton", "Tour") or (n.get("props") or {}).get("indeterminate")]
    return {"state": "reduce" if flagged else "ok", "confidence": 0.8,
            "directives": [{"kind": "reduce_motion", "target": n["id"], "value": "static", "reason": "%s animates continuously." % n["type"]} for n in flagged[:8]]}


cap("access.motion", "Motion Sensitivity Advisor",
    "Finds continuous or large motion in a scene and specifies calmer equivalents for reduced-motion users.",
    why="Vestibular disorders make some animation physically unpleasant; alternatives must be designed, not just disabled.",
    do="List elements whose motion should be reduced and what to replace it with.",
    inp={"scene?": "any"}, out=DIRECTIVES, present="service", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Loading"}, "children": [{"type": "Skeleton", "id": "sk"}, {"type": "Progress", "id": "p", "props": {"value": 0, "indeterminate": True}}]}},
    reflex=_motion)


def _desc_chart(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    f = D.facts(i.get("data") or [], i.get("x") or "", i.get("y") or "")
    if not f.get("count"):
        return {"text": "An empty chart.", "rationale": "No data."}
    return {"text": "%s chart of %s by %s with %d points, from %s to %s. Highest %s at %s; lowest %s at %s. Overall trend: %s." % (
        (i.get("kind") or "bar").capitalize(), f["y"], f["x"], f["count"], D.fmt(f["first"], f["format"]), D.fmt(f["last"], f["format"]),
        D.fmt(f["max"]["value"], f["format"]), f["max"]["label"], D.fmt(f["min"]["value"], f["format"]), f["min"]["label"], f["trend"]),
        "rationale": "Structure, range, extremes and trend — the same reading order as a sighted glance."}


cap("access.describe_chart", "Chart Description",
    "Writes the text alternative for a chart: its type, range, extremes and trend, computed from the data.",
    why="A chart without a description is a blank rectangle to a screen reader.",
    do="Describe the chart for someone who cannot see it using only the supplied facts: type, axes, range, extremes, trend.",
    inp={"data": ["any"], "kind?": "str", "x?": "str", "y?": "str"}, out=TEXT, present="annotate", binds=["Chart"],
    ex={"kind": "line", "data": [{"m": "Jan", "v": 10}, {"m": "Feb", "v": 14}, {"m": "Mar", "v": 19}], "x": "m", "y": "v"},
    facts=lambda i, c: D.facts(i.get("data") or [], i.get("x") or "", i.get("y") or ""), reflex=_desc_chart)
