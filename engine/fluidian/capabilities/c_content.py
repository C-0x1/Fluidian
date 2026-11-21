"""Content & Microcopy, Workflow & Agentic UI, Collaboration, Ambient & Emotional UX capabilities."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .. import components as C
from ..reflex import behavior as B
from ..reflex import data as D
from ..reflex import design as G
from ..reflex import review as R
from ..reflex import scene as S
from ..reflex import text as T
from .c_command import DEMO_ACTIONS, acts, parse_args
from .c_compose import scene_in
from .registry import DIRECTIVES, ITEMS, NOTE, PLAN, SCENE, TEXT, VERDICT, Ctx, cap, directives, items, note, scene, verdict

LONG = ("The importer now accepts CSV and Excel files up to 50 MB. We decided to ship column mapping first and defer "
        "deduplication to the next release. Mira will write the migration guide by Friday. Early testers reported "
        "that validation errors were confusing, so the error messages were rewritten.")

cap("content.microcopy", "Microcopy Author",
    "Writes button labels, field labels and helper text that state outcomes in the product's voice.",
    why="“Submit” and “OK” are the default because good labels take thought nobody budgets for.",
    do="Rewrite the label so it states the outcome in two to four words, sentence case, verb first.",
    inp={"text": "str", "context?": "str", "voice?": "str"}, out=TEXT, present="transform", binds=["Button", "Link", "Input"],
    max_out=120, ex={"text": "Submit", "context": "saving profile settings"},
    reflex=lambda i, c: {"text": R.suggest_label(i["text"]), "rationale": "Names the outcome instead of the mechanism."})

cap("content.translate", "Scene Translation",
    "Translates interface text into a target locale, preserving placeholders, names and formatting.",
    why="Localisation is usually a release blocker; it should be a property of the interface.",
    do="Translate each text into the locale. Keep placeholders such as {name} and %s, product names and numbers unchanged. Return texts in the same order.",
    inp={"texts": ["str"], "locale": "str"}, out={"texts": ["str"], "locale": "str"}, present="transform",
    binds=["Page", "Shell", "Text", "Button"], ex={"texts": ["Save changes", "Welcome", "Hello {name}"], "locale": "es"},
    reflex=lambda i, c: {"texts": [T.localize(t, i["locale"])[0] for t in i["texts"]], "locale": i["locale"]})

cap("content.summarize", "TL;DR Summaries",
    "Condenses long content into a short summary with key points.",
    why="Readers decide in seconds whether to read on; a faithful summary respects that.",
    do="Summarise faithfully in at most two sentences, then list up to four key points. Add no facts.",
    inp={"text": "str", "sentences?": "int"}, out=NOTE, present="annotate", binds=["Text", "Markdown", "Card", "Thread"],
    untrusted=["text"], ex={"text": LONG},
    reflex=lambda i, c: note(T.title_of(i["text"]) or "Summary", T.summarize(i["text"], int(i.get("sentences") or 2)),
                             T.key_points(i["text"], 3, T.summarize(i["text"], int(i.get("sentences") or 2))), 0.6, "ai"))

cap("content.tone_harmonize", "Tone Harmonizer",
    "Brings a set of interface strings into one consistent voice.",
    why="Copy written by ten people over three years reads like it.",
    do="Rewrite each text in the described voice. Same meaning, same order, similar length.",
    inp={"texts": ["str"], "voice": "str"}, out={"texts": ["str"]}, present="transform",
    ex={"texts": ["Error: You must enter a valid email!", "Unable to save."], "voice": "friendly"},
    reflex=lambda i, c: {"texts": [T.retone(t, i["voice"]) for t in i["texts"]]})

cap("content.tour", "Onboarding Tour Author",
    "Writes a guided tour for a screen: which elements to introduce, in what order, with one sentence each.",
    why="Product tours go stale the moment the UI changes; generating them from the scene keeps them true.",
    do="Choose up to six elements worth introducing and write a title and one-sentence body for each. Use element ids as targets.",
    inp={"scene?": "any", "audience?": "str"}, out={"steps": [{"target": "str", "title": "str", "body": "str"}]},
    present="annotate", binds=["Tour"], uses_scene=True,
    ex={"scene": {"type": "Page", "props": {"title": "Orders"}, "children": [{"type": "Search", "id": "q", "props": {"name": "q"}},
                                                                          {"type": "Table", "id": "orders", "props": {"rows": [], "columns": []}}]}},
    reflex=lambda i, c: {"steps": S.tour(scene_in(i, c))})


def _help(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    label, kind = i.get("label") or "this field", (i.get("kind") or "").lower()
    low = label.lower()
    body = ("We use your %s to contact you about your account." % low if re.search(r"(email|phone)", low) else
            "Choose something your team will recognise." if "name" in low else
            "Pick the option that best matches; you can change it later." if kind in ("select", "radiogroup") else
            "Enter the %s. You can edit this later." % low)
    return note(label, body, [], 0.55, "info")


cap("content.help", "Contextual Help",
    "Writes the helper text or tooltip for any control: why it is asked and what a good answer looks like.",
    why="People abandon forms at fields whose purpose they do not understand.",
    do="Write one or two sentences of help for the control: why it is needed and what to enter.",
    inp={"label": "str", "kind?": "str", "context?": "str"}, out=NOTE, present="ask", binds=["Input", "Select", "Toggle"],
    max_out=200, ex={"label": "Work email", "kind": "input"}, reflex=_help)


def _whats_new(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    before = C.normalize(C.from_transport(i["before"]))[0] if isinstance(i.get("before"), dict) else None
    changes = C.diff(before, scene_in({"scene": i.get("after")}, c))
    verbs = {"added": "New", "removed": "Removed", "changed": "Updated", "replaced": "Replaced"}
    bullets = ["%s: %s" % (verbs[ch["op"]], ch["text"] or ch["type"]) for ch in changes[:5]]
    return note("What's new", "%d change%s since you last saw this screen." % (len(changes), "" if len(changes) == 1 else "s"), bullets, 0.9, "info")


cap("content.whats_new", "What's-New from Scene Diff",
    "Writes a “what changed” note by comparing two versions of a screen.",
    why="Changelogs are written for releases; people need them per screen, at the moment they return.",
    do="Describe the differences in facts as user-facing changes: what is new, updated or gone. Skip cosmetic changes.",
    inp={"before": "any", "after": "any"}, out=NOTE, present="annotate",
    ex={"before": {"type": "Page", "props": {"title": "Orders"}, "children": [{"type": "Table", "id": "t", "props": {"rows": []}}]},
        "after": {"type": "Page", "props": {"title": "Orders"}, "children": [{"type": "Search", "id": "q", "props": {"name": "q"}}, {"type": "Table", "id": "t", "props": {"rows": []}}]}},
    facts=lambda i, c: {"changes": C.diff(C.normalize(C.from_transport(i["before"]))[0], C.normalize(C.from_transport(i["after"]))[0])},
    reflex=_whats_new)

cap("content.notify", "Notification Triage",
    "Rewrites notifications to be scannable, ranks them by urgency and decides which may interrupt.",
    why="Every notification competes for the same attention; most should wait.",
    do="For each notification give a priority (high, medium, low), a delivery decision (now, defer, digest) and a rewrite under 90 characters.",
    inp={"items": ["str"], "busy?": "bool"},
    out={"items": [{"index": "int", "priority": "enum:high|medium|low", "deliver": "enum:now|defer|digest", "rewrite": "str"}]},
    present="service", ex={"items": ["Payment failed for Globex — card declined", "Weekly digest is ready", "@you Mira commented on the Q3 plan"], "busy": True},
    reflex=lambda i, c: {"items": [{k: r[k] for k in ("index", "priority", "deliver", "rewrite")} for r in B.triage(i["items"], bool(i.get("busy")))]})


def _truncate(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    text, limit = i["text"], int(i.get("max") or 40)
    if len(text) <= limit:
        return {"text": text, "rationale": "Already fits."}
    if len(text.split()) > 9 or text.rstrip().endswith((".", "!", "?")):
        clause = re.split(r"(?<=[,;:])\s+|\s+(?:and|but|because|which|so)\s+", text)[0].rstrip(",;:.")
        if len(clause) < limit and len(clause) < len(text.rstrip(".")):
            return {"text": clause + "…", "rationale": "Kept the leading clause, which carries the main statement."}
        return {"text": T.clip(text, limit), "rationale": "Cut at a word boundary; the sentence has no shorter complete clause."}
    short = re.sub(r"\s*\([^)]*\)", "", text)
    for a, b in (("and", "&"), ("Department", "Dept"), ("Management", "Mgmt"), ("International", "Intl"), ("Corporation", "Corp"),
                 ("Incorporated", "Inc"), ("Number", "No."), ("Quarter", "Q"), ("approximately", "~"), ("versus", "vs")):
        short = re.sub(r"\b%s\b" % a, b, short)
    if len(short) > limit:
        short = " ".join(w for w in short.split() if w.lower() not in ("the", "a", "an", "of", "for", "to"))
    return {"text": T.clip(short, limit), "rationale": "Dropped asides and filler before cutting; key nouns kept."}


cap("content.truncate", "Semantic Truncation",
    "Shortens text to fit a space by meaning — abbreviating and dropping filler — instead of cutting mid-thought.",
    why="An ellipsis hides the one word that mattered.",
    do="Shorten the text to at most the character limit while keeping its distinguishing information. Abbreviate before you cut.",
    inp={"text": "str", "max": "int"}, out=TEXT, present="transform", binds=["Text", "Heading", "Badge", "Tab"], max_out=120,
    ex={"text": "Quarterly Revenue Report for the International Sales Department (draft)", "max": 34}, reflex=_truncate)

cap("content.title", "Title Generator",
    "Proposes a concise title for user content — a document, a ticket, a thread.",
    why="Untitled items are unfindable items.",
    do="Write a specific title of at most seven words in sentence case. No quotation marks.",
    inp={"text": "str"}, out=TEXT, present="fill", binds=["Input", "Heading"], untrusted=["text"], max_out=80, ex={"text": LONG},
    reflex=lambda i, c: {"text": T.title_of(i["text"]), "rationale": "Taken from the leading statement."})


def _consent(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    t = i["text"]
    flags = [("Shares data with third parties", r"third[- ]part|partners|affiliates"), ("Renews automatically", r"auto(matically)?[- ]renew|recurring"),
             ("Marketing messages", r"marketing|promotional|newsletter"), ("Can change terms", r"modify|amend|change (these|the) terms"),
             ("Data kept after closing", r"retain|retention|after (termination|closing)")]
    hits = [label for label, pattern in flags if re.search(pattern, t, re.IGNORECASE)]
    return note("In plain words", T.simplify(T.summarize(t, 2)), hits, 0.55, "warning" if hits else "info")


cap("content.consent", "Consent Simplifier",
    "Explains consent and legal text in plain words and flags the clauses people usually miss.",
    why="Consent nobody understands is not consent.",
    do="Explain what the person is agreeing to in two plain sentences, then flag notable clauses (sharing, renewal, marketing, retention) as bullets.",
    inp={"text": "str"}, out=NOTE, present="annotate", binds=["Checkbox", "Text", "Markdown"], untrusted=["text"],
    ex={"text": "By continuing you agree that we may share usage data with partners and that your subscription will automatically renew until cancelled."},
    reflex=_consent)

cap("content.emoji", "Semantic Emoji Suggestions",
    "Suggests fitting emoji for a message or status.",
    why="A well-chosen emoji is a scannable status; a random one is noise.",
    do="Suggest up to three emoji that match the text's meaning, most fitting first.",
    inp={"text": "str"}, out=ITEMS, present="suggest", binds=["Input", "TextArea"], max_out=120, ex={"text": "Launch went great, thanks team"},
    reflex=lambda i, c: items(G.match_emoji(i["text"])))

cap("content.faq", "FAQ Synthesis",
    "Builds a question-and-answer section from existing content.",
    why="Support questions repeat; the answers usually already exist in prose.",
    do="Compose a Stack of Disclosure components, one per likely question, each answered only from the text.",
    inp={"text": "str"}, out=SCENE, present="compose", binds=["Generative"], untrusted=["text"], ex={"text": LONG},
    reflex=lambda i, c: scene(S.faq(i["text"]), "One collapsible answer per distinct statement."))

# --- workflow & agentic -----------------------------------------------------------
cap("flow.goal_wizard", "Goal-to-Wizard",
    "Turns a stated goal into a multi-step wizard with the right fields at each step.",
    why="Wizards are the right pattern for unfamiliar tasks and tedious to hand-build for each one.",
    do="Design a wizard for the goal: a Steps indicator, the first step's fields in a Form, and navigation buttons.",
    inp={"goal": "str"}, out=SCENE, present="compose", tier="balanced", binds=["Generative"], uses_actions=True, max_out=2200,
    ex={"goal": "invite a new team member and set their access"}, reflex=lambda i, c: scene(*S.goal_wizard(i["goal"])))


def _steps(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    steps, known = i.get("steps") or [], i.get("known") if isinstance(i.get("known"), dict) else {}
    skip = [s for s in steps if any(k.lower() in str(s).lower() for k in known)]
    todo = [s for s in steps if s not in skip]
    return {"next": str(todo[0]) if todo else "", "skip": [str(s) for s in skip],
            "rationale": "Skipped %d step%s already answered by known values." % (len(skip), "" if len(skip) == 1 else "s")}


cap("flow.step_predict", "Step Prediction & Skipping",
    "Chooses the next step of a flow and skips steps whose answers are already known.",
    why="Asking for information the system already has is the most avoidable friction there is.",
    do="Given the steps and the known values, return the next step to show and the steps that can be skipped, with the reason.",
    inp={"steps": ["str"], "known?": "any"}, out={"next": "str", "skip": ["str"], "rationale": "str"}, present="service", binds=["Steps"],
    ex={"steps": ["Email", "Company", "Billing address", "Review"], "known": {"email": "ada@analytical.io", "company": "Analytical"}}, reflex=_steps)


def _approval(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    name, args = i.get("action") or "", i.get("args") if isinstance(i.get("args"), dict) else {}
    risk = B.risk_of(name, i.get("description") or "")
    why = {"high": "Irreversible or moves money; requires explicit approval.", "medium": "Changes shared data or contacts someone.",
           "low": "Read-only or easily undone."}[risk]
    node = S.N("Approval", title=T.sentence_case(name.replace("_", " ")), summary=i.get("description") or why, risk=risk, agent=i.get("agent"),
               details=[{"key": S.label_of(k), "value": str(v)} for k, v in args.items()])
    return {"risk": risk, "reason": why, "requiresApproval": risk != "low", "scene": C.to_transport(node)}


cap("flow.approval", "Risk-Rated Approval",
    "Rates the risk of an agent-proposed action and renders a human-in-the-loop approval card.",
    why="Agents should act freely where it is safe and stop where it is not; the line must be explicit.",
    do="Rate the action's risk (low, medium, high) from what it does and its arguments, explain why, and compose an Approval component summarising it.",
    inp={"action": "str", "args?": "any", "description?": "str", "agent?": "str"},
    out={"risk": "enum:low|medium|high", "reason": "str", "requiresApproval": "bool", "scene": "node"}, present="compose", binds=["Approval"],
    ex={"action": "refund_order", "args": {"order": "#4821", "amount": "$129.00"}, "description": "Refund the customer's last order", "agent": "Billing agent"},
    reflex=_approval)

def _timeline(raw: List[Any]) -> Dict[str, Any]:
    """Plain-language agent timeline from raw tool calls or from steps that already carry a title and status."""
    rows = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        status = s.get("status") if s.get("status") in ("done", "running", "pending", "failed") else (
            "done" if s.get("ok") else ("failed" if s.get("ok") is False else "pending"))
        title = s.get("title") or T.sentence_case(str(s.get("tool", "step")).split(".")[-1].replace("_", " "))
        rows.append({"title": str(title), "status": status, "detail": s.get("detail") or s.get("note"), "tool": s.get("tool")})
    count = lambda state: sum(1 for r in rows if r["status"] == state)
    parts = ["%d of %d steps completed" % (count("done"), len(rows))]
    if count("running"):
        parts.append("%d in progress" % count("running"))
    if count("failed"):
        parts.append("%d failed" % count("failed"))
    if count("pending"):
        parts.append("%d to go" % count("pending"))
    return {"steps": rows, "summary": ", ".join(parts) + "."}


cap("flow.timeline", "Agent Activity Timeline",
    "Explains what an agent did, step by step, in language a non-engineer can audit.",
    why="Autonomy without an audit trail is unaccountable.",
    do="Rewrite the raw agent steps as short plain-language timeline entries with a status each. Keep order; hide internals.",
    inp={"steps": ["any"]}, out={"steps": [{"title": "str", "status": "enum:done|running|pending|failed", "detail?": "str", "tool?": "str"}], "summary": "str"},
    present="annotate", binds=["AgentTimeline"],
    ex={"steps": [{"tool": "ocr.read", "ok": True, "note": "invoice_204.pdf"}, {"tool": "crm.match_vendor", "ok": True}, {"tool": "ledger.post", "ok": False, "note": "period closed"}]},
    reflex=lambda i, c: _timeline(i["steps"]))

cap("flow.decompose", "Task Decomposition Board",
    "Breaks a goal into concrete tasks and lays them out as a Now / Next / Later board.",
    why="Large goals stall until someone writes down the first three tasks.",
    do="Decompose the goal into four to eight concrete tasks and arrange them in a Board with columns Now, Next and Later.",
    inp={"goal": "str"}, out=SCENE, present="compose", tier="balanced", binds=["Generative", "Board"],
    ex={"goal": "launch the customer referral programme"}, reflex=lambda i, c: scene(*S.decompose(i["goal"])))

cap("flow.handoff", "Handoff Summary",
    "Writes the note a colleague needs to take over a task: state, decisions, open questions, next step.",
    why="Context lost at handoff is the most expensive kind of rework.",
    do="Write a handoff: a one-line state, then bullets for decisions made, open questions and the immediate next step.",
    inp={"text": "str", "to?": "str"}, out=NOTE, present="service", untrusted=["text"], ex={"text": LONG, "to": "Noor"},
    reflex=lambda i, c: note("Handoff%s" % (" for " + i["to"] if i.get("to") else ""), T.summarize(i["text"], 1),
                             T.key_points(i["text"], 4, T.summarize(i["text"], 1)), 0.55, "info"))

cap("flow.rules", "Rule Builder",
    "Converts “when X happens, do Y” into a structured automation rule bound to registered actions.",
    why="Automation UIs with condition builders are powerful and intimidating; a sentence is neither.",
    do="Parse the rule into a trigger, conditions (field, op, value) and one registered action with JSON arguments. Use 'none' if no action fits.",
    inp={"text": "str", "actions?": ["any"]},
    out={"trigger": "str", "conditions": [{"field": "str", "op": "str", "value": "str"}], "action": "str", "args": "json", "summary": "str", "confidence": "num"},
    present="service", uses_actions=True, post=parse_args, ex={"text": "when amount is over 5000 then export the report", "actions": DEMO_ACTIONS},
    reflex=lambda i, c: (lambda r: dict(r, args=json.dumps(r["args"])))(B.parse_rule(i["text"], acts(i, c))))


def _batch(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    spec = D.nl_query(i["description"], i["rows"])
    rows = D.apply_query(i["rows"], spec)
    verb = next((w for w in T.words(i["description"]) if w in ("archive", "delete", "remove", "export", "tag", "assign", "close", "send", "approve", "refund")), "select")
    return {"verb": verb, "matched": len(rows), "total": len(i["rows"]), "risk": B.risk_of(verb), "explanation": spec["explanation"],
            "indices": [i["rows"].index(r) for r in rows][:500]}


cap("flow.batch", "Batch-by-Description",
    "Selects the records a bulk operation applies to from a description, and previews the impact before anything runs.",
    why="Bulk actions are where a mis-click costs the most; a described, previewed selection is safer than checkboxes.",
    do="Identify the operation verb and translate the description into the matching rows using facts. Rate the risk.",
    inp={"description": "str", "rows": ["any"]},
    out={"verb": "str", "matched": "int", "total": "int", "risk": "enum:low|medium|high", "explanation": "str", "indices": ["int"]},
    present="service", binds=["Table"],
    ex={"description": "archive everything with status draft", "rows": D.fixtures(["id", "customer", "status"], 8)}, facts=_batch, reflex=_batch)


def _review(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    vals = i.get("values") if isinstance(i.get("values"), dict) else {}
    issues = []
    for k, v in vals.items():
        s = str(v).strip()
        if s.lower() in ("test", "asdf", "n/a", "tbd", "xxx"):
            issues.append("“%s” in %s looks like a placeholder" % (s, k))
        if "email" in k.lower() and s and not re.fullmatch(r"[^@\s]+@[^@\s]+\.\w{2,}", s):
            issues.append("%s is not a complete email address" % k)
        if re.search(r"(amount|total|price|qty|quantity)", k.lower()) and (D.to_number(v) or 0) <= 0 and s:
            issues.append("%s is zero or negative" % k)
    start, end = vals.get("start_date") or vals.get("start"), vals.get("end_date") or vals.get("end")
    if start and end and str(end) < str(start):
        issues.append("the end date is before the start date")
    if issues:
        return verdict(False, "Before you submit: " + "; ".join(issues) + ".", "warning", "Review the highlighted values.")
    return verdict(True, "Everything looks consistent.")


cap("flow.review", "Pre-Submit Review",
    "Reads a completed form as a careful colleague would and flags inconsistencies before submission.",
    why="Cross-field mistakes — end before start, a placeholder left in — pass every per-field validator.",
    do="Check the values together for contradictions, placeholders and implausible entries. Report kindly in one sentence, or confirm all is consistent.",
    inp={"values": "any", "context?": "str"}, out=VERDICT, present="validate", binds=["Form", "SmartForm"],
    ex={"values": {"email": "ada@analytical", "start_date": "2027-03-10", "end_date": "2027-03-02", "amount": 0}}, reflex=_review)


def _recover(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    e = (i.get("error") or "").lower()
    table = [(r"network|offline|timeout|fetch|econn|502|503|504", "We lost the connection", "Your work is saved locally.", ["Check your connection", "Retry now"]),
             (r"401|unauthori|session|expired|token", "Your session ended", "Sign in again to continue where you left off.", ["Sign in", "Your draft is kept"]),
             (r"403|forbidden|permission|denied", "You don't have access", "Ask a workspace admin for permission.", ["Request access", "Go back"]),
             (r"404|not found|missing", "We can't find that", "It may have been moved or deleted.", ["Search for it", "Go to the overview"]),
             (r"409|conflict|stale|modified", "Someone else changed this", "Review their changes before saving yours.", ["Compare versions", "Reload"]),
             (r"429|rate|quota|limit", "Too many requests", "Wait a moment; nothing was lost.", ["Retry in a minute"]),
             (r"valid|required|invalid", "Some details need attention", "Fix the highlighted fields and submit again.", ["Review fields"])]
    for pattern, title, body, steps in table:
        if re.search(pattern, e):
            return note(title, body, steps, 0.75, "warning")
    return note("Something went wrong", "Nothing was lost. Try again, and contact support if it continues.", ["Retry", "Copy error details"], 0.4, "warning")


cap("flow.recover", "Error Recovery Guide",
    "Turns a failure into a recovery path: what happened, what is safe, what to do next.",
    why="Error pages state the problem and stop; people need the way out.",
    do="Explain the error in one calm sentence, say what was preserved, and list up to three concrete recovery steps.",
    inp={"error": "str", "context?": "str"}, out=NOTE, present="annotate", binds=["Callout", "EmptyState", "Banner"],
    ex={"error": "HTTP 409 Conflict: record modified by another user"}, reflex=_recover)

cap("flow.checkpoint", "Named Checkpoints",
    "Names a point in a session from what changed, so people can return to “before I changed the pricing table”.",
    why="Version numbers are for machines; people navigate history by meaning.",
    do="Write a short descriptive name (under six words) and a one-line description for this checkpoint from the changes.",
    inp={"changes": ["str"]}, out={"name": "str", "description": "str"}, present="service", max_out=120,
    ex={"changes": ["Renamed plan Scale to Growth", "Raised price from $29 to $35"]},
    reflex=lambda i, c: {"name": T.clip(T.title_case(" ".join(T.keywords(" ".join(i["changes"]), 3))) or "Checkpoint", 40),
                         "description": "; ".join(str(x) for x in i["changes"][:3])})

# --- collaboration ---------------------------------------------------------------------
THREAD = [{"author": "Mira", "content": "Can we ship the importer Friday?"}, {"author": "Noor", "content": "Only if we defer deduplication. Agreed to ship mapping first."},
          {"author": "Ada", "content": "I will write the migration guide by Thursday."}]


def _join(msgs: Any) -> str:
    return " ".join("%s: %s" % (m.get("author", ""), m.get("content", "")) if isinstance(m, dict) else str(m) for m in (msgs or []))


cap("collab.thread_summary", "Thread Summary",
    "Summarises a discussion thread: where it stands, who said what matters, what is unresolved.",
    why="Catching up on a 60-message thread is how afternoons disappear.",
    do="Summarise the thread in two sentences, then list key points attributed by name. Add nothing that was not said.",
    inp={"messages": ["any"]}, out=NOTE, present="annotate", binds=["Thread"], untrusted=["messages"], ex={"messages": THREAD},
    reflex=lambda i, c: note("Thread summary", T.summarize(_join(i["messages"]), 2), T.key_points(_join(i["messages"]), 3), 0.55, "ai"))


def _merge(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    a, b, base = str(i.get("mine") or ""), str(i.get("theirs") or ""), str(i.get("base") or "")
    if a == b:
        return {"resolution": a, "strategy": "identical", "explanation": "Both edits are the same.", "confidence": 1.0}
    if a == base:
        return {"resolution": b, "strategy": "take_theirs", "explanation": "Only the other edit changed the text.", "confidence": 0.95}
    if b == base:
        return {"resolution": a, "strategy": "take_mine", "explanation": "Only your edit changed the text.", "confidence": 0.95}
    sa, sb = T.sentences(a), T.sentences(b)
    merged = sa + [s for s in sb if s not in sa]
    return {"resolution": " ".join(merged), "strategy": "combine", "explanation": "Both edits changed the text; kept every distinct sentence. Review before saving.", "confidence": 0.45}


cap("collab.merge", "Edit Conflict Mediator",
    "Proposes a merged version when two people edit the same text, and explains what it kept from each.",
    why="“Your changes could not be saved” makes people choose whose work to destroy.",
    do="Merge the two edits against the base. Keep both people's intent where compatible; where not, choose and explain. State your confidence.",
    inp={"base": "str", "mine": "str", "theirs": "str"},
    out={"resolution": "str", "strategy": "enum:identical|take_mine|take_theirs|combine", "explanation": "str", "confidence": "num"},
    present="service", untrusted=["base", "mine", "theirs"],
    ex={"base": "Ship on Friday.", "mine": "Ship on Friday. Mira owns QA.", "theirs": "Ship on Friday. Docs go out Thursday."}, reflex=_merge)

cap("collab.reply", "Smart Replies",
    "Offers three short, distinct replies to a message: agree, decline, ask.",
    why="Most replies are one of a few speech acts; composing them from scratch is busywork.",
    do="Write three distinct replies under 15 words each: one accepting, one declining politely, one asking a clarifying question.",
    inp={"message": "str"}, out=ITEMS, present="suggest", binds=["Thread", "TextArea"], untrusted=["message"], max_out=200,
    ex={"message": "Can we ship the importer Friday?"},
    reflex=lambda i, c: items([{"label": "Yes, that works for me.", "value": "Yes, that works for me."},
                               {"label": "I can't commit to that yet.", "value": "I can't commit to that yet."},
                               {"label": "What needs to be ready by then?" if "?" in i["message"] else "Can you share more detail?",
                                "value": "What needs to be ready by then?" if "?" in i["message"] else "Can you share more detail?"}]))


def _cool(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    h = T.heat(i["text"])
    if h >= 0.45:
        return verdict(False, "This may read as harsher than you intend.", "warning", T.retone(T.sentence_case(i["text"]), "empathetic"))
    return verdict(True, "Reads as measured.")


cap("collab.cooldown", "Cool-Down Nudge",
    "Notices when a draft message reads as heated and offers a calmer version before it is sent.",
    why="Messages sent in frustration cost more than the minute it takes to rephrase them.",
    do="Judge whether the draft would read as hostile or heated to its recipient. If so, give a calmer rewrite that keeps the point.",
    inp={"text": "str"}, out=VERDICT, present="validate", binds=["TextArea"], untrusted=["text"],
    ex={"text": "THIS IS RIDICULOUS!!! The worst rollout ever, useless."}, reflex=_cool)

cap("collab.decisions", "Decision Log",
    "Extracts decisions and owners from a discussion into a durable log.",
    why="Decisions made in chat are lost in chat.",
    do="List each explicit decision with its owner and due date if stated. Do not infer decisions that were not made.",
    inp={"messages": ["any"]}, out={"decisions": [{"decision": "str", "owner?": "str", "due?": "str"}]}, present="service", binds=["Thread"],
    untrusted=["messages"], ex={"messages": THREAD},
    reflex=lambda i, c: {"decisions": T.decisions(i["messages"])})

cap("collab.mention", "Mention & Reviewer Suggestions",
    "Suggests who to mention or ask for review from the content and each person's expertise.",
    why="Work stalls when the right person is not in the loop and nobody knows who that is.",
    do="Rank the people by relevance of their expertise to the text. Return the top three with the reason as detail.",
    inp={"text": "str", "people": [{"name": "str", "expertise": "str"}]}, out=ITEMS, present="suggest", binds=["TextArea", "Thread"],
    ex={"text": "The CSV importer mis-parses dates in column mapping", "people": [{"name": "Ada", "expertise": "data import, parsing"},
                                                                                 {"name": "Noor", "expertise": "billing, invoices"}]},
    reflex=lambda i, c: items([{"label": i["people"][h["index"]]["name"], "value": i["people"][h["index"]]["name"],
                                "detail": i["people"][h["index"]]["expertise"], "score": h["score"], "icon": "user"}
                               for h in D.search(i["text"], [p["expertise"] for p in i["people"]], 3)]))

cap("collab.recap", "Meeting Recap Card",
    "Turns meeting notes or a transcript into a recap card: summary, decisions, next steps.",
    why="The recap is the only artefact of most meetings, and usually nobody writes it.",
    do="Compose a Card with a two-sentence summary, a Decisions list and a Next steps list with owners. Use only what was said.",
    inp={"text": "str"}, out=SCENE, present="compose", binds=["Generative"], untrusted=["text"], ex={"text": LONG},
    reflex=lambda i, c: scene(S.recap(i["text"]), "Summary, then decisions, then follow-ups."))

# --- ambient ---------------------------------------------------------------------------------
cap("ambient.loading_story", "Narrative Loading States",
    "Replaces a spinner with a short account of what is actually happening.",
    why="Waits feel shorter when people know what they are waiting for.",
    do="Write three to four short progress phrases (under five words each) describing the stages of the task, in order.",
    inp={"task": "str"}, out={"steps": ["str"]}, present="transform", binds=["Thinking", "Skeleton", "Progress"], max_out=120,
    ex={"task": "importing a CSV of customers"},
    reflex=lambda i, c: {"steps": ["Reading %s" % (T.keywords(i["task"], 1) or ["data"])[0], "Checking the details", "Putting it together", "Almost ready"]})

cap("ambient.empathy", "Empathic Error Tone",
    "Rephrases system messages with care when the situation is stressful — failures, losses, declines.",
    why="The moment something fails is the moment tone matters most.",
    do="Rewrite the message calmly and kindly: acknowledge, state what is safe, say the next step. No blame, no exclamation marks.",
    inp={"text": "str"}, out=TEXT, present="transform", binds=["Callout", "Banner", "Text"],
    ex={"text": "Error: payment declined! You must use a valid card."},
    reflex=lambda i, c: {"text": T.retone(i["text"], "empathetic"), "rationale": "Acknowledges the problem before instructing."})


def _celebrate(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    e = i["event"].lower()
    big = bool(re.search(r"(first|100|1000|milestone|launch|complete|goal|record|anniversary)", e))
    return {"celebrate": big or bool(re.search(r"(done|paid|shipped|won|closed)", e)), "intensity": "big" if big else "subtle",
            "message": "%s — nicely done." % T.sentence_case(i["event"].rstrip(".!")), "effect": "confetti" if big else "check"}


cap("ambient.celebrate", "Celebration Moments",
    "Decides whether an event deserves celebration, how much, and what to say.",
    why="Delight that fires on every click is noise; delight that fires on real milestones is memory.",
    do="Decide if the event merits celebration and at what intensity (subtle or big). Write one warm sentence without exclamation marks.",
    inp={"event": "str"}, out={"celebrate": "bool", "intensity": "enum:subtle|big", "message": "str", "effect": "enum:none|check|confetti"},
    present="service", max_out=120, ex={"event": "first invoice paid"}, reflex=_celebrate)

cap("ambient.nudge", "Gentle Nudges",
    "Spots stalled work and proposes one considerate reminder, with the reason it matters now.",
    why="Reminders work when they are rare, specific and well-timed.",
    do="From the stalled items choose the one most worth a reminder and write a single considerate nudge with the reason.",
    inp={"items": [{"title": "str", "idleDays": "num"}]}, out=ITEMS, present="suggest", binds=["Suggestions", "List"],
    ex={"items": [{"title": "Reply to Globex renewal", "idleDays": 6}, {"title": "Review Q3 plan", "idleDays": 2}]},
    reflex=lambda i, c: items([{"label": "Pick up “%s”?" % r["title"], "detail": "Untouched for %d days." % r["idleDays"], "value": r["title"],
                                "score": min(1.0, r["idleDays"] / 7.0), "icon": "clock"}
                               for r in sorted(i["items"], key=lambda r: -r["idleDays"])[:1]]))

cap("ambient.sentiment", "Sentiment Lens",
    "Reads the sentiment of customer text and summarises it as a tone, a score and the phrases that drove it.",
    why="Support queues and reviews are easier to triage when mood is visible at a glance.",
    do="Classify the sentiment and give a one-sentence reading plus the phrases that most influenced it.",
    inp={"text": "str"}, out=NOTE, present="annotate", binds=["Thread", "Text", "List"], untrusted=["text"],
    ex={"text": "The app crashed again and I am frustrated. Support was slow."},
    reflex=lambda i, c: (lambda s: note("%s sentiment" % s[0].capitalize(), "Polarity %+.2f on a −1 to 1 scale." % s[1],
                                        [w for w in T.words(i["text"]) if w in T._NEG or w in T._POS][:4], 0.6,
                                        {"positive": "success", "negative": "danger", "neutral": "neutral"}[s[0]]))(T.sentiment(i["text"])))

cap("ambient.pacing", "Session Pacing",
    "Notices long sessions and late-session error clusters, and protects the work before suggesting a pause.",
    why="Tired people make mistakes; software can save first and suggest second.",
    do="From the session profile decide whether the person is fresh, in a long session or fatigued; return protective directives.",
    inp={"durationMinutes": "num", "events?": ["any"]}, out=DIRECTIVES, present="observe", consent="personalization",
    ex={"durationMinutes": 75, "events": [{"t": 4_300_000 + n * 1000, "kind": "error", "target": "amount"} for n in range(4)]},
    reflex=lambda i, c: directives(B.pacing(i.get("events") or c.signals, float(i["durationMinutes"]) * 60000)))

cap("ambient.priority", "Attention Prioritiser",
    "Ranks everything competing for attention on a screen and names the one thing to look at first.",
    why="When everything is highlighted, nothing is.",
    do="Rank the items by how much they deserve attention right now and say which single item comes first and why.",
    inp={"items": ["str"]}, out=ITEMS, present="suggest", binds=["List", "Suggestions"],
    ex={"items": ["Weekly digest ready", "Payment failed for Globex", "New comment from Mira"]},
    reflex=lambda i, c: items([{"label": r["text"], "detail": "%s priority" % r["priority"], "score": r["score"], "value": str(r["index"])}
                               for r in B.triage(i["items"])]))

cap("ambient.greeting", "Contextual Greeting",
    "Writes a greeting that reflects the time of day and what awaits, instead of a static “Welcome back”.",
    why="The first line of a screen sets the tone for the session.",
    do="Write a greeting of at most twelve words that fits the local time and mentions the most relevant pending item.",
    inp={"name?": "str", "pending?": "str"}, out=TEXT, present="transform", binds=["Heading", "Hero", "Page"], max_out=80,
    ex={"name": "Mira", "pending": "3 invoices to approve"},
    reflex=lambda i, c: {"text": "Good %s%s%s" % ("morning" if c.now.hour < 12 else ("afternoon" if c.now.hour < 18 else "evening"),
                                                  ", " + i["name"] if i.get("name") else "", " — " + i["pending"] if i.get("pending") else ""),
                         "rationale": "Time of day plus the top pending item."})
