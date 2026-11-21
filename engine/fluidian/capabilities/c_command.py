"""Conversational Command capabilities."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .. import components as C
from ..reflex import behavior as B
from ..reflex import data as D
from ..reflex import parse as P
from ..reflex import text as T
from .registry import FIELDS, ITEMS, PLAN, Ctx, cap, fields, items, texts_of

ROUTE = {"action": "str", "args": "json", "confidence": "num", "reply": "str", "alternatives": ["str"]}
DEMO_ACTIONS = [{"name": "create_invoice", "description": "Create a new invoice for a customer",
                 "params": {"customer": "string customer name", "amount": "number amount", "due": "date due date"}},
                {"name": "export_report", "description": "Download the monthly report as CSV"},
                {"name": "invite_user", "description": "Invite a teammate by email", "params": {"email": "string email address"}}]


def acts(i: Dict[str, Any], c: Ctx) -> List[Dict[str, Any]]:
    given = i.get("actions")
    return [a for a in given if isinstance(a, dict)] if isinstance(given, list) and given else c.actions


def _route(i: Dict[str, Any], c: Ctx, key: str = "utterance") -> Dict[str, Any]:
    text = re.sub(r"^\s*(um+|uh+|hey|okay|ok|so|please|can you|could you|i want to|i'd like to)[, ]+", "", i.get(key) or "", flags=re.IGNORECASE)
    hit = B.route(text, acts(i, c))
    return dict(hit, args=json.dumps(hit["args"], ensure_ascii=False))


def parse_args(out: Dict[str, Any], i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    """Post-processor: decode JSON-encoded argument strings into objects."""
    def fix(obj: Dict[str, Any]) -> None:
        if isinstance(obj.get("args"), str):
            try:
                parsed = json.loads(obj["args"])
            except ValueError:
                parsed = {}
            obj["args"] = parsed if isinstance(parsed, dict) else {}
    fix(out)
    for step in out.get("steps") or []:
        if isinstance(step, dict):
            fix(step)
    return out


cap("command.route", "Intent Bar Routing",
    "Maps a typed or spoken request to one of the application's registered actions and extracts its arguments.",
    why="Every application has more actions than its menus can show; language reaches all of them.",
    do="Choose the registered action that best fulfils the utterance and extract its arguments as a JSON object string. "
       "Use action 'none' when nothing fits. Never invent an action name.",
    inp={"utterance": "str", "actions?": ["any"]}, out=ROUTE, present="command", binds=["IntentBar"],
    uses_actions=True, uses_scene=True, post=parse_args, max_out=300,
    ex={"utterance": "create an invoice for Acme Corp for $1,200 due next friday", "actions": DEMO_ACTIONS}, reflex=_route)

cap("command.plan", "Action Planner",
    "Breaks a multi-step goal into an ordered plan of registered actions, each rated for risk.",
    why="People state outcomes, not click sequences; planning bridges the two and keeps risky steps reviewable.",
    do="Plan the goal as ordered steps using only registered actions. Give each step its arguments (JSON object "
       "string), a risk level and a reason. Return no steps if the goal cannot be met.",
    inp={"goal": "str", "actions?": ["any"]}, out=PLAN, present="command", tier="balanced", binds=["IntentBar"],
    uses_actions=True, uses_scene=True, post=parse_args,
    ex={"goal": "create an invoice for Globex for $300 then export the report", "actions": DEMO_ACTIONS},
    reflex=lambda i, c: (lambda p: dict(p, steps=[dict(s, args=json.dumps(s["args"])) for s in p["steps"]]))(B.plan(i["goal"], acts(i, c))))


def _copilot(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    msg = i.get("message") or ""
    hit = B.route(msg, acts(i, c)) if acts(i, c) else {"action": "none", "confidence": 0}
    texts = texts_of(c.scene, 80)
    if hit["action"] != "none" and hit["confidence"] >= 0.6:
        return {"reply": "I can do that: %s Shall I go ahead?" % hit["reply"], "suggestions": ["Yes, run it", "Not now"],
                "action": hit["action"], "args": json.dumps(hit["args"])}
    found = D.search(msg, texts, 3)
    if found:
        reply = "On this screen: " + "; ".join("“%s”" % T.clip(f["text"], 90) for f in found) + "."
    elif texts:
        reply = "This screen is “%s”. It contains %d labelled elements; ask about any of them." % (texts[0], len(texts))
    else:
        reply = "I don't have a screen to look at yet. Ask me once one is open."
    return {"reply": reply, "suggestions": ["Summarise this screen", "What can I do here?"], "action": None, "args": "{}"}


cap("command.copilot", "Copilot Dock",
    "A scene-aware assistant: answers questions about what is on screen and proposes registered actions.",
    why="An assistant that cannot see the interface gives generic answers; grounding it in the scene makes it useful.",
    do="Answer using the scene outline and conversation. Be brief and specific to this screen. If a registered "
       "action would help, name it with arguments and ask for confirmation. Offer up to three follow-up prompts.",
    inp={"message": "str", "history?": ["any"]},
    out={"reply": "str", "suggestions": ["str"], "action?": "str", "args": "json"}, present="chat", tier="balanced",
    binds=["Copilot"], uses_scene=True, uses_actions=True, stream=True, post=parse_args, untrusted=["message"],
    ex={"message": "what can I do here?"}, reflex=_copilot)


def _ask(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    nodes = [(n, C.primary_text(n)) for n, _, _ in C.walk(c.scene)] if c.scene else []
    nodes = [(n, t) for n, t in nodes if t]
    found = D.search(i.get("question") or "", [t for _, t in nodes], 3)
    if not found:
        return {"answer": "Nothing on this screen matches that question.", "references": [], "confidence": 0.2}
    return {"answer": "The closest match is “%s” (%s)." % (found[0]["text"], nodes[found[0]["index"]][0]["type"]),
            "references": [nodes[f["index"]][0]["id"] for f in found], "confidence": min(0.9, 0.4 + found[0]["score"])}


cap("command.ask_screen", "Ask the Screen",
    "Answers a question about the current screen and points to the elements the answer came from.",
    why="“Where do I change my plan?” is faster to ask than to hunt for.",
    do="Answer the question from the scene outline only. Cite the ids of the elements you relied on. Say so plainly "
       "if the screen does not contain the answer.",
    inp={"question": "str"}, out={"answer": "str", "references": ["str"], "confidence": "num"}, present="ask",
    uses_scene=True, untrusted=["question"], max_out=320, ex={"question": "where do I save?"}, reflex=_ask)


def _point(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    node = C.find(c.scene, i.get("target") or "") if c.scene else None
    if node is None:
        return {"answer": "That element is not on this screen.", "role": "unknown", "nextSteps": []}
    spec, props = C.SPEC[node["type"]], node.get("props") or {}
    bits = ["This is a %s%s." % (node["type"], (" labelled “%s”" % C.primary_text(node)) if C.primary_text(node) else ""), spec["summary"]]
    steps = []
    if props.get("disabled"):
        bits.append("It is disabled right now.")
        steps.append("Complete the required fields to enable it.")
    if props.get("error"):
        bits.append("It reports: %s" % props["error"])
        steps.append("Correct the value and try again.")
    if props.get("required"):
        bits.append("It is required.")
    for event, binding in (node.get("on") or {}).items():
        steps.append("On %s it runs “%s”." % (event, binding["action"].replace("_", " ")))
    return {"answer": " ".join(bits), "role": node["type"], "nextSteps": steps[:3]}


cap("command.point_ask", "Point-and-Ask",
    "Explains any element a person points at: what it is, why it is in its current state, what it will do.",
    why="“Why is this button greyed out?” deserves an answer at the button, not in a help centre.",
    do="Explain the targeted element in plain language: what it is for, why it is in its current state and what "
       "happens when it is used. Ground every statement in the scene outline.",
    inp={"target": "str", "question?": "str"}, out={"answer": "str", "role": "str", "nextSteps": ["str"]},
    present="ask", uses_scene=True, max_out=320, ex={"target": "save"}, reflex=_point)

cap("command.slash", "Slash Command Synthesis",
    "Generates a consistent slash-command vocabulary from the registered actions.",
    why="Power users want a keyboard path to everything without the team hand-curating commands.",
    do="Derive one short, unique slash command per registered action with its parameters in angle brackets.",
    inp={"actions?": ["any"]}, out=ITEMS, present="suggest", binds=["IntentBar"], uses_actions=True,
    ex={"actions": DEMO_ACTIONS}, reflex=lambda i, c: items(B.slash_commands(acts(i, c))))


def _next(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    recent = set(i.get("recent") or [])
    out = []
    if c.scene:
        for n, _, _ in C.walk(c.scene):
            if n["type"] == "Button" and n.get("on") and (n.get("props") or {}).get("variant") in ("primary", "ai"):
                out.append({"label": C.primary_text(n), "action": n["on"].get("click", {}).get("action"), "icon": "arrow-right", "score": 0.9})
    for a in acts(i, c):
        if a.get("name") not in recent and not any(o["action"] == a.get("name") for o in out):
            out.append({"label": T.sentence_case(str(a.get("name", "")).replace("_", " ")), "action": a.get("name"),
                        "detail": a.get("description"), "icon": "bolt", "score": 0.5})
    return items(out[:4])


cap("command.next_actions", "Next-Best-Action Chips",
    "Suggests the few actions most likely to be useful right now, given the screen and recent activity.",
    why="A short, relevant list beats a full menu; it turns navigation into recognition.",
    do="Suggest up to four next actions for this screen. Prefer registered actions and reference them by name. "
       "Keep labels under four words.",
    inp={"recent?": ["str"], "goal?": "str"}, out=ITEMS, present="suggest", binds=["Suggestions"], uses_scene=True,
    uses_actions=True, ex={"recent": ["export_report"]}, reflex=_next)

cap("command.undo_story", "Undo Narrative",
    "Narrates recent history in plain language and locates the step a person wants to undo.",
    why="“Undo the thing where I changed the owner” is how people think; Ctrl+Z ×7 is not.",
    do="Summarise the history as short numbered steps. If a request is given, return the zero-based index of the "
       "step to revert to and how many steps that reverts.",
    inp={"history": ["any"], "request?": "str"},
    out={"narrative": "str", "target": "int", "label": "str", "steps_reverted": "int"}, present="service",
    ex={"history": [{"label": "Renamed project"}, {"label": "Changed owner to Mira"}, {"label": "Archived 3 tasks"}],
        "request": "undo the owner change"},
    reflex=lambda i, c: B.undo_story(i.get("history") or [], i.get("request") or ""))

cap("command.macro", "Macro Distiller",
    "Notices a repeated sequence of actions and offers to save it as a single command.",
    why="Repetition is a feature request the user never files.",
    do="Find the longest action sequence repeated at least three times. Name it, list its steps and write a "
       "one-line offer to automate it. Set found to false if there is none.",
    inp={"events?": ["any"]}, out={"found": "bool", "name": "str", "repeats": "int", "steps": ["str"], "pitch": "str"},
    present="observe",
    ex={"events": [{"t": n * 900, "kind": "click", "target": t} for n, t in enumerate("filter export archive filter export archive filter export archive".split())]},
    reflex=lambda i, c: B.find_macro(i.get("events") or c.signals))


def _chat_form(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    got = P.smart_paste(i.get("message") or "", i.get("fields") or [])
    filled = set((i.get("filled") or {}).keys()) | {g["name"] for g in got}
    names = [f.get("name") if isinstance(f, dict) else str(f) for f in i.get("fields") or []]
    missing = [n for n in names if n not in filled]
    return {"fields": fields(got)["fields"], "complete": not missing,
            "question": ("What is the %s?" % missing[0].replace("_", " ")) if missing else None}


cap("command.chat_form", "Conversation-to-Form",
    "Fills a form through conversation: extracts values from each message and asks for what is still missing.",
    why="On small screens and for long forms, answering questions is easier than navigating fields.",
    do="Extract field values from the message. Then ask one short question for the most important missing field, "
       "or mark the form complete.",
    inp={"message": "str", "fields": ["any"], "filled?": "any"},
    out={"fields": FIELDS["fields"], "question?": "str", "complete": "bool"}, present="fill", binds=["Form", "Copilot"],
    untrusted=["message"], ex={"message": "I'm Ada Lovelace, ada@analytical.io", "fields": ["name", "email", "company"]},
    reflex=_chat_form)

cap("command.shortcut", "Shortcut Synthesizer",
    "Assigns mnemonic, collision-free keyboard shortcuts to every registered action.",
    why="Shortcuts are designed once and collide forever; generation keeps them systematic.",
    do="Assign each action a memorable shortcut that avoids browser and OS conventions and never repeats.",
    inp={"actions?": ["any"]}, out=ITEMS, present="service", uses_actions=True, ex={"actions": DEMO_ACTIONS},
    reflex=lambda i, c: items(B.shortcuts(acts(i, c))))


def _disambiguate(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    hit = B.route(i.get("utterance") or "", acts(i, c))
    names = ([hit["action"]] if hit["action"] != "none" else []) + hit["alternatives"]
    return {"question": "Which did you mean?" if len(names) > 1 else ("Run “%s”?" % names[0].replace("_", " ") if names else "I couldn't find a matching action."),
            "choices": [{"label": T.sentence_case(n.replace("_", " ")), "action": n} for n in names[:4]]}


cap("command.disambiguate", "Intent Disambiguation",
    "When a request matches several actions, asks one question with the candidates as choices.",
    why="Running the wrong action is worse than asking; asking well takes one tap.",
    do="List the registered actions that plausibly match, most likely first, behind one short question.",
    inp={"utterance": "str", "actions?": ["any"]}, out={"question": "str", "choices": [{"label": "str", "action": "str"}]},
    present="suggest", binds=["IntentBar"], uses_actions=True, ex={"utterance": "send the report", "actions": DEMO_ACTIONS},
    reflex=_disambiguate)

cap("command.voice_intent", "Voice Intent",
    "Turns a spoken transcript — fillers, restarts and all — into a registered action with arguments.",
    why="Speech is messy; the interface should hear the request, not the disfluency.",
    do="Ignore fillers and false starts in the transcript, then choose the registered action and arguments as for "
       "typed requests. Use 'none' when nothing fits.",
    inp={"transcript": "str", "actions?": ["any"]}, out=ROUTE, present="command", binds=["Mic", "IntentBar"],
    uses_actions=True, post=parse_args, untrusted=["transcript"],
    ex={"transcript": "um, hey, could you invite ada@analytical.io please", "actions": DEMO_ACTIONS},
    reflex=lambda i, c: _route(i, c, "transcript"))


def _search(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    pool: List[Dict[str, Any]] = []
    for a in acts(i, c):
        pool.append({"text": "%s %s" % (str(a.get("name", "")).replace("_", " "), a.get("description", "")),
                     "label": T.sentence_case(str(a.get("name", "")).replace("_", " ")), "detail": "Action", "action": a.get("name"), "icon": "bolt"})
    if c.scene:
        for n, _, _ in C.walk(c.scene):
            if C.primary_text(n):
                pool.append({"text": C.primary_text(n), "label": C.primary_text(n), "detail": n["type"], "value": n["id"], "icon": "eye"})
    for d in i.get("documents") or []:
        pool.append({"text": str(d), "label": T.clip(str(d), 60), "detail": "Document", "value": str(d), "icon": "file"})
    hits = D.search(i.get("query") or "", [p["text"] for p in pool], 6)
    return items([dict(pool[h["index"]], score=h["score"]) for h in hits])


cap("command.search", "Universal Semantic Search",
    "One search across actions, on-screen elements and documents, ranked by meaning rather than keywords.",
    why="People should not need to know whether something is a page, a setting or a command to find it.",
    do="Rank the candidates by relevance to the query. Return the best six with a label, the kind as detail, and the "
       "action name or element id.",
    inp={"query": "str", "documents?": ["str"]}, out=ITEMS, present="suggest", binds=["Search", "IntentBar"],
    uses_scene=True, uses_actions=True, untrusted=["query"],
    ex={"query": "download csv", "documents": ["How to refund a payment", "Exporting data as CSV"]}, reflex=_search)
