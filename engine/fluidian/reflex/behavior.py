"""Reflex behaviour models and command understanding.

Interaction signals are small event records collected by the runtime::

    {"t": 15230, "kind": "click", "target": "save", "meta": "…"}

``kind`` is one of click, input, key, shortcut, nav, error, help, undo, back,
submit, scroll, hover, deadclick.  ``t`` is milliseconds since session start.
Signals never contain typed values.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from . import data as D
from . import parse as P
from . import text as T

Event = Dict[str, Any]


def _d(kind: str, reason: str, target: Optional[str] = None, value: Optional[str] = None) -> Dict[str, Any]:
    return {"kind": kind, "target": target, "value": value, "reason": reason}


def profile(events: List[Event]) -> Dict[str, Any]:
    """Aggregate raw signals into rates the adaptive capabilities reason over."""
    events = sorted((e for e in events if isinstance(e, dict)), key=lambda e: e.get("t", 0))
    kinds: Dict[str, int] = {}
    for e in events:
        kinds[str(e.get("kind"))] = kinds.get(str(e.get("kind")), 0) + 1
    span = max(1.0, (events[-1].get("t", 0) - events[0].get("t", 0)) / 1000.0) if len(events) > 1 else 1.0
    rage = 0
    clicks = [e for e in events if e.get("kind") in ("click", "deadclick")]
    for i in range(2, len(clicks)):
        a, c = clicks[i - 2], clicks[i]
        if a.get("target") == c.get("target") == clicks[i - 1].get("target") and c.get("t", 0) - a.get("t", 0) <= 1200:
            rage += 1
    navs = [e for e in events if e.get("kind") == "nav"]
    ping = sum(1 for i in range(2, len(navs)) if navs[i].get("target") == navs[i - 2].get("target")
               and navs[i].get("t", 0) - navs[i - 2].get("t", 0) < 8000)
    gaps = [events[i].get("t", 0) - events[i - 1].get("t", 0) for i in range(1, len(events))]
    actions = max(1, kinds.get("click", 0) + kinds.get("shortcut", 0) + kinds.get("key", 0))
    return {"count": len(events), "seconds": round(span, 1), "kinds": kinds, "rageClicks": rage, "navPingPong": ping,
            "errors": kinds.get("error", 0), "help": kinds.get("help", 0), "undo": kinds.get("undo", 0) + kinds.get("back", 0),
            "deadClicks": kinds.get("deadclick", 0), "hesitations": sum(1 for g in gaps if g > 8000),
            "shortcutRatio": round((kinds.get("shortcut", 0)) / actions, 2), "perMinute": round(len(events) / span * 60, 1)}


def expertise(events: List[Event]) -> Dict[str, Any]:
    p = profile(events)
    score = 0.5 + 0.9 * p["shortcutRatio"] + min(0.25, p["perMinute"] / 240.0) - 0.08 * p["help"] - 0.05 * p["hesitations"] - 0.04 * p["errors"]
    score = max(0.0, min(1.0, score))
    level = "expert" if score >= 0.7 else ("novice" if score < 0.4 else "intermediate")
    directives = []
    if level == "novice":
        directives = [_d("show_hints", "Help opened %d×, %d long pauses." % (p["help"], p["hesitations"])),
                      _d("density", "More whitespace lowers scanning effort.", value="spacious"),
                      _d("offer_tour", "A short tour answers the questions the pauses suggest.")]
    elif level == "expert":
        directives = [_d("hide_hints", "Shortcuts account for %d%% of actions." % int(p["shortcutRatio"] * 100)),
                      _d("density", "Experts trade whitespace for information.", value="compact"),
                      _d("show_shortcuts", "Surface remaining shortcuts next to their buttons.")]
    confidence = min(0.95, 0.35 + p["count"] / 60.0)
    return {"state": level, "confidence": round(confidence, 2), "directives": directives}


def frustration(events: List[Event]) -> Dict[str, Any]:
    p = profile(events)
    score = min(1.0, 0.28 * p["rageClicks"] + 0.16 * p["errors"] + 0.14 * p["navPingPong"] + 0.12 * p["deadClicks"] + 0.06 * p["undo"])
    state = "frustrated" if score >= 0.55 else ("struggling" if score >= 0.3 else "calm")
    directives = []
    if p["rageClicks"]:
        hot = next((e.get("target") for e in reversed(events) if e.get("kind") in ("click", "deadclick")), None)
        directives.append(_d("explain_target", "Repeated rapid clicks suggest this control is not responding as expected.", hot))
    if p["errors"] >= 2:
        last = next((e.get("target") for e in reversed(events) if e.get("kind") == "error"), None)
        directives.append(_d("coach_error", "%d validation errors in a row." % p["errors"], last))
    if state == "frustrated":
        directives.append(_d("offer_help", "Offer the copilot with the current context pre-filled."))
        directives.append(_d("tone", "Switch system messages to the empathetic voice.", value="empathetic"))
    elif p["navPingPong"]:
        directives.append(_d("offer_search", "Moving back and forth usually means something could not be found."))
    return {"state": state, "confidence": round(min(0.95, 0.4 + score * 0.5 + p["count"] / 200.0), 2), "directives": directives}


def predict_focus(events: List[Event], candidates: Optional[List[str]] = None, k: int = 3) -> List[Dict[str, Any]]:
    """First-order Markov prediction of the next target, blended with recency and frequency."""
    seq = [str(e.get("target")) for e in events if e.get("kind") in ("click", "shortcut", "nav", "submit") and e.get("target")]
    if not seq:
        return []
    last = seq[-1]
    trans: Dict[str, int] = {}
    freq: Dict[str, int] = {}
    for a, b in zip(seq, seq[1:]):
        freq[b] = freq.get(b, 0) + 1
        if a == last:
            trans[b] = trans.get(b, 0) + 1
    total_t, total_f = sum(trans.values()) or 1, sum(freq.values()) or 1
    scores = {}
    for target in set(seq) | set(candidates or []):
        if target == last or (candidates and target not in candidates):
            continue
        scores[target] = 0.7 * trans.get(target, 0) / total_t + 0.3 * freq.get(target, 0) / total_f
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    return [{"label": t, "value": t, "score": round(s, 3), "detail": "follows “%s” in %d of %d cases" % (last, trans.get(t, 0), total_t)}
            for t, s in ranked if s > 0]


def nav_reorder(items: List[str], events: List[Event]) -> List[Dict[str, Any]]:
    horizon = max((e.get("t", 0) for e in events), default=0) or 1
    score = {item: 0.0 for item in items}
    count = {item: 0 for item in items}
    for e in events:
        target = str(e.get("target"))
        if e.get("kind") == "nav" and target in score:
            score[target] += 0.5 + 0.5 * (e.get("t", 0) / horizon)
            count[target] += 1
    order = sorted(items, key=lambda i: (-score[i], items.index(i)))
    return [{"label": item, "value": item, "score": round(score[item], 2),
             "detail": "%d visits" % count[item] if count[item] else "not visited yet"} for item in order]


def cognitive_load(stats: Dict[str, Any], events: List[Event]) -> Dict[str, Any]:
    p = profile(events)
    by = stats.get("byType", {})
    interactive = sum(by.get(t, 0) for t in ("Button", "Input", "Select", "TextArea", "Checkbox", "Toggle", "Link", "Tabs", "Search"))
    regions = sum(by.get(t, 0) for t in ("Card", "Section", "Table", "Chart", "Callout", "Banner"))
    load = min(1.0, interactive / 40.0 * 0.5 + regions / 16.0 * 0.3 + p["hesitations"] * 0.08 + stats.get("depth", 0) / 40.0)
    state = "overloaded" if load >= 0.7 else ("busy" if load >= 0.45 else "clear")
    directives = []
    if state != "clear":
        directives.append(_d("collapse_secondary", "%d interactive controls and %d regions compete for attention." % (interactive, regions)))
    if p["hesitations"] >= 2:
        directives.append(_d("highlight_primary", "%d long pauses: point to the next step." % p["hesitations"]))
    if state == "overloaded":
        directives.append(_d("focus_mode", "Offer focus mode to hide everything but the current task."))
    return {"state": state, "confidence": round(0.5 + min(0.4, p["count"] / 100.0), 2), "directives": directives}


def preferences(events: List[Event]) -> Dict[str, Any]:
    prefs: Dict[str, Tuple[str, int]] = {}
    for e in events:
        meta = str(e.get("meta") or "")
        m = re.match(r"^(theme|density|view|locale|sort|font_size):(.+)$", meta)
        if m:
            key, value = m.group(1), m.group(2)
            count = prefs.get(key, (value, 0))[1] + 1 if prefs.get(key, ("", 0))[0] == value else 1
            prefs[key] = (value, count)
    p = profile(events)
    if p["shortcutRatio"] >= 0.3:
        prefs["input"] = ("keyboard", int(p["shortcutRatio"] * 10))
    directives = [_d("set_" + key, "Chosen %d time%s this session." % (count, "" if count == 1 else "s"), value=value)
                  for key, (value, count) in sorted(prefs.items())]
    return {"state": "%d preferences" % len(directives), "confidence": round(min(0.9, 0.4 + 0.1 * len(events) ** 0.5), 2), "directives": directives}


def find_macro(events: List[Event], min_repeat: int = 3) -> Dict[str, Any]:
    """Detect a repeated action sequence worth automating."""
    seq = [str(e.get("target")) for e in events if e.get("kind") in ("click", "submit", "shortcut") and e.get("target")]
    best: Tuple[int, List[str]] = (0, [])
    for length in range(5, 1, -1):
        seen: Dict[Tuple[str, ...], int] = {}
        i = 0
        while i + length <= len(seq):
            gram = tuple(seq[i:i + length])
            if len(set(gram)) > 1:
                seen[gram] = seen.get(gram, 0) + 1
            i += 1
        for gram, count in seen.items():
            if count >= min_repeat and count * length > best[0] * max(1, len(best[1])):
                best = (count, list(gram))
        if best[0]:
            break
    if not best[0]:
        return {"found": False, "name": "", "repeats": 0, "steps": [], "pitch": "No repeated sequence yet."}
    name = "Run “%s → %s”" % (best[1][0], best[1][-1])
    return {"found": True, "name": name, "repeats": best[0], "steps": best[1],
            "pitch": "You have done these %d steps %d times. Save them as one action?" % (len(best[1]), best[0])}


def pacing(events: List[Event], duration_ms: float) -> Dict[str, Any]:
    minutes = duration_ms / 60000.0
    p = profile(events)
    late_errors = sum(1 for e in events if e.get("kind") == "error" and e.get("t", 0) > duration_ms * 0.66)
    directives = []
    state = "fresh"
    if minutes >= 50:
        state = "long-session"
        directives.append(_d("suggest_break", "%.0f minutes of continuous work." % minutes))
    if late_errors >= 3 and p["errors"] and late_errors / p["errors"] > 0.6:
        state = "fatigued"
        directives.append(_d("autosave", "Errors are clustering late in the session; protect the work."))
        directives.append(_d("simplify", "Reduce choices on screen until the pace recovers."))
    return {"state": state, "confidence": 0.6 if directives else 0.5, "directives": directives}


_URGENT = re.compile(r"\b(urgent|asap|immediately|outage|down|failed|security|breach|payment failed|overdue|expires? today|blocked|critical|deadline)\b", re.IGNORECASE)
_LOW = re.compile(r"\b(newsletter|digest|tip|did you know|weekly|promo|offer|suggestion|recommended|new feature)\b", re.IGNORECASE)


def priority_of(text: str) -> Tuple[str, float]:
    if _URGENT.search(text or ""):
        return "high", 0.9
    if _LOW.search(text or ""):
        return "low", 0.2
    mention = bool(re.search(r"@\w+|\byou\b|\byour\b", text or "", re.IGNORECASE))
    return ("medium", 0.6) if mention else ("medium", 0.45)


def triage(items: List[Any], busy: bool = False) -> List[Dict[str, Any]]:
    """Rank notifications and decide whether each should interrupt now."""
    out = []
    for i, item in enumerate(items):
        text = item.get("text") if isinstance(item, dict) else str(item)
        level, score = priority_of(text or "")
        deliver = "now" if level == "high" else ("defer" if busy else ("digest" if level == "low" else "now"))
        out.append({"index": i, "text": text, "priority": level, "score": score, "deliver": deliver,
                    "rewrite": T.clip(T.retone(text or "", "concise"), 90)})
    return sorted(out, key=lambda r: (-r["score"], r["index"]))


# --- command understanding ---------------------------------------------------
_SYN = {"create": {"new", "add", "make", "start", "open", "draft", "compose"}, "delete": {"remove", "trash", "erase", "destroy", "drop"},
        "show": {"open", "view", "see", "display", "go", "list", "find"}, "send": {"email", "mail", "message", "notify", "share"},
        "search": {"find", "lookup", "look", "filter", "query"}, "update": {"edit", "change", "modify", "set", "rename"},
        "export": {"download", "save", "csv", "pdf"}, "invite": {"add", "onboard"}, "refund": {"reimburse", "return"},
        "archive": {"hide", "close", "store"}, "assign": {"give", "delegate", "hand"}, "schedule": {"book", "plan", "calendar"},
        "pay": {"charge", "bill", "invoice"}, "cancel": {"stop", "abort", "end"}, "approve": {"accept", "confirm", "ok"}}
_HIGH = re.compile(r"(delete|remove|destroy|erase|wipe|revoke|terminate|purge|drop|refund|pay|charge|transfer|wire|publish|deploy|send_all|broadcast|reset)", re.IGNORECASE)
_MED = re.compile(r"(send|email|invite|update|edit|change|assign|archive|cancel|export|share|merge|import|schedule)", re.IGNORECASE)


def risk_of(name: str, description: str = "") -> str:
    text = "%s %s" % (name, description)
    return "high" if _HIGH.search(text) else ("medium" if _MED.search(text) else "low")


def _tokens(text: str) -> set:
    base = {w.rstrip("s") if len(w) > 3 else w for w in T.words(re.sub(r"[_\-]+", " ", text))} - T.STOP
    expanded = set(base)
    for canon, alts in _SYN.items():
        if base & (alts | {canon}):
            expanded.add(canon)
    return expanded


def _extract_args(utterance: str, params: Dict[str, Any]) -> Dict[str, Any]:
    args: Dict[str, Any] = {}
    quoted = re.findall(r"[\"“']([^\"”']{1,120})[\"”']", utterance)
    emails = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", utterance)
    numbers = re.findall(r"(?<![\w.])[$€£]?\d[\d,]*(?:\.\d+)?(?:k|m)?\b", utterance)
    codes = re.findall(r"\b[A-Z]{2,}[-_]?\d[\w\-]*\b", utterance)
    for name, spec in (params or {}).items():
        hint = ("%s %s" % (name, spec if isinstance(spec, str) else "")).lower()
        declared = spec.split()[0].lower() if isinstance(spec, str) and spec.split() else ""
        textual = declared in ("string", "str", "text")
        if "email" in hint and emails:
            args[name] = emails.pop(0)
        elif codes and (textual or not declared) and re.search(r"\b(id|code|number|invoice|order|ticket|reference|ref|sku)\b", hint):
            args[name] = codes.pop(0)
        elif re.search(r"\b(date|when|due|day|deadline|time)\b", hint):
            when = P.natural_date(utterance)
            if when["kind"] != "unknown":
                args[name] = when["value"]
        elif not textual and re.search(r"\b(number|int|integer|amount|count|quantity|id|seats|total|price|percent)\b", hint) and numbers:
            q = P.quantity(numbers.pop(0))
            value = D.to_number(q["value"])
            args[name] = int(value) if value is not None and float(value).is_integer() else value
        elif quoted:
            args[name] = quoted.pop(0)
        else:
            m = re.search(r"\b(?:%s)\s+(?:is|to|=|as|named|called|for)?\s*([\w][\w \-]{0,40}?)(?=\s+(?:and|with|for|to|on|by|due|at)\b|[,.;]|$)" % re.escape(name.replace("_", " ")), utterance, re.IGNORECASE)
            if m:
                args[name] = m.group(1).strip()
            else:
                # "open the trust page": the value sits directly before the parameter's name.
                before = re.search(r"\b([\w\-]+)\s+%s\b" % re.escape(name.replace("_", " ")), utterance, re.IGNORECASE)
                if before and before.group(1).lower() not in ("the", "a", "an", "this", "that", "new", "my", "your", "another", "next", "same"):
                    args[name] = before.group(1)
                    continue
                m = re.search(r"\b(?:for|to|named|called|titled)\s+([A-Z][\w&\-]*(?:\s+[A-Z][\w&\-]*){0,3})", utterance)
                if m and re.search(r"\b(name|title|customer|company|user|who|recipient|to|query|text|subject)\b", hint):
                    args[name] = m.group(1).strip()
    return args


def route(utterance: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Map an utterance to the best registered action and extract its arguments."""
    words = _tokens(utterance)
    ranked = []
    for a in actions:
        name = str(a.get("name", ""))
        name_t, desc_t = _tokens(name), _tokens(str(a.get("description", "")))
        score = 2.0 * len(words & name_t) / (len(name_t) or 1) + 1.0 * len(words & desc_t) / (len(desc_t) ** 0.5 or 1)
        ranked.append((round(score, 3), name, a))
    ranked.sort(key=lambda t: (-t[0], t[1]))
    if not ranked or ranked[0][0] < 0.5:
        return {"action": "none", "args": {}, "confidence": 0.15, "reply": "I couldn't match that to an available action.",
                "alternatives": [r[1] for r in ranked[:3] if r[0] > 0]}
    top = ranked[0]
    margin = top[0] - (ranked[1][0] if len(ranked) > 1 else 0.0)
    confidence = max(0.3, min(0.97, 0.45 + 0.18 * top[0] + 0.2 * min(1.0, margin)))
    args = _extract_args(utterance, top[2].get("params") or {})
    return {"action": top[1], "args": args, "confidence": round(confidence, 2),
            "reply": "Running “%s”%s." % (top[1].replace("_", " "), (" with " + ", ".join("%s = %s" % kv for kv in args.items())) if args else ""),
            "alternatives": [r[1] for r in ranked[1:4] if r[0] >= 0.5]}


