"""Design-System Intelligence and Data & Visualisation Intelligence capabilities."""
from __future__ import annotations

import re
from typing import Any, Dict

from .. import colors as K
from .. import components as C
from ..reflex import data as D
from ..reflex import design as G
from ..reflex import review as R
from ..reflex import scene as S
from ..reflex import text as T
from .c_compose import scene_in
from .registry import ITEMS, NOTE, REPORT, SCENE, Ctx, cap, items, note, scene, texts_of

THEME = {"name": "str", "brand": "str", "accent": "str", "dark": "bool", "radius": "int",
         "font": "enum:sans|serif|mono|rounded", "density": "enum:compact|comfortable|spacious", "rationale": "str"}
ROWS = [{"month": m, "revenue": v, "orders": o} for m, v, o in
        zip(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"], [42000, 44500, 47100, 49800, 81000, 54200, 57900], [310, 322, 341, 350, 512, 371, 389])]


def with_tokens(out: Dict[str, Any], i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    """Post-processor: expand brand intent into the full contrast-verified token list."""
    out["tokens"] = G.expand_theme(out)
    return out


cap("design.theme_prompt", "Theme-from-Prompt",
    "Generates a complete, contrast-verified theme from a description such as “calm fintech at night”.",
    why="A theme is forty coupled decisions; a sentence should be enough to make all of them coherently.",
    do="Choose brand and accent colours (hex), light or dark scheme, corner radius (0–24), font family and density that express the description.",
    inp={"prompt": "str"}, out=THEME, present="theme", binds=["Page", "Shell"], post=with_tokens, max_out=300,
    ex={"prompt": "calm fintech at night"}, reflex=lambda i, c: G.theme_from_prompt(i["prompt"]))

cap("design.brand_extract", "Brand Extraction",
    "Derives a theme from a brand description or a logo/screenshot (vision): dominant hue, accent, personality.",
    why="Matching a customer's brand is the first request in every white-label deal.",
    do="Infer the brand's primary and accent colours (hex), scheme, radius, font family and density from the description or image.",
    inp={"description?": "str", "image?": "str"}, out=THEME, present="theme", vision=True, post=with_tokens, max_out=300,
    ex={"description": "Tidewater Coffee — warm, friendly, round, brand colour #7a4b2a"},
    reflex=lambda i, c: G.theme_from_prompt(i.get("description") or "brand"))

cap("design.palette", "Palette Harmonizer",
    "Expands one seed colour into an 11-step perceptual ramp plus complementary, analogous and triadic harmonies.",
    why="Ramps built in HSL have uneven steps; OKLCH ramps look even and keep contrast predictable.",
    inp={"seed": "str"},
    out={"ramp": [{"step": "str", "value": "str"}], "complementary": "str", "analogous": ["str"], "triadic": ["str"], "neutral": "str"},
    present="theme", ex={"seed": "#2f6bff"}, direct=lambda i, c: G.harmonies(i["seed"]))

cap("design.contrast_heal", "Contrast Healer",
    "Checks text/background pairs against WCAG and repairs failures by shifting lightness while preserving hue.",
    why="Contrast failures are the most common accessibility defect and the most mechanical to fix.",
    inp={"pairs": [{"fg": "str", "bg": "str", "name?": "str", "target?": "num"}]},
    out={"pairs": [{"name": "str", "fg": "str", "bg": "str", "ratio": "num", "fixed": "str", "fixedRatio": "num", "passes": "bool", "note": "str"}]},
    present="theme", ex={"pairs": [{"name": "muted on white", "fg": "#9db8ff", "bg": "#ffffff"}]},
    direct=lambda i, c: {"pairs": G.heal_pairs(i["pairs"])})

cap("design.dark_mode", "Dark-Mode Derivation",
    "Derives a dark theme from a light brand: re-tuned surfaces, lifted brand colour, verified contrast — not inversion.",
    why="Inverting colours produces muddy, low-contrast dark modes; derivation keeps the brand recognisable.",
    inp={"brand": "str", "accent?": "str", "radius?": "int"}, out={"tokens": [{"name": "str", "value": "str"}], "rationale": "str"},
    present="theme", ex={"brand": "#2f6bff"},
    direct=lambda i, c: {"tokens": K.theme_tokens(i["brand"], i.get("accent") or "", True, int(i.get("radius") or 12)),
                         "rationale": "Surfaces tinted toward the brand hue; brand lifted two ramp steps; all text pairs verified at 4.5:1."})


def _mood(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    label, score = T.sentiment(i.get("text") or "")
    hue = {"positive": "#1f9d6b", "negative": "#c2542d", "neutral": "#2f6bff"}[label]
    return {"name": "%s mood" % label.capitalize(), "brand": hue, "accent": "", "dark": False, "radius": 14 if label == "positive" else 10,
            "font": "sans", "density": "spacious" if label == "negative" else "comfortable",
            "rationale": "Content reads as %s (%.2f); accent and spacing adjusted to match." % (label, score)}


cap("design.mood", "Mood Shift",
    "Tunes accent, radius and spacing to the emotional tone of the content on screen.",
    why="A celebration and an outage should not look identical.",
    do="Read the emotional tone of the text and choose brand colour (hex), radius, font and density that suit it. Stay subtle.",
    inp={"text": "str"}, out=THEME, present="theme", post=with_tokens, untrusted=["text"], max_out=300,
    ex={"text": "Great news — the migration finished early and everything works perfectly."}, reflex=_mood)

cap("design.type_pair", "Type Pairing",
    "Recommends heading and body font stacks and a modular scale for a described mood, using system-safe fonts.",
    why="Typography sets tone before a single word is read; pairing is a learned craft.",
    do="Recommend heading and body font stacks (CSS font-family values), a modular scale ratio and the reason.",
    inp={"mood": "str"}, out={"mood": "str", "heading": "str", "body": "str", "scale": "num", "why": "str"}, present="theme",
    ex={"mood": "editorial and authoritative"}, reflex=lambda i, c: G.type_pair(i["mood"]))


def _token_lint(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    out = []
    for v in i.get("values") or []:
        if K.is_hex(v):
            near = G.nearest_token(v)
            out.append(R._finding("tokens.raw-colour", "warning" if near["distance"] > 0.02 else "info", "Raw colour %s" % v,
                                  "Hard-coded colours drift from the theme.", None, "Use var(%s) (distance %.3f)." % (near["token"], near["distance"])))
        elif isinstance(v, str) and re.fullmatch(r"\d+px", v) and int(v[:-2]) % 4:
            out.append(R._finding("tokens.off-grid", "info", "Off-grid size %s" % v, "Sizes should sit on the 4px grid.", None,
                                  "Use %dpx." % (round(int(v[:-2]) / 4) * 4)))
    return R._report(out, "token")


cap("design.token_lint", "Token Linter",
    "Flags hard-coded colours and off-grid sizes and maps each to the nearest design token.",
    why="Design systems erode one hex code at a time.",
    inp={"values": ["str"]}, out=REPORT, present="audit", ex={"values": ["#2e6bfe", "13px", "16px"]}, direct=_token_lint)

cap("design.icon_match", "Semantic Icon Match",
    "Chooses the icon whose meaning best fits a label or action.",
    why="Icon choice by filename search yields inconsistent metaphors across a product.",
    do="Pick up to three icons from the icon set whose meaning best matches the text. Use exact icon names as value.",
    inp={"text": "str"}, out=ITEMS, present="suggest", binds=["Button", "Icon", "Stat"], facts=lambda i, c: {"icons": sorted(G.ICONS)},
    ex={"text": "Send invoice reminder"}, reflex=lambda i, c: items(G.match_icon(i["text"])))

cap("design.voice_lint", "Voice & Tone Lint",
    "Checks interface copy against a voice guide: banned words, shouting, passive voice, mixed terminology.",
    why="Voice consistency is a brand asset that no one has time to police by hand.",
    do="Review the copy against the voice description. Report each issue with the offending text and a rewrite.",
    inp={"texts?": ["str"], "voice?": "str", "scene?": "any"}, out=REPORT, present="audit", uses_scene=True,
    ex={"texts": ["Simply click here!", "LOG IN TO CONTINUE", "Sign in"]},
    reflex=lambda i, c: R.voice_lint(i.get("texts") or texts_of(scene_in(i, c)), i.get("voice") or ""))

cap("design.motion", "Motion Choreographer",
    "Specifies duration, easing and movement for a transition from what the change means.",
    why="Motion communicates causality; arbitrary durations communicate nothing.",
    do="Specify motion for the described change: kind, duration in ms, CSS easing, movement, and a reduced-motion alternative.",
    inp={"intent": "str"},
    out={"kind": "str", "durationMs": "int", "easing": "str", "movement": "str", "reducedMotion": "str", "rationale": "str"},
    present="service", ex={"intent": "row deleted from table"}, reflex=lambda i, c: G.choreograph(i["intent"]))

cap("design.illustrate", "Generative Illustration",
    "Creates on-brand illustrations for empty states, heroes and placeholders — via the image model, or procedurally offline.",
    why="Stock art dilutes a brand; bespoke art for every state was never affordable.",
    inp={"prompt": "str", "width?": "int", "height?": "int", "brand?": "str"}, out={"url": "str", "alt": "str", "source": "str"},
    present="media", binds=["Image", "Hero", "EmptyState"], ex={"prompt": "calm ocean waves"},
    direct=lambda i, c: (c.kernel.media.image(i, c) if c.kernel else
                         {"url": G.illustrate(i["prompt"], int(i.get("width") or 640), int(i.get("height") or 360), i.get("brand") or ""),
                          "alt": "Abstract illustration: %s" % i["prompt"], "source": "procedural"}))

cap("design.semantic_color", "Semantic Colour Assignment",
    "Assigns status tones to labels by meaning: “overdue” is danger, “pending” is warning, “paid” is success.",
    why="Status colours chosen ad hoc end up contradicting each other across screens.",
    do="Assign each label one tone: success, warning, danger, info or neutral, by what the status means to the user.",
    inp={"labels": ["str"]}, out=ITEMS, present="service", binds=["Badge", "Table"], ex={"labels": ["Paid", "Overdue", "Pending", "Draft"]},
    reflex=lambda i, c: items([{"label": lab, "value": G.semantic_tone(lab), "score": 0.8} for lab in i["labels"]]))

cap("design.spacing", "Rhythm & Spacing Advisor",
    "Audits spacing rhythm: inner gaps larger than outer gaps, too many scale steps, manual spacers.",
    why="Consistent rhythm is what makes a layout feel designed; it is also easy to check mechanically.",
    do="Audit the scene's spacing for rhythm problems and give a specific fix for each.",
    inp={"scene?": "any"}, out=REPORT, present="audit", uses_scene=True,
    ex={"scene": {"type": "Stack", "props": {"gap": "sm"}, "children": [{"type": "Stack", "props": {"gap": "xl"}, "children": [{"type": "Text", "props": {"content": "a"}}]}, {"type": "Spacer"}]}},
    reflex=lambda i, c: R.spacing_audit(scene_in(i, c)))

# --- data -----------------------------------------------------------------------
CHART = {"kind": "enum:bar|line|area|donut|scatter|table", "x": "str", "y": ["str"], "rationale": "str", "confidence": "num"}

cap("data.chart_choose", "Chart Chooser",
    "Selects the chart form that answers the question for the shape of the data.",
    why="The wrong chart hides the answer; choosing well requires knowing both the data and the question.",
    do="Choose the chart kind and the x and y keys that best answer the question, using the column types in facts.",
    inp={"data": ["any"], "question?": "str"}, out=CHART, present="service", binds=["Chart"],
    ex={"data": ROWS, "question": "how is revenue trending?"},
    facts=lambda i, c: {"columns": D.column_types(i["data"])}, reflex=lambda i, c: D.choose_chart(i["data"], i.get("question") or ""))

cap("data.insights", "Insight Captions",
    "Writes the takeaway for a dataset or chart, grounded in statistics the engine computed.",
    why="A chart shows; a caption tells. Most dashboards ship without the telling.",
    do="State the single most important takeaway and up to four supporting points using only the numbers in facts.",
    inp={"data": ["any"], "x?": "str", "y?": "str"}, out=NOTE, present="annotate", binds=["Chart", "Table"], ex={"data": ROWS},
    facts=lambda i, c: D.facts(i["data"], i.get("x") or "", i.get("y") or ""),
    reflex=lambda i, c: D.insights(i["data"], i.get("x") or "", i.get("y") or ""))


def _off_trend(value: float, expected: float) -> str:
    if not expected:
        return "far above" if value > 0 else "far below"
    change = (value - expected) / abs(expected) * 100
    return "%d%% %s" % (round(abs(change)), "above" if change > 0 else "below")


def _anom(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    f = D.facts(i["data"], i.get("x") or "", i.get("y") or "")
    vals = [D.to_number(r.get(f["y"])) for r in i["data"]]
    found = D.anomalies(vals, [str(r.get(f["x"])) for r in i["data"]])  # type: ignore[arg-type]
    return {"anomalies": [{"label": a["label"], "value": float(a["value"]), "direction": a["direction"], "z": float(a["z"]),
                           "explanation": "%s is %s the trend (%s against an expected %s)." % (
                               a["label"], _off_trend(a["value"], a["expected"]), D.fmt(a["value"], f["format"]), D.fmt(a["expected"], f["format"]))}
                          for a in found],
            "summary": "%d unusual point%s in %s." % (len(found), "" if len(found) == 1 else "s", f["y"]) if found else "No anomalies detected."}


cap("data.anomaly", "Anomaly Spotlight",
    "Finds outliers with robust statistics and explains each in a sentence.",
    why="Anomalies are the reason people open dashboards; they should not have to be found by eye.",
    do="For each detected anomaly in facts write a one-sentence explanation. Do not add anomalies that are not in facts.",
    inp={"data": ["any"], "x?": "str", "y?": "str"},
    out={"anomalies": [{"label": "str", "value": "num", "direction": "enum:high|low", "z": "num", "explanation": "str"}], "summary": "str"},
    present="annotate", binds=["Chart", "Table"], ex={"data": ROWS}, facts=_anom, reflex=_anom)


def _query(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    spec = D.nl_query(i["question"], i["rows"])
    return {"filters": [{"column": f["column"], "op": f["op"], "value": str(f["value"])} for f in spec["filters"]],
            "sort": spec["sort"], "limit": int(spec["limit"]), "explanation": spec["explanation"], "confidence": spec["confidence"]}


def _apply(out: Dict[str, Any], i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    cols = {col["key"] for col in D.column_types(i.get("rows") or [])}
    out["filters"] = [f for f in out.get("filters") or [] if f.get("column") in cols]
    out["sort"] = [s for s in out.get("sort") or [] if s.get("column") in cols]
    out["rows"] = D.apply_query(i.get("rows") or [], out)
    out["matched"] = len(out["rows"])
    return out


cap("data.query", "Natural-Language Table Query",
    "Filters, sorts and limits a table from a sentence: “overdue invoices over $5k, newest first”.",
    why="Filter builders are powerful and unused; a sentence is how people already ask.",
    do="Translate the question into filters (op: eq, neq, gt, gte, lt, lte, contains), sort and limit over the listed columns only.",
    inp={"question": "str", "rows": ["any"]},
    out={"filters": [{"column": "str", "op": "enum:eq|neq|gt|gte|lt|lte|contains", "value": "str"}],
         "sort": [{"column": "str", "dir": "enum:asc|desc"}], "limit": "int", "explanation": "str", "confidence": "num"},
    present="fill", binds=["Table"], post=_apply, untrusted=["question"],
    ex={"question": "overdue invoices over 5000 sorted by amount desc", "rows": D.fixtures(["id", "customer", "amount", "status", "due_date"], 8)},
    facts=lambda i, c: {"columns": D.column_types(i["rows"])}, reflex=_query)

cap("data.column_types", "Column Typing & Formatting",
    "Infers each column's semantic type, display format and alignment from sample rows.",
    why="Currency right-aligned with two decimals, dates as dates: details that tables rarely get right by default.",
    inp={"rows": ["any"]},
    out={"columns": [{"key": "str", "label": "str", "type": "str", "format": "str", "align": "str", "unique": "int", "missing": "int"}]},
    present="service", binds=["Table"], ex={"rows": D.fixtures(["name", "email", "mrr", "churn_rate", "created_at"], 4)},
    direct=lambda i, c: {"columns": D.column_types(i["rows"])})


def _explain(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    v = D.to_number(i.get("value"))
    series = [D.to_number(x) for x in (i.get("context") or [])]
    series = [x for x in series if x is not None]
    if v is None or not series:
        return note(str(i.get("label") or "Value"), "No comparison data is available for this number.", [], 0.3, "neutral")
    mean = sum(series) / len(series)
    rank = sorted(series, reverse=True).index(v) + 1 if v in series else None
    pct = (v - mean) / abs(mean) * 100 if mean else 0
    return note("%s: %s" % (i.get("label") or "Value", D.fmt(v)), "%.0f%% %s the average of %s." % (abs(pct), "above" if pct >= 0 else "below", D.fmt(mean)),
                (["Ranks %d of %d" % (rank, len(series))] if rank else []) + ["Range %s – %s" % (D.fmt(min(series)), D.fmt(max(series)))],
                0.85, "success" if pct > 5 else ("warning" if pct < -5 else "info"))


cap("data.explain_value", "Explain This Number",
    "Explains any figure in context: how it compares with the average, its rank and its range.",
    why="A number without context is a fact; with context it is information.",
    do="Explain what the value means relative to the comparison series in facts, in one sentence plus up to three points.",
    inp={"value": "any", "label?": "str", "context?": ["any"]}, out=NOTE, present="ask", binds=["Stat", "Table"],
    ex={"value": 81000, "label": "May revenue", "context": [42000, 44500, 47100, 49800, 81000, 54200, 57900]},
    facts=lambda i, c: {"series": i.get("context")}, reflex=_explain)

cap("data.forecast", "Forecast Ghost Line",
    "Projects a series forward with a confidence band, drawn as a dashed continuation of the chart.",
    why="“Where is this heading?” is the next question after every trend chart.",
    inp={"values": ["num"], "horizon?": "int"},
    out={"points": [{"step": "int", "value": "num", "low": "num", "high": "num"}], "method": "str"}, present="service", binds=["Chart"],
    ex={"values": [10, 12, 13, 15, 16, 17, 19], "horizon": 3},
    direct=lambda i, c: {"points": D.forecast([float(v) for v in i["values"]], int(i.get("horizon") or 3)),
                         "method": "Least-squares linear trend with an 80% residual band."})


def _narr(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    rows = i["rows"]
    ins = D.insights(rows)
    return {"text": "%d records. %s %s" % (len(rows), ins["body"], " ".join(b + "." for b in ins["bullets"][:2])), "rationale": "Count, headline, then extremes."}


cap("data.narrate", "Table-to-Narrative",
    "Turns a table into a short paragraph a person could read aloud in a meeting.",
    why="Not every audience reads tables; every audience reads sentences.",
    do="Summarise the table in two or three sentences using only the numbers in facts.",
    inp={"rows": ["any"]}, out={"text": "str", "rationale?": "str"}, present="annotate", binds=["Table"], ex={"rows": ROWS},
    facts=lambda i, c: D.facts(i["rows"]), reflex=_narr)

cap("data.search", "Semantic Search",
    "Ranks documents or records by meaning using embeddings, with a local index for offline use.",
    why="Keyword search fails on synonyms; people search for what they mean.",
    inp={"query": "str", "documents": ["str"], "k?": "int"}, out={"results": [{"index": "int", "score": "num", "text": "str"}]},
    present="suggest", binds=["Search", "Table", "List"],
    ex={"query": "refund a payment", "documents": ["How to refund a customer payment", "Invite teammates", "Export invoices as CSV"]},
    direct=lambda i, c: {"results": (c.kernel.vectors.rank(i["query"], i["documents"], int(i.get("k") or 5)) if c.kernel
                                     else D.search(i["query"], i["documents"], int(i.get("k") or 5)))})


def _formula_post(out: Dict[str, Any], i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    rows = i.get("rows") or []
    out["preview"] = [D.evaluate(out.get("expression") or "", r, rows) for r in rows[:5]] if out.get("expression") else []
    if out.get("expression") and rows and all(p is None for p in out["preview"]):
        out["expression"], out["explanation"], out["confidence"] = "", "The expression could not be evaluated safely.", 0.0
    return out


cap("data.formula", "Formula from Description",
    "Writes a computed-column formula from a description and evaluates it in a sandboxed evaluator.",
    why="Spreadsheet formulas are a programming language most users never asked to learn.",
    do="Write an arithmetic expression over the column names (operators + - * / and sum, avg, min, max, count, round, abs) that computes what is described.",
    inp={"description": "str", "columns": ["str"], "rows?": ["any"]},
    out={"expression": "str", "explanation": "str", "columns": ["str"], "confidence": "num"}, present="service", binds=["Table"],
    post=_formula_post, ex={"description": "price times quantity", "columns": ["price", "quantity"], "rows": [{"price": 3, "quantity": 4}]},
    reflex=lambda i, c: D.formula_from_text(i["description"], i["columns"]))

cap("data.story", "Data Storytelling",
    "Builds a narrative sequence of views from a dataset: headline, then one annotated chart per measure.",
    why="Stakeholders remember stories, not dashboards.",
    do="Compose a scene that tells the data's story: a headline, then sections each with a chart and an insight. Use the facts for every claim.",
    inp={"rows": ["any"], "title?": "str"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"], max_out=3000,
    ex={"rows": ROWS, "title": "First-half performance"}, facts=lambda i, c: D.facts(i["rows"]),
    reflex=lambda i, c: scene(*S.story(i["rows"], i.get("title") or "")))

cap("data.entities", "Entity Recognition",
    "Spots people, organisations, amounts, dates and contacts in text so they can become interactive.",
    why="A name in a paragraph should be one hover away from its record.",
    do="List the entities in the text with their kind: person, organization, money, date, percent, email, phone or url.",
    inp={"text": "str"}, out={"entities": [{"kind": "str", "text": "str"}]}, present="annotate", binds=["Text", "Markdown", "Thread"],
    untrusted=["text"], ex={"text": "Mira Chen met Acme Corp on March 3, 2027 about a $1.2m deal."},
    reflex=lambda i, c: {"entities": __import__("fluidian.reflex.parse", fromlist=["entities"]).entities(i["text"])})

cap("data.dedupe", "Duplicate Detection",
    "Groups records that are probably the same entity despite spelling and formatting differences.",
    why="Duplicates corrupt every count on every dashboard downstream.",
    inp={"records": ["any"], "keys?": ["str"], "threshold?": "num"}, out={"groups": [{"indices": ["int"], "similarity": "num"}]},
    present="service", binds=["Table"], ex={"records": ["Acme Corp", "ACME Corp.", "Globex", "Acme Corporation"], "threshold": 0.55},
    direct=lambda i, c: {"groups": D.dedupe(i["records"], i.get("keys"), float(i.get("threshold") or 0.72))})

cap("data.kpi", "KPI Card Generator",
    "Chooses the headline figures in a dataset and renders them as Stat cards with deltas and sparklines.",
    why="Deciding which three numbers matter is the hard part of every dashboard.",
    do="Compose a Grid of Stat components for the most decision-relevant measures, with deltas from facts.",
    inp={"rows": ["any"]}, out=SCENE, present="compose", binds=["Generative"], ex={"rows": ROWS},
    facts=lambda i, c: {"kpis": D.kpis(i["rows"])},
    reflex=lambda i, c: scene(S.N("Grid", *[S.N("Stat", label=k["label"].capitalize(), value=k["value"], delta=k["delta"], trend=k["trend"], spark=k["spark"])
                                            for k in D.kpis(i["rows"])], columns=max(1, min(4, len(D.kpis(i["rows"]))))),
                              "One card per numeric measure, with half-over-half change."))


def _units(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    from ..reflex import parse as P
    out = []
    for raw in i.get("values") or []:
        q = P.quantity(str(raw))
        conv = P.convert(float(q["value"]), q["unit"], i["to"]) if q["value"] and q["unit"] and i.get("to") else None
        out.append({"input": str(raw), "value": float(conv if conv is not None else (q["value"] or 0)),
                    "unit": i["to"] if conv is not None else q["unit"], "ok": bool(q["value"]) and (conv is not None or not i.get("to"))})
    return {"values": out}


cap("data.units", "Unit Normalisation",
    "Converts mixed units in a column — hours and minutes, kilograms and pounds — to one unit.",
    why="Mixed units make sums meaningless and are invisible until someone checks.",
    inp={"values": ["str"], "to?": "str"}, out={"values": [{"input": "str", "value": "num", "unit": "str", "ok": "bool"}]},
    present="service", binds=["Table"], ex={"values": ["90 min", "2 h", "45 minutes"], "to": "h"}, direct=_units)

cap("data.pivot", "Pivot Suggestions",
    "Suggests the group-by and aggregate combinations most likely to be informative for a table.",
    why="Pivot tables are powerful once you know what to pivot on.",
    do="Suggest up to six group-by/aggregate combinations over the listed columns, most informative first.",
    inp={"rows": ["any"]}, out=ITEMS, present="suggest", binds=["Table"], ex={"rows": D.fixtures(["customer", "status", "amount", "plan"], 8)},
    facts=lambda i, c: {"columns": D.column_types(i["rows"])}, reflex=lambda i, c: items(D.pivots(i["rows"])))
