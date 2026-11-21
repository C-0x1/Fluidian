"""Input Intelligence capabilities."""
from __future__ import annotations

import re
from typing import Any, Dict

from ..reflex import data as D
from ..reflex import parse as P
from ..reflex import text as T
from .registry import FIELDS, ITEMS, TEXT, VALUE, VERDICT, Ctx, cap, fields, items, value, verdict

_PHRASES = [("thank", " you for your time."), ("thanks for", " getting back to me."), ("best", " regards,"),
            ("looking forward", " to hearing from you."), ("please let me know", " if you have any questions."),
            ("let me know", " if you need anything else."), ("i hope", " this helps."), ("as discussed", ", here are the next steps."),
            ("following up", " on our conversation."), ("i wanted to", " follow up on this."), ("could you", " please take a look?"),
            ("sorry for", " the delay."), ("happy to", " help with this."), ("we are", " looking into it."),
            ("the customer", " reported an issue with"), ("steps to", " reproduce:"), ("expected", " behaviour:"),
            ("this pr", " adds"), ("fixes", " an issue where"), ("meeting", " notes:")]
_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "icloud.com", "proton.me", "hotmail.com", "example.com"]


def _ghost(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    text = i.get("text") or ""
    low = text.lower()
    for ex in i.get("examples") or []:
        if isinstance(ex, str) and len(text) >= 2 and ex.lower().startswith(low) and len(ex) > len(text):
            return {"completion": ex[len(text):], "confidence": 0.85}
    m = re.search(r"@([a-z0-9.\-]*)$", low)
    if m:
        hit = next((d for d in _DOMAINS if d.startswith(m.group(1)) and d != m.group(1)), None)
        return {"completion": hit[len(m.group(1)):] if hit else "", "confidence": 0.8 if hit else 0.0}
    tail = low.rstrip()
    for key, rest in _PHRASES:
        if tail.endswith(key):
            return {"completion": ("" if text.endswith(" ") else "") + rest.lstrip() if text.endswith(" ") else rest, "confidence": 0.55}
    return {"completion": "", "confidence": 0.0}


cap("input.ghost", "Ghost Completion",
    "Predicts the rest of what a person is typing and shows it as inline ghost text; Tab accepts.",
    why="Most typed text in business software is predictable; completion removes keystrokes without removing control.",
    do="Continue the text naturally in the same voice. Return only the characters to append (often a few words, at "
       "most one sentence). Return an empty completion when unsure.",
    inp={"text": "str", "label?": "str", "context?": "str", "examples?": ["str"]},
    out={"completion": "str", "confidence": "num"}, present="ghost", binds=["Input", "TextArea", "Search"], max_out=160,
    ex={"text": "Thank", "label": "Reply"}, reflex=_ghost)

cap("input.smart_paste", "Smart Paste",
    "Distributes pasted unstructured text — a signature, an email, a listing — across the right form fields.",
    why="People copy details from one place to type them into another; the form should do the reading.",
    do="Extract a value for each listed field from the pasted text. Only use values that appear in the text; omit "
       "fields you cannot find. Normalise dates to ISO 8601 and amounts to plain numbers.",
    inp={"text": "str", "fields": ["any"]}, out=FIELDS, present="fill", binds=["Form", "SmartForm"], untrusted=["text"],
    ex={"text": "Ada Lovelace\nHead of Research at Analytical Engines Ltd\nada@analytical.io | +44 20 7946 0958",
        "fields": ["name", "email", "phone", "company", "title"]},
    reflex=lambda i, c: fields(P.smart_paste(i["text"], i["fields"])))

cap("input.natural_date", "Natural Dates & Times",
    "Resolves phrases like “next Friday at 3pm” or “in two weeks” into exact values.",
    why="Date pickers are slow; language is how people already think about time.",
    do="Resolve the expression relative to `now`. Return ISO 8601 (date, or date and time), a readable display "
       "string and the kind. Use kind 'unknown' with an empty value if it is not a date.",
    inp={"text": "str", "dayFirst?": "bool"},
    out={"value": "str", "display": "str", "kind": "enum:date|datetime|unknown", "confidence": "num"},
    present="fill", binds=["Input"], max_out=200, ex={"text": "next Friday at 3pm"},
    reflex=lambda i, c: P.natural_date(i["text"], c.now, bool(i.get("dayFirst"))))

cap("input.natural_quantity", "Natural Quantities & Units",
    "Parses “$1.2m”, “2.5 hrs” or “5k” into a number, a unit and a canonical value.",
    why="Numeric fields reject the way people actually write numbers.",
    do="Parse the quantity. Return the canonical numeric value as a string, a display form, the unit and its "
       "dimension (currency, time, length, mass, data, ratio or count).",
    inp={"text": "str", "expect?": "str"},
    out={"value": "str", "display": "str", "unit": "str", "dimension": "str", "confidence": "num"},
    present="fill", binds=["Input", "Slider"], max_out=200, ex={"text": "$1.2m"},
    reflex=lambda i, c: P.quantity(i["text"]))

_LOCALE_DEFAULTS = {"US": ("United States", "USD"), "GB": ("United Kingdom", "GBP"), "DE": ("Germany", "EUR"), "FR": ("France", "EUR"),
                    "ES": ("Spain", "EUR"), "JP": ("Japan", "JPY"), "BR": ("Brazil", "BRL"), "CA": ("Canada", "CAD"),
                    "IN": ("India", "INR"), "AU": ("Australia", "AUD"), "PT": ("Portugal", "EUR"), "MX": ("Mexico", "MXN")}


def _infer(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    known = i.get("known") if isinstance(i.get("known"), dict) else {}
    out = []
    email = str(known.get("email") or "")
    site = str(known.get("website") or known.get("url") or "")
    name = str(known.get("name") or "")
    for target in i.get("targets") or []:
        key = target.lower()
        if key in known and known[key]:
            continue
        if "@" in email:
            local, domain = email.split("@", 1)
            public = domain.split(".")[0] in ("gmail", "yahoo", "outlook", "hotmail", "icloud", "proton")
            parts = [p for p in re.split(r"[._\-+]", local) if p.isalpha()]
            if key in ("name", "full_name") and 1 < len(parts) <= 3:
                out.append({"name": target, "value": " ".join(p.capitalize() for p in parts), "confidence": 0.6})
            elif key == "first_name" and parts:
                out.append({"name": target, "value": parts[0].capitalize(), "confidence": 0.6})
            elif key == "last_name" and len(parts) > 1:
                out.append({"name": target, "value": parts[-1].capitalize(), "confidence": 0.55})
            elif key in ("company", "organization") and not public:
                out.append({"name": target, "value": domain.split(".")[0].replace("-", " ").title(), "confidence": 0.55})
            elif key in ("website", "url") and not public:
                out.append({"name": target, "value": "https://" + domain, "confidence": 0.7})
        if site and key in ("company", "organization") and not any(o["name"] == target for o in out):
            host = re.sub(r"^https?://(www\.)?", "", site).split("/")[0]
            out.append({"name": target, "value": host.split(".")[0].replace("-", " ").title(), "confidence": 0.6})
        if name and key in ("first_name", "last_name") and not any(o["name"] == target for o in out):
            parts = name.split()
            out.append({"name": target, "value": parts[0] if key == "first_name" else parts[-1], "confidence": 0.9})
        region = c.locale.split("-")[-1].upper()
        if key in ("country", "currency") and region in _LOCALE_DEFAULTS and not any(o["name"] == target for o in out):
            out.append({"name": target, "value": _LOCALE_DEFAULTS[region][0 if key == "country" else 1], "confidence": 0.5})
    return fields(out, "Derived from the values already entered.")


cap("input.infer_fields", "Field Inference",
    "Fills fields that can be derived from what is already known — company from an email domain, names from a full name.",
    why="Every field a form can answer itself is a field nobody has to type.",
    do="From the known values, infer values for the target fields. Only infer what follows with reasonable "
       "certainty and give an honest confidence for each.",
    inp={"known": "any", "targets": ["str"]}, out=FIELDS, present="fill", binds=["Form"],
    ex={"known": {"email": "ada.lovelace@analytical.io"}, "targets": ["name", "company", "website"]}, reflex=_infer)

_JUNK = {"test", "asdf", "qwerty", "n/a", "na", "none", "xxx", "aaa", "123", "abc", "foo", "bar", "lorem", "tbd", "-", "."}


def _semantic(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    v, expect = (i.get("value") or "").strip(), (i.get("expectation") or "").lower()
    label = i.get("label") or "This field"
    if not v:
        return verdict(False, "%s is empty." % label, "warning", "Add a value to continue.")
    if v.lower() in _JUNK or re.fullmatch(r"(.)\1{2,}", v):
        return verdict(False, "“%s” looks like a placeholder." % v, "warning", "Enter the real %s." % label.lower())
    if re.search(r"\b(person|full name|name of)\b", expect) or expect.strip() == "name":
        if re.search(r"\d", v) or len(v) < 2:
            return verdict(False, "Names don't usually contain digits.", "warning", "Check for a typo.")
        if len(v.split()) < 2 and "full" in expect:
            return verdict(False, "This looks like a first name only.", "info", "Add a family name.")
    if re.search(r"\b(job title|role|position)\b", expect) and (re.search(r"@|\d{3,}", v) or len(v) < 3):
        return verdict(False, "That doesn't look like a job title.", "warning", "For example “Product Manager”.")
    if re.search(r"\b(company|organisation|organization|business)\b", expect) and "@" in v:
        return verdict(False, "That looks like an email address, not a company.", "warning", "Enter the company's name.")
    if re.search(r"\b(reason|description|explain|details|why|feedback)\b", expect) and len(v.split()) < 4:
        return verdict(False, "A little more detail will help.", "info", "Write at least one full sentence.")
    if re.search(r"\b(url|website|link)\b", expect) and not P.heal_format(v, "url")["ok"]:
        return verdict(False, "That doesn't look like a web address.", "warning", "For example https://example.com.")
    if re.search(r"\bemail\b", expect) and not P.heal_format(v, "email")["ok"]:
        return verdict(False, "That email address is incomplete.", "warning", "It needs a name, @ and a domain.")
    return verdict(True, "Looks good.")


cap("input.semantic_validate", "Semantic Validation",
    "Checks whether a value means what the field expects — a real job title, a plausible reason — not just its format.",
    why="Regex validation accepts “asdf” as a company name; meaning-level checks catch what patterns cannot.",
    do="Decide whether the value plausibly satisfies the expectation. Be lenient with unusual but real values. "
       "When it fails, explain kindly and suggest a fix in one sentence each.",
    inp={"value": "str", "expectation": "str", "label?": "str"}, out=VERDICT, present="validate",
    binds=["Input", "TextArea"], untrusted=["value"], max_out=220,
    ex={"value": "asdf", "expectation": "company name", "label": "Company"}, reflex=_semantic)


def _coach(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    err, field = (i.get("error") or "").lower(), (i.get("field") or "this field")
    name = field.replace("_", " ")
    rules = [(r"required|missing|blank|empty|null", "Add your %s to continue." % name, None),
             (r"email", "That email address isn't complete.", "name@company.com"),
             (r"(too short|min(imum)?\D*(\d+))", "Your %s needs a few more characters." % name, None),
             (r"(too long|max(imum)?\D*(\d+))", "Your %s is a little too long." % name, None),
             (r"pattern|regex|format|invalid", "The %s isn't in the expected format." % name, None),
             (r"range|between|greater|less|exceed", "That %s is outside the allowed range." % name, None),
             (r"exists|taken|duplicate|unique|conflict", "That %s is already in use." % name, None),
             (r"password", "Choose a stronger password.", "At least 12 characters with a number"),
             (r"date", "That date isn't valid.", "2027-01-15"), (r"number|numeric|integer", "Use digits only for %s." % name, "42"),
             (r"unauthori[sz]ed|forbidden|permission|denied", "You don't have access to do that.", None),
             (r"timeout|network|unavailable|503|502", "We couldn't reach the server. Your entry is safe; try again.", None)]
    for pattern, message, example in rules:
        m = re.search(pattern, err)
        if m:
            digits = re.search(r"\d+", err)
            suggestion = ("Use at least %s characters." % digits.group(0)) if (digits and "short" in err or digits and "min" in err) else (
                "Keep it under %s characters." % digits.group(0) if digits and ("long" in err or "max" in err) else
                ("Try a different one." if "use" in message else None))
            return {"message": message, "suggestion": suggestion, "example": example}
    return {"message": "Something about %s needs another look." % name, "suggestion": "Check the value and try again.", "example": None}


cap("input.error_coach", "Error Coach",
    "Rewrites technical validation errors into specific, kind guidance with an example of a correct value.",
    why="“Invalid input” tells people they failed; a coach tells them how to succeed.",
    do="Rewrite the error for the person filling in the field. Say what to do, not what went wrong; no blame, no "
       "jargon, no codes. Offer one concrete suggestion and, where useful, an example value.",
    inp={"error": "str", "field?": "str", "value?": "str"},
    out={"message": "str", "suggestion?": "str", "example?": "str"}, present="validate", binds=["Input", "TextArea", "Form"],
    max_out=220, ex={"error": "ERR_VALIDATION: field 'work_email' failed pattern ^\\S+@\\S+$", "field": "work_email"}, reflex=_coach)

cap("input.format_heal", "Format Healing",
    "Repairs formatting mistakes in emails, phone numbers, URLs, cards, IBANs and postal codes instead of rejecting them.",
    why="A missing “https://” or a space in a card number is not a user error worth an error message.",
    do="Return the value in canonical form for its kind, whether it is plausible, and a short note describing any "
       "correction. Never invent missing digits or characters.",
    inp={"value": "str", "kind": "str"}, out={"value": "str", "ok": "bool", "changed": "bool", "note": "str"},
    present="fill", binds=["Input"], max_out=200, ex={"value": "ada@gmial.com", "kind": "email"},
    reflex=lambda i, c: P.heal_format(i["value"], i["kind"]))

cap("input.tone_dial", "Tone Dial",
    "Rewrites a draft in a chosen tone — friendly, formal, concise, confident, empathetic — with a before/after preview.",
    why="Writing the same thing in the right register is a skill most people outsource to a colleague.",
    do="Rewrite the text in the requested tone. Preserve meaning, facts, names and numbers; change only wording and "
       "rhythm. Return the rewritten text only.",
    inp={"text": "str", "tone": "str"}, out=TEXT, present="rewrite", binds=["TextArea", "Input"], untrusted=["text"],
    ex={"text": "We can not process your refund at this point in time.", "tone": "friendly"},
    reflex=lambda i, c: {"text": T.retone(i["text"], i["tone"]), "rationale": "Adjusted wording for a %s register; facts unchanged." % i["tone"]})

_SHORT = {"w/": "with", "w/o": "without", "tmrw": "tomorrow", "tmw": "tomorrow", "mtg": "meeting", "pls": "please", "plz": "please",
          "thx": "thanks", "fyi": "for your information", "asap": "as soon as possible", "eod": "by end of day", "b/c": "because",
          "bc": "because", "lmk": "let me know", "btw": "by the way", "approx": "approximately", "appt": "appointment",
          "mgmt": "management", "dept": "department", "qty": "quantity", "msg": "message", "info": "information",
          "hrs": "hours", "abt": "about", "re": "regarding", "cust": "customer", "acct": "account", "amt": "amount",
          "mins": "minutes", "yr": "year", "wk": "week", "nxt": "next", "u": "you", "r": "are", "ur": "your", "&": "and", "+": "and",
          "eta": "estimated arrival", "ooo": "out of office", "wfh": "working from home", "cc": "copy", "nb": "note"}


def _expand(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    out = []
    for tok in (i.get("text") or "").split():
        core = tok.rstrip(".,;:!?")
        tail = tok[len(core):]
        out.append(_SHORT.get(core.lower(), core) + tail)
    text = " ".join(out).strip()
    if text and text[-1] not in ".!?":
        text += "."
    return {"text": text[:1].upper() + text[1:], "rationale": "Expanded abbreviations into full words."}


cap("input.expand", "Shorthand Expansion",
    "Turns quick notes like “mtg w/ sam tmrw re pricing” into a complete, polished sentence.",
    why="People capture thoughts in fragments; recipients deserve sentences.",
    do="Expand the shorthand into clear, complete prose. Keep every fact; add no new information.",
    inp={"text": "str", "context?": "str"}, out=TEXT, present="rewrite", binds=["TextArea", "Input"], untrusted=["text"],
    ex={"text": "mtg w/ sam tmrw re pricing, pls send deck asap"}, reflex=_expand)

cap("input.mask_synth", "Mask Synthesis",
    "Infers an input mask, a validating pattern and a placeholder from a few example values.",
    why="Hand-written masks and regular expressions are error-prone; examples are easy to supply.",
    do="From the examples infer the shared format. Return a mask (9 = digit, A = letter, other characters literal), "
       "an anchored regular expression and a placeholder string.",
    inp={"examples": ["str"]}, out={"mask": "str", "regex": "str", "placeholder": "str", "explanation": "str"},
    present="service", max_out=260, ex={"examples": ["AB-1234", "XY-9876"]},
    reflex=lambda i, c: dict(P.synth_mask(i["examples"]), explanation="Derived from the character classes shared by every example."))


def _default(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    hist = [h for h in (i.get("history") or []) if isinstance(h, str) and h]
    name = (i.get("field") or "").lower()
    if hist:
        best = max(sorted(set(hist)), key=hist.count)
        return value(best, confidence=min(0.95, 0.5 + hist.count(best) / (2.0 * len(hist))), explanation="Used %d of the last %d times." % (hist.count(best), len(hist)))
    region = c.locale.split("-")[-1].upper()
    if "country" in name and region in _LOCALE_DEFAULTS:
        return value(_LOCALE_DEFAULTS[region][0], confidence=0.6, explanation="Matches your locale.")
    if "currency" in name and region in _LOCALE_DEFAULTS:
        return value(_LOCALE_DEFAULTS[region][1], confidence=0.6, explanation="Matches your locale.")
    if "language" in name or "locale" in name:
        return value(c.locale, confidence=0.6, explanation="Matches your browser language.")
    if re.search(r"(date|day|when|start)", name):
        return value(c.now.strftime("%Y-%m-%d"), "Today", 0.5, "Most entries are dated today.")
    if re.search(r"(qty|quantity|seats|count|guests)", name):
        return value("1", confidence=0.5, explanation="The most common quantity.")
    return value("", "", 0.0, "No basis for a default yet.")


cap("input.smart_default", "Smart Defaults",
    "Proposes the most likely value for a field from history, locale and context.",
    why="The best form field is one that is already right.",
    do="Propose the single most likely value for the field given history and context, with a short explanation. "
       "Return an empty value with confidence 0 if there is no sound basis.",
    inp={"field": "str", "context?": "any", "history?": ["str"]}, out=VALUE, present="fill", binds=["Input", "Select"],
    max_out=200, ex={"field": "currency", "history": ["EUR", "USD", "EUR"]}, reflex=_default)


def _clarify(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    v, field = (i.get("value") or "").strip(), (i.get("field") or "").lower()
    options = [o for o in (i.get("options") or []) if isinstance(o, str)]
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})", v)
    if m and int(m.group(1)) <= 12 and int(m.group(2)) <= 12 and m.group(1) != m.group(2):
        months = P.MONTHS
        a = "%d %s" % (int(m.group(2)), months[int(m.group(1)) - 1].capitalize())
        b = "%d %s" % (int(m.group(1)), months[int(m.group(2)) - 1].capitalize())
        return {"needed": True, "question": "Which date do you mean?", "choices": [a, b]}
    if re.fullmatch(r"\d+(\.\d+)?", v) and re.search(r"(duration|length|weight|distance|size|timeout|budget|price)", field):
        units = {"duration": ["minutes", "hours", "days"], "timeout": ["seconds", "minutes"], "weight": ["kg", "lb"],
                 "distance": ["km", "miles"], "length": ["cm", "inches"], "size": ["MB", "GB"], "budget": ["USD", "EUR"], "price": ["USD", "EUR"]}
        key = next(k for k in units if k in field)
        return {"needed": True, "question": "%s what?" % v, "choices": ["%s %s" % (v, u) for u in units[key]]}
    hits = [o for o in options if v and o.lower().startswith(v.lower())]
    if len(hits) > 1:
        return {"needed": True, "question": "Did you mean one of these?", "choices": hits[:4]}
    return {"needed": False, "question": "", "choices": []}


cap("input.clarify", "Clarifying Micro-Question",
    "Asks one short question when an entry is ambiguous — “3/4” in March or April? “30” minutes or hours?",
    why="Guessing silently causes data errors; rejecting causes friction; one tap resolves both.",
    do="Decide whether the value is genuinely ambiguous for this field. If so ask one short question and offer two "
       "to four concrete choices. If it is clear, set needed to false.",
    inp={"value": "str", "field": "str", "options?": ["str"]},
    out={"needed": "bool", "question": "str", "choices": ["str"]}, present="suggest", binds=["Input", "Select"],
    max_out=220, ex={"value": "03/04/2027", "field": "due_date"}, reflex=_clarify)

_LANG = {"es": {"el", "la", "los", "las", "de", "que", "y", "en", "un", "una", "por", "con", "para", "es", "hola", "gracias", "mañana"},
         "fr": {"le", "la", "les", "des", "et", "est", "un", "une", "pour", "avec", "dans", "bonjour", "merci", "demain", "je", "nous"},
         "de": {"der", "die", "das", "und", "ist", "ein", "eine", "mit", "für", "nicht", "ich", "wir", "danke", "morgen", "bitte"},
         "pt": {"o", "os", "as", "de", "que", "e", "em", "um", "uma", "para", "com", "não", "obrigado", "amanhã", "olá"},
         "it": {"il", "lo", "gli", "di", "che", "e", "un", "una", "per", "con", "non", "grazie", "domani", "ciao"}}


def detect_language(text: str) -> tuple:
    ws = set(T.words(text))
    if re.search(r"[぀-ヿ一-鿿]", text or ""):
        return "ja", 0.9
    scores = {lang: len(ws & vocab) for lang, vocab in _LANG.items()}
    english = len(ws & T.STOP)
    best = max(scores, key=lambda k: scores[k]) if scores else "en"
    if scores.get(best, 0) > english and scores[best] >= 1:
        return best, min(0.95, 0.5 + 0.12 * scores[best])
    return "en", 0.6 if ws else 0.2


def _polyglot(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    lang, conf = detect_language(i.get("text") or "")
    return {"text": i.get("text") or "", "detected": lang, "confidence": conf}


cap("input.polyglot", "Polyglot Input Bridge",
    "Lets people type in their own language and stores the value in the application's working language.",
    why="Global teams should not be forced to think in the application's language to use it.",
    do="Detect the language of the text (ISO 639-1). If it differs from the target language, translate it "
       "faithfully into the target; otherwise return it unchanged.",
    inp={"text": "str", "target?": "str"}, out={"text": "str", "detected": "str", "confidence": "num"},
    present="fill", binds=["Input", "TextArea"], untrusted=["text"],
    ex={"text": "Necesito una factura para mañana", "target": "en"}, reflex=_polyglot)


def _shield(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    allow = set(i.get("allow") or [])
    found = [f for f in P.find_pii(i.get("text") or "") if f["kind"] not in allow]
    redacted, _ = P.redact(i.get("text") or "", [k for k in ("secret", "email", "iban", "card", "ssn", "phone", "ip") if k not in allow])
    kinds = sorted({f["kind"] for f in found})
    return {"safe": not found, "redacted": redacted,
            "findings": [{"kind": f["kind"], "excerpt": f["value"][:3] + "…" + f["value"][-2:] if len(f["value"]) > 6 else "…"} for f in found],
            "message": "Nothing sensitive detected." if not found else "This contains %s. Remove it or confirm it is intended." % ", ".join(kinds)}


cap("input.sensitive_shield", "Sensitive Data Shield",
    "Warns before submission when free text contains card numbers, credentials, national identifiers or other personal data.",
    why="Secrets pasted into a notes field end up in logs, exports and model prompts.",
    inp={"text": "str", "allow?": ["str"]},
    out={"safe": "bool", "findings": [{"kind": "str", "excerpt": "str"}], "redacted": "str", "message": "str"},
    present="validate", binds=["TextArea", "Input"], ex={"text": "Card 4242 4242 4242 4242, key sk-abc123def456ghi789jkl"},
    direct=_shield)

cap("input.address", "Address Structuring",
    "Splits a pasted postal address into street, city, region, postal code and country.",
    why="Five address fields are five chances to give up; one paste should fill them all.",
    do="Split the address into the fields: address (street line), city, state, postal, country. Use only what is "
       "present; omit fields you cannot determine.",
    inp={"text": "str"}, out=FIELDS, present="fill", binds=["Form", "TextArea"], untrusted=["text"],
    ex={"text": "12 Babbage Street, London, EC1A 1BB, United Kingdom"},
    reflex=lambda i, c: fields([{"name": k, "value": v, "confidence": 0.75} for k, v in P.parse_address(i["text"]).items()]))


def _rank(i: Dict[str, Any], c: Ctx) -> Dict[str, Any]:
    options = [o for o in (i.get("options") or []) if isinstance(o, str)]
    recent = [r for r in (i.get("recent") or []) if isinstance(r, str)]
    sim = {h["text"]: h["score"] for h in D.search(i.get("context") or "", options, len(options))} if i.get("context") else {}
    scored = [(recent.count(o) * 1.0 + sim.get(o, 0.0), -idx, o) for idx, o in enumerate(options)]
    scored.sort(reverse=True)
    return items([{"label": o, "value": o, "score": round(s, 2),
                   "detail": ("used %d× recently" % recent.count(o)) if recent.count(o) else ("matches context" if sim.get(o) else None)}
                  for s, _, o in scored])


cap("input.option_rank", "Option Ranking",
    "Reorders the options of a select or radio group so the likeliest choices come first.",
    why="Alphabetical lists make everyone scroll; relevance puts the answer under the cursor.",
    do="Rank the options from most to least likely for this context and recent choices. Return every option exactly "
       "once, using the original strings as both label and value.",
    inp={"options": ["str"], "context?": "str", "recent?": ["str"]}, out=ITEMS, present="suggest",
    binds=["Select", "RadioGroup", "Segmented"],
    ex={"options": ["Billing", "Technical", "Feedback", "General"], "context": "my invoice shows the wrong amount", "recent": ["Technical"]},
    reflex=_rank)
