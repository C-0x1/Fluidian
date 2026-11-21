"""Generative Composition capabilities."""
from __future__ import annotations

from typing import Any, Dict

from .. import components as C
from ..reflex import scene as S
from .registry import SCENE, Ctx, cap, scene


def scene_in(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    """The scene to operate on: the explicit input, else the session's current scene."""
    raw = i.get("scene")
    if isinstance(raw, dict):
        return C.normalize(C.from_transport(raw))[0]
    return c.scene or C.normalize({"type": "Page", "props": {"title": ""}})[0]


cap("compose.intent", "Intent-to-Interface",
    "Turns a plain-language description of a screen into a complete, renderable scene.",
    why="The fastest path from idea to interface is a sentence; the framework owns layout, hierarchy and component choice.",
    do="Compose a scene that fulfils the intent using only catalogue components. Lead with what matters most, give every "
       "field a label, keep to one primary action per region, and bind buttons to registered actions when one fits.",
    inp={"intent": "str", "constraints?": "str"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"],
    uses_actions=True, stream=True, max_out=2600,
    ex={"intent": "Contact form with name, email, company and message"},
    reflex=lambda i, c: scene(*S.compose_intent(i["intent"])))

cap("compose.data_view", "Data-Shaped Views",
    "Inspects arbitrary JSON and chooses the presentation that fits its shape: table, figures, chart or detail.",
    why="APIs return shapes, not screens; choosing the view from the data removes a whole class of glue code.",
    do="Choose the clearest presentation for the data. Records become a table with typed columns, numeric series gain a "
       "chart, headline numbers become Stat components. Use the data exactly as given.",
    inp={"data": "any", "title?": "str", "question?": "str"}, out=SCENE, present="compose", tier="balanced",
    binds=["Generative"], max_out=2600,
    ex={"data": [{"month": "Jan", "revenue": 42000}, {"month": "Feb", "revenue": 46500}, {"month": "Mar", "revenue": 51200}], "title": "Revenue"},
    reflex=lambda i, c: scene(*S.data_view(i["data"], i.get("title") or "")))

cap("compose.schema_form", "Schema-to-Form",
    "Builds a grouped, labelled form from a JSON Schema, choosing the right control for every property.",
    why="A schema already states types, formats and constraints; re-typing them as form markup is waste and drift.",
    do="Create a form for the schema. Pick controls from type, format, enum and name; group related properties into "
       "sections; mark required fields; write helper text from descriptions.",
    inp={"schema": "any", "name?": "str", "values?": "any", "submitLabel?": "str"}, out=SCENE, present="compose",
    tier="fast", binds=["SmartForm", "Generative"], max_out=2200,
    ex={"schema": {"title": "Contact", "type": "object", "required": ["email"],
                   "properties": {"email": {"type": "string", "format": "email"}, "plan": {"enum": ["Starter", "Scale"]},
                                  "seats": {"type": "integer", "minimum": 1, "maximum": 50}}}},
    reflex=lambda i, c: scene(*S.schema_form(i["schema"], i.get("name") or "form", i.get("values"), i.get("submitLabel") or "Save")))

cap("compose.wireframe", "Wireframe-to-Scene",
    "Converts a plain-text sketch — headings, brackets for buttons, underscores for inputs — into a working scene.",
    why="Sketching in a text editor is the lowest-friction design tool there is; it should produce real UI.",
    do="Interpret the sketch as an interface: '# ' headings, '[ Label ]' buttons, '[____]' or 'Label: ____' inputs, "
       "'[x]' checkboxes, '( )' radios, pipes for tables, '---' dividers. Preserve order and wording.",
    inp={"sketch": "str"}, out=SCENE, present="compose", tier="fast", binds=["Generative"], max_out=2200,
    ex={"sketch": "# Checkout\nName: ____\n[____] Email\n[x] Save card\n[Back] [*Pay now]"},
    reflex=lambda i, c: scene(*S.wireframe(i["sketch"])))

cap("compose.html_import", "HTML-to-Scene Migration",
    "Maps existing HTML onto Fluidian components, discarding presentation in favour of design tokens.",
    why="Adoption stalls when existing screens must be rewritten by hand; migration should be a paste.",
    do="Translate the HTML into catalogue components by meaning, not appearance. Keep text, field names, options and "
       "table data. Ignore scripts, styles and tracking markup.",
    inp={"html": "str"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"], untrusted=["html"], max_out=2600,
    ex={"html": "<h1>Join</h1><form><label>Email</label><input type='email' name='email'><button type='submit'>Sign up</button></form>"},
    reflex=lambda i, c: scene(*S.html_import(i["html"])))

cap("compose.remix", "Layout Remix",
    "Produces alternative arrangements of the same content so layouts can be compared instead of imagined.",
    why="Exploring layout options is expensive by hand, so most teams ship the first one.",
    do="Return distinct arrangements of the given scene's content. Do not add or remove content; change grouping, "
       "order and containers. Name each variant and state when it is the better choice.",
    inp={"scene?": "any", "count?": "int", "goal?": "str"},
    out={"variants": [{"name": "str", "rationale": "str", "scene": "node"}]}, present="service", tier="balanced",
    uses_scene=True, max_out=3200,
    ex={"scene": {"type": "Page", "props": {"title": "Overview"}, "children": [
        {"type": "Card", "props": {"title": "Revenue"}}, {"type": "Card", "props": {"title": "Orders"}}, {"type": "Card", "props": {"title": "Churn"}}]}, "count": 3},
    reflex=lambda i, c: {"variants": [{"name": v["name"], "rationale": v["rationale"], "scene": C.to_transport(v["scene"])}
                                      for v in S.remix(scene_in(i, c), int(i.get("count") or 3))]})

cap("compose.refine", "Conversational Refinement",
    "Edits an existing scene from an instruction such as “make it compact” or “add a phone field”.",
    why="Iteration is where interfaces get good; each round should cost one sentence.",
    do="Apply the instruction to the scene and return the full updated scene. Change only what the instruction asks; "
       "keep ids, field names and bound actions intact.",
    inp={"instruction": "str", "scene?": "any"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"],
    uses_scene=True, max_out=2800,
    ex={"instruction": "add a phone field", "scene": {"type": "Page", "props": {"title": "Contact"}, "children": [
        {"type": "Form", "props": {"name": "contact"}, "children": [{"type": "Input", "props": {"name": "email", "label": "Email"}},
                                                                    {"type": "Button", "props": {"label": "Send", "variant": "primary"}}]}]}},
    reflex=lambda i, c: scene(*S.refine(scene_in(i, c), i["instruction"])))

cap("compose.empty_state", "Empty-State Author",
    "Writes the empty state for a region: what is missing, why, and the best next step.",
    why="Empty screens are where new users decide to leave; a good empty state is onboarding.",
    do="Write an EmptyState for the context: a short title, one helpful sentence and at most two actions. Distinguish "
       "'nothing yet', 'no results' and 'failed to load'.",
    inp={"context": "str", "actions?": ["str"]}, out=SCENE, present="compose", tier="fast",
    binds=["Table", "List", "Board", "Generative"], max_out=500,
    ex={"context": "invoices table for a brand-new workspace"},
    reflex=lambda i, c: scene(S.empty_state(i["context"], i.get("actions")), "Tailored to the context and its most likely next step."))

cap("compose.skeleton", "Skeleton Forecaster",
    "Predicts loading placeholders that match the shape of the content about to arrive.",
    why="Skeletons that match the final layout remove layout shift and make waits feel shorter.",
    do="Return a scene of Skeleton components mirroring the structure of the described or given content: same "
       "containers, same proportions, text lines where text will be.",
    inp={"description?": "str", "scene?": "any"}, out=SCENE, present="compose", tier="fast", binds=["Generative"], max_out=1200,
    ex={"description": "sales dashboard with three figures, a chart and a table"},
    reflex=lambda i, c: scene(S.skeleton_for(scene_in(i, c) if i.get("scene") else None, i.get("description") or ""),
                              "Placeholders mirror the containers and proportions of the expected content."))


def _disclose(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    ranked = S.priorities(scene_in(i, c))
    budget = int(i.get("budget") or max(1, (len(ranked) + 1) // 2))
    return {"primary": [r["id"] for r in ranked[:budget]], "secondary": [r["id"] for r in ranked[budget:]],
            "rationale": "Kept the %d highest-value regions visible; the rest move behind “Show more”." % min(budget, len(ranked))}


cap("compose.disclose", "Progressive Disclosure Planner",
    "Decides which regions stay visible and which move behind disclosure, based on importance.",
    why="Showing everything at once is the most common cause of overwhelming screens.",
    do="Rank the top-level regions by importance to the screen's main task. Return ids to keep visible (primary) and "
       "ids to tuck away (secondary). Use only ids from the scene.",
    inp={"scene?": "any", "budget?": "int"}, out={"primary": ["str"], "secondary": ["str"], "rationale": "str"},
    present="service", tier="fast", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Account"}, "children": [
        {"type": "Card", "id": "plan", "props": {"title": "Plan"}, "children": [{"type": "Stat", "props": {"label": "Seats", "value": "24"}}]},
        {"type": "Card", "id": "log", "props": {"title": "Audit log"}, "children": [{"type": "Timeline", "props": {"items": []}}]}]}, "budget": 1},
    reflex=_disclose)


def _responsive(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    ranked = S.priorities(scene_in(i, c))
    plan = []
    for pos, r in enumerate(ranked):
        if pos < 2:
            mode, why = "keep", "Core to the task; shown first on small screens."
        elif r["type"] in ("Table", "Board"):
            mode, why = "summarize", "Wide content becomes a summary card with a link to the full view."
        elif r["type"] in ("Split", "Grid", "Row", "Toolbar"):
            mode, why = "stack", "Side-by-side content stacks vertically."
        elif pos >= max(4, len(ranked) - 1):
            mode, why = "hide", "Lowest priority; available from the overflow menu."
        else:
            mode, why = "collapse", "Secondary; collapsed behind its title."
        plan.append({"id": r["id"], "compact": mode, "priority": r["score"], "reason": why})
    return {"plan": plan}


cap("compose.responsive", "Semantic Reflow",
    "Plans small-screen behaviour by meaning: what stays, stacks, collapses, summarises or hides.",
    why="Breakpoints know widths, not importance; reflow should follow what the user came to do.",
    do="For each top-level region decide its compact behaviour: keep, stack, collapse, summarize or hide, with a "
       "priority and a reason. Use only ids from the scene.",
    inp={"scene?": "any"},
    out={"plan": [{"id": "str", "compact": "enum:keep|stack|collapse|hide|summarize", "priority": "num", "reason": "str"}]},
    present="service", tier="fast", uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Orders"}, "children": [
        {"type": "Toolbar", "id": "tools"}, {"type": "Table", "id": "orders", "props": {"rows": [], "columns": []}},
        {"type": "Card", "id": "tips", "props": {"title": "Tips"}}]}},
    reflex=_responsive)

cap("compose.continue", "Screen Continuation",
    "Predicts and drafts the screen a person will most likely need next.",
    why="Knowing the next screen lets an app prefetch, pre-render and remove a navigation step.",
    do="Given the current scene, compose the most probable next screen in the same flow: confirmation after a form, "
       "detail after a list, overview after sign-in.",
    inp={"scene?": "any", "goal?": "str"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"],
    uses_scene=True, max_out=2400,
    ex={"scene": {"type": "Page", "props": {"title": "Customers"}, "children": [{"type": "Table", "props": {"rows": [], "columns": []}}]}},
    reflex=lambda i, c: scene(*S.continuation(scene_in(i, c))))


def _component(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    node, why = S.compose_intent(i["description"])
    body = node.get("children") or [node]
    name = i.get("name") or "".join(w.capitalize() for w in S._intent_title(i["description"]).split()[:3]) or "Composite"
    slots = [str((n.get("props") or {}).get("name")) for n, _, _ in C.walk(node) if (n.get("props") or {}).get("name")]
    return {"name": name, "scene": C.to_transport(S.N("Card", *body, title=S._intent_title(i["description"]))),
            "slots": slots[:8], "rationale": "A reusable composite built from primitives. " + why}


cap("compose.component", "Component Synthesis",
    "Designs a reusable composite component from a description, using only primitives.",
    why="Teams reinvent the same card, row and panel; synthesis gives a consistent starting point in seconds.",
    do="Design one self-contained composite from catalogue primitives. Return its PascalCase name, the scene, and "
       "the named slots a developer would parameterise.",
    inp={"description": "str", "name?": "str"}, out={"name": "str", "scene": "node", "slots": ["str"], "rationale": "str"},
    present="service", tier="balanced", max_out=1800,
    ex={"description": "pricing plans"}, reflex=_component)


def _variants(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    sc = scene_in(i, c)
    types = {n["type"] for n, _, _ in C.walk(sc)}
    metric = i.get("metric") or "conversion"
    out = [{"name": "Outcome-led primary action", "hypothesis": "Naming the outcome on the main button raises %s." % metric,
            "change": "Rename the primary button to state what happens next.", "expectedEffect": "Higher click-through on the primary action.", "risk": "low"}]
    if "Form" in types or "SmartForm" in types:
        out.append({"name": "Two-step form", "hypothesis": "Asking for fewer fields first reduces abandonment.",
                    "change": "Move optional fields to a second step.", "expectedEffect": "More starts completed.", "risk": "medium"})
    if "Table" in types:
        out.append({"name": "Summary above table", "hypothesis": "Headline figures help people decide where to look.",
                    "change": "Add three Stat components above the table.", "expectedEffect": "Faster time to first action.", "risk": "low"})
    out.append({"name": "Social proof near action", "hypothesis": "Reassurance at the decision point improves %s." % metric,
                "change": "Place a short proof statement beside the primary action.", "expectedEffect": "Fewer hesitations before acting.", "risk": "low"})
    return {"variants": out[:4]}


cap("compose.variant_lab", "Variant Lab",
    "Proposes A/B variants for a screen, each with a hypothesis, the concrete change and its risk.",
    why="Experiments fail at the idea stage; structured hypotheses make testing routine.",
    do="Propose up to four experiment variants that could improve the metric. Each needs a falsifiable hypothesis, "
       "one concrete change to this scene, the expected effect and a risk level.",
    inp={"scene?": "any", "metric": "str"},
    out={"variants": [{"name": "str", "hypothesis": "str", "change": "str", "expectedEffect": "str", "risk": "enum:low|medium|high"}]},
    present="service", tier="balanced", uses_scene=True,
    ex={"metric": "sign-up completion", "scene": {"type": "Page", "props": {"title": "Sign up"}, "children": [
        {"type": "Form", "props": {"name": "signup"}, "children": [{"type": "Input", "props": {"name": "email", "label": "Email"}}]}]}},
    reflex=_variants)