def plan(goal: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    clauses = [c.strip() for c in re.split(r"\b(?:and then|then|after that|and finally|afterwards)\b|;|\.(?=\s|$)|,\s+(?:and\s+)?(?=\w+\s)", goal or "") if c and c.strip()]
    steps, used = [], set()
    for clause in clauses or [goal]:
        hit = route(clause, actions)
        if hit["action"] != "none" and hit["action"] not in used:
            used.add(hit["action"])
            spec = next(a for a in actions if a.get("name") == hit["action"])
            steps.append({"title": clause[:1].upper() + clause[1:], "action": hit["action"], "args": hit["args"],
                          "risk": risk_of(hit["action"], str(spec.get("description", ""))), "why": "Matches “%s”." % T.clip(clause, 60)})
    if not steps:
        return {"summary": "No registered action covers this goal yet.", "steps": []}
    risky = sum(1 for s in steps if s["risk"] == "high")
    return {"summary": "%d step%s%s." % (len(steps), "" if len(steps) == 1 else "s", "; %d need%s approval" % (risky, "s" if risky == 1 else "") if risky else ""), "steps": steps}


def slash_commands(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out, taken = [], set()
    for a in actions:
        parts = re.split(r"[_\-\s]+", str(a.get("name", "")).lower())
        slug = parts[0] if parts[0] not in taken else "-".join(parts[:2])
        while slug in taken:
            slug += "2"
        taken.add(slug)
        params = " ".join("<%s>" % p for p in (a.get("params") or {}))
        out.append({"label": "/%s%s" % (slug, (" " + params) if params else ""), "detail": str(a.get("description", "")),
                    "action": a.get("name"), "value": "/" + slug})
    return out


def shortcuts(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Assign mnemonic, collision-free shortcuts (first free letter of each action)."""
    reserved = set("cvxazsfprtnwq")  # browser and OS conventions
    taken, out = set(), []
    for a in actions:
        name = str(a.get("name", ""))
        letters = [w[0] for w in re.split(r"[_\-\s]+", name.lower()) if w] + [c for c in name.lower() if c.isalpha()]
        key = next((c for c in letters if c not in taken and c not in reserved), None)
        combo = ("G then %s" % key.upper()) if key else None
        if key is None:
            key = next((c for c in letters if ("shift+" + c) not in taken), "k")
            combo, key = "Ctrl+Shift+%s" % key.upper(), "shift+" + key
        taken.add(key)
        out.append({"label": combo, "detail": name.replace("_", " "), "action": name, "value": combo})
    return out


def parse_rule(text: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    m = re.match(r"^\s*(?:when(?:ever)?|if|every time|once|after)\s+(.+?)(?:,\s*|\s+then\s+|\s*→\s*)(.+)$", text or "", re.IGNORECASE)
    if not m:
        return {"trigger": "", "conditions": [], "action": "none", "args": {}, "summary": "Write the rule as “when … then …”.", "confidence": 0.1}
    cond, then = m.group(1).strip(), m.group(2).strip().rstrip(".")
    conditions = []
    subject = ""
    for part in re.split(r"\s+and\s+", cond):
        late = re.search(r"([\w ]+?)\s+is\s+(overdue|late|inactive|idle|unpaid)\s+(?:by|for)\s+(?:more than\s+|at least\s+)?(\d+)\s+(minute|hour|day|week|month)s?", part, re.IGNORECASE)
        if late:
            subject = subject or re.sub(r"^(?:an?|the|any)\s+", "", late.group(1).strip(), flags=re.IGNORECASE)
            conditions.append({"field": "%ss_%s" % (late.group(4).lower(), late.group(2).lower()), "op": "gte", "value": late.group(3)})
            continue
        c = re.search(r"([\w ]+?)\s+(is over|is above|exceeds|is under|is below|is|equals|contains|changes to|becomes|>=|<=|>|<|=)\s+(.+)$", part, re.IGNORECASE)
        if c:
            op = {"is over": "gt", "is above": "gt", "exceeds": "gt", ">": "gt", ">=": "gte", "is under": "lt", "is below": "lt", "<": "lt", "<=": "lte",
                  "contains": "contains"}.get(c.group(2).lower(), "eq")
            conditions.append({"field": c.group(1).strip().replace(" ", "_").lower(), "op": op, "value": c.group(3).strip()})
    hit = route(then, actions)
    trigger = subject or re.sub(r"^(?:an?|the|any)\s+", "", re.split(r"\s+(?:is|exceeds|becomes|changes|contains|>|<|=)", cond)[0].strip(), flags=re.IGNORECASE)
    return {"trigger": trigger, "conditions": conditions, "action": hit["action"], "args": hit["args"],
            "summary": "When %s → %s." % (cond, hit["action"].replace("_", " ") if hit["action"] != "none" else then),
            "confidence": round(0.5 + 0.4 * hit["confidence"], 2) if hit["action"] != "none" else 0.35}


def undo_story(history: List[Any], request: str = "") -> Dict[str, Any]:
    """Narrate recent actions and locate the one a person wants to undo."""
    entries = [h if isinstance(h, dict) else {"label": str(h)} for h in history]
    lines = ["%d. %s" % (i + 1, e.get("label") or e.get("action") or "Step") for i, e in enumerate(entries)]
    target = len(entries) - 1 if entries else -1
    if request and entries:
        want = _tokens(request)
        scored = [(len(want & _tokens(str(e.get("label") or e.get("action") or ""))), i) for i, e in enumerate(entries)]
        best = max(scored, key=lambda t: (t[0], t[1]))
        if best[0] > 0:
            target = best[1]
        m = re.search(r"\b(\d+)\s+steps?\b", request)
        if m:
            target = max(0, len(entries) - int(m.group(1)))
    return {"narrative": " ".join(lines) or "Nothing has happened yet.", "target": target,
            "label": (entries[target].get("label") or entries[target].get("action") or "") if target >= 0 else "",
            "steps_reverted": len(entries) - target if target >= 0 else 0}
