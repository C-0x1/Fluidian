"""Reflex parsing: dates, quantities, personal data, pasted text, formats."""
from __future__ import annotations

import calendar
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]
_NUMWORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "couple": 2, "few": 3}


def _num(tok: str) -> Optional[int]:
    tok = tok.lower()
    if tok.isdigit():
        return int(tok)
    return _NUMWORDS.get(tok)


def _add_months(d: datetime, months: int) -> datetime:
    index = d.month - 1 + months
    year, month = d.year + index // 12, index % 12 + 1
    return d.replace(year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1]))


def natural_date(text: str, now: Optional[datetime] = None, day_first: bool = False) -> Dict[str, Any]:
    """Resolve expressions like "next Friday at 3pm" or "in 2 weeks" to ISO values."""
    now = now or datetime.now()
    raw = (text or "").strip()
    s = raw.lower()
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    date: Optional[datetime] = None
    clock: Optional[Tuple[int, int]] = None
    confidence = 0.0

    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)", s)
    if m:
        hour, minute = int(m.group(1)) % 12, int(m.group(2) or 0)
        if m.group(3).startswith("p"):
            hour += 12
        clock = (hour, minute)
    else:
        m = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", s)
        if m:
            clock = (int(m.group(1)), int(m.group(2)))
    for word, value in (("noon", (12, 0)), ("midday", (12, 0)), ("midnight", (0, 0)), ("morning", (9, 0)),
                        ("afternoon", (15, 0)), ("evening", (18, 0)), ("tonight", (20, 0)), ("eod", (17, 0)),
                        ("end of day", (17, 0)), ("lunch", (12, 30))):
        if clock is None and re.search(r"\b%s\b" % word, s):
            clock = value

    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        try:
            date, confidence = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))), 0.98
        except ValueError:
            date = None
    if date is None:
        m = re.search(r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b", s)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            month, day = (b, a) if (day_first or a > 12) else (a, b)
            year = int(m.group(3)) if m.group(3) else now.year
            year += 2000 if year < 100 else 0
            try:
                date, confidence = datetime(year, month, day), 0.85
                if not m.group(3) and date < base:
                    date = date.replace(year=year + 1)
            except ValueError:
                date = None
    if date is None:
        names = "|".join(MONTHS) + "|" + "|".join(mm[:3] for mm in MONTHS)
        m = re.search(r"\b(%s)\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b" % names, s) or None
        day_s = month_s = year_s = None
        if m:
            month_s, day_s, year_s = m.group(1), m.group(2), m.group(3)
        else:
            m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(%s)\.?(?:,?\s+(\d{4}))?\b" % names, s)
            if m:
                day_s, month_s, year_s = m.group(1), m.group(2), m.group(3)
        if m and month_s and day_s:
            month = next(i for i, mm in enumerate(MONTHS) if mm.startswith(month_s[:3])) + 1
            year = int(year_s) if year_s else now.year
            try:
                date, confidence = datetime(year, month, int(day_s)), 0.92
                if not year_s and date < base:
                    date = date.replace(year=year + 1)
            except ValueError:
                date = None
    if date is None:
        m = re.search(r"\bin\s+(\w+)\s+(minute|min|hour|hr|day|week|month|year)s?\b", s)
        ago = re.search(r"\b(\w+)\s+(minute|min|hour|hr|day|week|month|year)s?\s+ago\b", s)
        hit = m or ago
        if hit and _num(hit.group(1)) is not None:
            n = _num(hit.group(1)) * (-1 if ago and not m else 1)  # type: ignore[operator]
            unit = hit.group(2)
            if unit in ("minute", "min", "hour", "hr"):
                moment = now + (timedelta(minutes=n) if unit.startswith("min") else timedelta(hours=n))
                date, clock, confidence = moment.replace(second=0, microsecond=0), (moment.hour, moment.minute), 0.9
                date = date.replace(hour=0, minute=0)
            elif unit == "day":
                date, confidence = base + timedelta(days=n), 0.93
            elif unit == "week":
                date, confidence = base + timedelta(weeks=n), 0.93
            elif unit == "month":
                date, confidence = _add_months(base, n), 0.9
            else:
                date, confidence = _add_months(base, 12 * n), 0.9
    if date is None:
        for word, delta in (("day after tomorrow", 2), ("tomorrow", 1), ("tmrw", 1), ("yesterday", -1), ("today", 0),
                            ("tonight", 0), ("now", 0)):
            if re.search(r"\b%s\b" % word, s):
                date, confidence = base + timedelta(days=delta), 0.95
                if word == "now":
                    clock = (now.hour, now.minute)
                break
    if date is None:
        m = re.search(r"\b(next|this|last|on)?\s*(%s)\b" % "|".join(WEEKDAYS + [w[:3] for w in WEEKDAYS]), s)
        if m:
            target = next(i for i, w in enumerate(WEEKDAYS) if w.startswith(m.group(2)[:3]))
            delta = (target - base.weekday()) % 7
            qualifier = m.group(1) or ""
            if qualifier == "last":
                delta = delta - 7 if delta else -7
            elif qualifier == "next":
                # "next Friday" means the Friday of the following calendar week
                delta = (7 - base.weekday()) + target
            elif delta == 0 and qualifier != "this":
                delta = 7
            date, confidence = base + timedelta(days=delta), 0.86
    if date is None:
        if re.search(r"\bnext week\b", s):
            date, confidence = base + timedelta(days=7 - base.weekday()), 0.8
        elif re.search(r"\bnext month\b", s):
            date, confidence = _add_months(base.replace(day=1), 1), 0.8
        elif re.search(r"\b(end of (the )?month|eom)\b", s):
            date, confidence = base.replace(day=calendar.monthrange(base.year, base.month)[1]), 0.85
        elif re.search(r"\b(end of (the )?week|eow)\b", s):
            date, confidence = base + timedelta(days=(4 - base.weekday()) % 7), 0.8
        elif re.search(r"\bnext year\b", s):
            date, confidence = base.replace(year=base.year + 1, month=1, day=1), 0.75

    if date is None and clock is None:
        return {"value": "", "display": raw, "kind": "unknown", "confidence": 0.0}
    if date is None:
        date, confidence = base, 0.7
        if clock and (clock[0], clock[1]) <= (now.hour, now.minute):
            date = base + timedelta(days=1)
    if clock is not None:
        moment = date.replace(hour=clock[0], minute=clock[1])
        return {"value": moment.strftime("%Y-%m-%dT%H:%M"), "display": moment.strftime("%a %d %b %Y, %H:%M"),
                "kind": "datetime", "confidence": round(confidence, 2)}
    return {"value": date.strftime("%Y-%m-%d"), "display": date.strftime("%a %d %b %Y"), "kind": "date",
            "confidence": round(confidence, 2)}


_MULT = {"k": 1e3, "thousand": 1e3, "m": 1e6, "mm": 1e6, "mil": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9}
_CURRENCY = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "usd": "USD", "eur": "EUR", "gbp": "GBP", "jpy": "JPY",
             "dollars": "USD", "euros": "EUR", "pounds": "GBP", "bucks": "USD"}
# unit -> (dimension, canonical unit, factor to canonical)
UNITS: Dict[str, Tuple[str, str, float]] = {}
for _names, _dim, _canon, _factor in [
    ("ms millisecond milliseconds", "time", "s", 0.001), ("s sec secs second seconds", "time", "s", 1),
    ("min mins minute minutes", "time", "s", 60), ("h hr hrs hour hours", "time", "s", 3600),
    ("d day days", "time", "s", 86400), ("w wk wks week weeks", "time", "s", 604800),
    ("mm millimeter millimeters", "length", "m", 0.001), ("cm centimeter centimeters", "length", "m", 0.01),
    ("meter meters metre metres", "length", "m", 1), ("km kilometer kilometers", "length", "m", 1000),
    ("in inch inches", "length", "m", 0.0254), ("ft foot feet", "length", "m", 0.3048), ("mi mile miles", "length", "m", 1609.344),
    ("g gram grams", "mass", "kg", 0.001), ("kg kilogram kilograms kilo kilos", "mass", "kg", 1),
    ("tonne tonnes ton tons", "mass", "kg", 1000), ("lb lbs pound pounds", "mass", "kg", 0.45359237), ("oz ounce ounces", "mass", "kg", 0.028349523),
    ("kb", "data", "MB", 0.001), ("mb", "data", "MB", 1), ("gb", "data", "MB", 1000), ("tb", "data", "MB", 1e6),
    ("% percent pct", "ratio", "%", 1),
]:
    for _n in _names.split():
        UNITS[_n] = (_dim, _canon, _factor)


def _fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return "{:,}".format(int(round(value)))
    return "{:,.2f}".format(value).rstrip("0").rstrip(".")


def quantity(text: str) -> Dict[str, Any]:
    """Parse "$1.2m", "2.5 hrs", "5k", "12 kg" into a number, unit and canonical value."""
    raw = (text or "").strip()
    s = raw.lower().replace(",", "")
    m = re.search(r"([$€£¥])?\s*([-+]?\d+(?:\.\d+)?|\.\d+)\s*(k|mm|mil|m|bn|b|thousand|million|billion)?\b\s*([a-z%$€£¥]+)?", s)
    if not m:
        word = next((w for w in s.split() if w in _NUMWORDS), None)
        if word is None:
            return {"value": "", "display": raw, "unit": "", "dimension": "", "confidence": 0.0}
        return {"value": str(_NUMWORDS[word]), "display": str(_NUMWORDS[word]), "unit": "", "dimension": "count", "confidence": 0.6}
    number = float(m.group(2))
    mult, unit = m.group(3), (m.group(4) or "")
    currency = _CURRENCY.get(m.group(1) or "") or _CURRENCY.get(unit, "")
    if mult == "m" and not currency and unit == "" and re.search(r"\d\s*m\b", s) and not re.search(r"[$€£¥]", s):
        # a bare "5m" is ambiguous: treat as minutes only when the text mentions time
        if re.search(r"\b(wait|timeout|duration|meeting|call|timer|every|after|for)\b", s):
            mult, unit = None, "min"
    if mult:
        number *= _MULT[mult]
    if currency:
        return {"value": _fmt_number(number).replace(",", ""), "display": "%s %s" % (currency, _fmt_number(number)),
                "unit": currency, "dimension": "currency", "confidence": 0.92}
    if unit in UNITS:
        dim, canon, factor = UNITS[unit]
        canonical = number * factor
        return {"value": _fmt_number(canonical).replace(",", ""), "display": "%s %s" % (_fmt_number(number), unit),
                "unit": canon, "dimension": dim, "confidence": 0.9}
    return {"value": _fmt_number(number).replace(",", ""), "display": _fmt_number(number), "unit": "",
            "dimension": "count", "confidence": 0.8 if not unit else 0.55}


def convert(value: float, src: str, dst: str) -> Optional[float]:
    a, b = UNITS.get(src.lower()), UNITS.get(dst.lower())
    if not a or not b or a[0] != b[0]:
        return None
    return value * a[2] / b[2]


def luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total, alt = total + d, not alt
    return bool(digits) and total % 10 == 0


_PII: List[Tuple[str, "re.Pattern[str]"]] = [
    ("secret", re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}|eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,})")),
    ("secret", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*([^\s,;]{6,})")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}(?:[ ]?[A-Z0-9]{1,3})?\b")),
    ("card", re.compile(r"\b(?:\d[ \-]?){13,19}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone", re.compile(r"(?<![\w@])\+?\(?\d{1,4}\)?(?:[ .\-]\(?\d{2,4}\)?){1,5}(?!\w)")),
    ("ip", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")),
]


def find_pii(text: str, kinds: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    taken: List[Tuple[int, int]] = []
    for kind, pattern in _PII:
        if kinds and kind not in kinds:
            continue
        for m in pattern.finditer(text or ""):
            start, end = (m.start(1), m.end(1)) if (kind == "secret" and m.lastindex) else (m.start(), m.end())
            value = text[start:end]
            if kind == "card" and not luhn(re.sub(r"\D", "", value)):
                continue
            if kind == "phone":
                digits = re.sub(r"\D", "", value)
                if not 7 <= len(digits) <= 15 or re.match(r"^\d{4}-\d{2}-\d{2}", value) \
                        or re.fullmatch(r"\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}", value):
                    continue
            if any(start < e and end > s for s, e in taken):
                continue
            taken.append((start, end))
            found.append({"kind": kind, "value": value, "start": start, "end": end})
    return sorted(found, key=lambda f: f["start"])


def redact(text: str, kinds: Optional[List[str]] = None, counters: Optional[Dict[str, int]] = None,
           mapping: Optional[Dict[str, str]] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """Replace personal data with reversible placeholders such as ``⟦EMAIL_1⟧``."""
    counters = counters if counters is not None else {}
    mapping = mapping if mapping is not None else {}
    reverse = {v: k for k, v in mapping.items()}
    findings = find_pii(text, kinds)
    out, last = [], 0
    for f in findings:
        placeholder = reverse.get(f["value"])
        if placeholder is None:
            counters[f["kind"]] = counters.get(f["kind"], 0) + 1
            placeholder = "⟦%s_%d⟧" % (f["kind"].upper(), counters[f["kind"]])
            mapping[placeholder] = f["value"]
            reverse[f["value"]] = placeholder
        f["placeholder"] = placeholder
        out.append(text[last:f["start"]])
        out.append(placeholder)
        last = f["end"]
    out.append((text or "")[last:])
    return "".join(out), findings


def restore(value: Any, mapping: Dict[str, str]) -> Any:
    """Re-insert redacted values into any JSON-like structure."""
    if not mapping:
        return value
    if isinstance(value, str):
        for placeholder, original in mapping.items():
            if placeholder in value:
                value = value.replace(placeholder, original)
        return value
    if isinstance(value, list):
        return [restore(v, mapping) for v in value]
    if isinstance(value, dict):
        return {k: restore(v, mapping) for k, v in value.items()}
    return value


_SYNONYMS = {
    "email": ["email", "e-mail", "mail"], "phone": ["phone", "tel", "telephone", "mobile", "cell"],
    "name": ["name", "full name", "fullname", "contact", "contact name"], "first_name": ["first name", "firstname", "given name"],
    "last_name": ["last name", "lastname", "surname", "family name"],
    "company": ["company", "organization", "organisation", "org", "employer", "business", "account"],
    "title": ["title", "role", "position", "job", "job title"], "website": ["website", "url", "site", "web", "homepage"],
    "amount": ["amount", "total", "price", "cost", "value", "budget"], "date": ["date", "due", "deadline", "when", "due date"],
    "address": ["address", "street", "address line"], "city": ["city", "town"], "state": ["state", "region", "province"],
    "postal": ["zip", "postal", "postcode", "postal code", "zip code"], "country": ["country"],
    "notes": ["notes", "note", "message", "comments", "description", "details"], "subject": ["subject", "topic", "re"],
}
_COUNTRIES = ["united states", "usa", "canada", "united kingdom", "uk", "germany", "france", "spain", "italy", "netherlands",
              "australia", "japan", "india", "brazil", "mexico", "ireland", "sweden", "switzerland", "portugal", "singapore"]


def _canonical(field: str) -> str:
    key = re.sub(r"[_\-]+", " ", field).strip().lower()
    for canon, names in _SYNONYMS.items():
        if key == canon.replace("_", " ") or key in names:
            return canon
    for canon, names in _SYNONYMS.items():
        if any(re.search(r"\b%s\b" % re.escape(n), key) for n in names):
            return canon
    return key


def parse_address(text: str) -> Dict[str, str]:
    raw = re.sub(r"\s*\n\s*", ", ", (text or "").strip())
    out: Dict[str, str] = {}
    m = re.search(r"\b(\d{1,6}\s+[A-Za-z0-9.' ]+?\s(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|court|ct|place|pl|square|sq|terrace|highway|hwy)\b\.?(?:\s*(?:#|apt|suite|ste|unit)\.?\s*\w+)?)",
                  raw, re.IGNORECASE)
    if m:
        out["address"] = m.group(1).strip().rstrip(",")
    m = re.search(r"\b([A-Z]{2})\s+(\d{5}(?:-\d{4})?)\b", raw)
    if m:
        out["state"], out["postal"] = m.group(1), m.group(2)
        before = raw[:m.start()].rstrip(", ")
        city = before.split(",")[-1].strip()
        if city and city != out.get("address"):
            out["city"] = city
    else:
        m = re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", raw) or re.search(r"\b(\d{4,5})\s+([A-ZÀ-Ý][\wÀ-ÿ\- ]+)", raw)
        if m and m.lastindex == 1:
            out["postal"] = m.group(1)
        elif m:
            out["postal"], out["city"] = m.group(1), m.group(2).split(",")[0].strip()
    low = raw.lower()
    for country in _COUNTRIES:
        if re.search(r"\b%s\b" % re.escape(country), low):
            out["country"] = country.upper() if len(country) <= 3 else country.title()
            break
    return out


def smart_paste(text: str, fields: List[Any]) -> List[Dict[str, Any]]:
    """Distribute unstructured text (a signature, an email, a listing) across form fields."""
    raw = text or ""
    cands: Dict[str, Tuple[str, float]] = {}
    for line in raw.splitlines():
        m = re.match(r"\s*([A-Za-z][A-Za-z \-/]{1,24})\s*[:=\-–]\s*(.+?)\s*$", line)
        if m:
            cands.setdefault(_canonical(m.group(1)), (m.group(2).strip(), 0.95))
    email = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", raw)
    if email:
        cands.setdefault("email", (email.group(0), 0.97))
    phone = next((f for f in find_pii(raw, ["phone"])), None)
    if phone:
        cands.setdefault("phone", (phone["value"], 0.9))
    url = re.search(r"\b((?:https?://|www\.)[^\s,;]+)", raw)
    if url:
        cands.setdefault("website", (url.group(1).rstrip(".)"), 0.9))
    money = re.search(r"[$€£¥]\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|bn)?|\b\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP)\b", raw)
    if money:
        cands.setdefault("amount", (quantity(money.group(0))["value"], 0.85))
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    name_line = next((ln for ln in lines if re.fullmatch(r"(?:[A-ZÀ-Ý][a-zà-ÿ'’\-]+\.?\s){1,3}[A-ZÀ-Ý][a-zà-ÿ'’\-]+", ln)), None)
    if name_line:
        cands.setdefault("name", (name_line, 0.8))
    elif email and "name" not in cands:
        local = re.split(r"[._\-+]", email.group(0).split("@")[0])
        if 1 < len(local) <= 3 and all(p.isalpha() for p in local):
            cands["name"] = (" ".join(p.capitalize() for p in local), 0.6)
    if "name" in cands:
        parts = cands["name"][0].split()
        cands.setdefault("first_name", (parts[0], cands["name"][1] - 0.05))
        if len(parts) > 1:
            cands.setdefault("last_name", (parts[-1], cands["name"][1] - 0.05))
    title = next((ln for ln in lines if re.search(r"\b(manager|director|engineer|designer|founder|ceo|cto|cfo|vp|head of|lead|officer|analyst|consultant|president|developer)\b", ln, re.IGNORECASE) and "@" not in ln and len(ln) < 60), None)
    if title:
        title_text = re.split(r"\s+(?:at|@)\s+|,\s*", title)[0].strip()
        cands.setdefault("title", (title_text, 0.75))
        m = re.search(r"\s(?:at|@)\s+(.+)$", title)
        if m:
            cands.setdefault("company", (m.group(1).strip().rstrip("."), 0.75))
    org = re.search(r"\b([A-Z][\w&'\- ]{1,40}?\s(?:Inc|LLC|Ltd|GmbH|Corp|Co|S\.A\.|AG|PLC|BV)\.?)(?=\W|$)", raw)
    if org:
        cands.setdefault("company", (org.group(1).strip(), 0.8))
    elif email and "company" not in cands:
        domain = email.group(0).split("@")[1].split(".")[0]
        if domain not in ("gmail", "yahoo", "outlook", "hotmail", "icloud", "proton", "protonmail", "example"):
            cands["company"] = (domain.capitalize(), 0.5)
    for key, value in parse_address(raw).items():
        cands.setdefault(key, (value, 0.7))
    when = natural_date(raw)
    if when["kind"] != "unknown" and re.search(r"\d", raw):
        cands.setdefault("date", (when["value"], min(0.8, when["confidence"])))

    if "amount" in cands:
        hit = re.search(r"[$€£¥]?\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|bn|USD|EUR|GBP)?", cands["amount"][0])
        if hit:
            cands["amount"] = (quantity(hit.group(0))["value"] or cands["amount"][0], cands["amount"][1])
    if "date" in cands:
        resolved = natural_date(cands["date"][0])
        if resolved["kind"] != "unknown":
            cands["date"] = (resolved["value"], cands["date"][1])

    out: List[Dict[str, Any]] = []
    for f in fields:
        name = f.get("name") if isinstance(f, dict) else str(f)
        label = (f.get("label") if isinstance(f, dict) else "") or name
        for probe in (name, label):
            hit = cands.get(_canonical(probe or ""))
            if hit and hit[0]:
                out.append({"name": name, "value": hit[0], "confidence": round(hit[1], 2)})
                break
    return out


_TYPO_DOMAINS = {"gmial.com": "gmail.com", "gmai.com": "gmail.com", "gmail.con": "gmail.com", "gmail.co": "gmail.com",
                 "hotmial.com": "hotmail.com", "yaho.com": "yahoo.com", "yahoo.con": "yahoo.com", "outlok.com": "outlook.com",
                 "iclod.com": "icloud.com", "gnail.com": "gmail.com"}


def heal_format(value: str, kind: str) -> Dict[str, Any]:
    """Repair common formatting mistakes and report whether the value is plausible."""
    raw = (value or "").strip()
    kind = (kind or "").lower()
    fixed, ok, note = raw, True, ""
    if kind == "email":
        fixed = re.sub(r"\s+", "", raw).replace(",", ".")
        if "@" in fixed:
            local, _, domain = fixed.rpartition("@")
            domain = domain.lower()
            domain = _TYPO_DOMAINS.get(domain, domain)
            fixed = local + "@" + domain
        ok = bool(re.fullmatch(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", fixed))
        note = "Corrected the domain." if ok and fixed.lower() != re.sub(r"\s+", "", raw).lower() else ("" if ok else "An email needs a name, @ and a domain.")
    elif kind in ("phone", "tel"):
        digits = re.sub(r"\D", "", raw)
        plus = raw.startswith("+")
        if len(digits) == 10 and not plus:
            fixed = "(%s) %s-%s" % (digits[:3], digits[3:6], digits[6:])
        elif len(digits) == 11 and digits[0] == "1":
            fixed = "+1 (%s) %s-%s" % (digits[1:4], digits[4:7], digits[7:])
        elif plus and len(digits) >= 8:
            fixed = "+" + digits[:2] + " " + " ".join(re.findall(r"\d{1,4}", digits[2:]))
        ok = 7 <= len(digits) <= 15
        note = "" if ok else "Phone numbers have 7–15 digits."
    elif kind in ("url", "website"):
        fixed = re.sub(r"\s+", "", raw)
        if fixed and not re.match(r"^[a-z][a-z0-9+.\-]*://", fixed, re.IGNORECASE):
            fixed = "https://" + fixed
        m = re.match(r"^(\w+://)([^/]+)(.*)$", fixed)
        if m:
            fixed = m.group(1).lower() + m.group(2).lower() + m.group(3)
        ok = bool(re.match(r"^https?://[a-z0-9\-]+(\.[a-z0-9\-]+)+", fixed))
        note = "" if ok else "That doesn't look like a web address."
    elif kind in ("card", "credit_card"):
        digits = re.sub(r"\D", "", raw)
        fixed = " ".join(re.findall(r"\d{1,4}", digits))
        ok = 13 <= len(digits) <= 19 and luhn(digits)
        note = "" if ok else "The card number fails its checksum; re-check the digits."
    elif kind == "iban":
        compact = re.sub(r"\s+", "", raw).upper()
        fixed = " ".join(re.findall(r".{1,4}", compact))
        ok = False
        if re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", compact):
            rearranged = compact[4:] + compact[:4]
            ok = int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1
        note = "" if ok else "The IBAN checksum does not match."
    elif kind in ("postal", "zip"):
        compact = re.sub(r"\s+", "", raw).upper()
        if re.fullmatch(r"\d{9}", compact):
            fixed = compact[:5] + "-" + compact[5:]
        elif re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}", compact):
            fixed = compact[:-3] + " " + compact[-3:]
        else:
            fixed = raw.upper()
        ok = bool(re.fullmatch(r"[A-Z0-9][A-Z0-9 \-]{2,9}", fixed))
    elif kind == "name":
        fixed = " ".join(p[:1].upper() + p[1:].lower() if p.islower() or p.isupper() else p for p in raw.split())
        ok = bool(re.search(r"[^\W\d_]", fixed))
    elif kind in ("number", "amount"):
        q = quantity(raw)
        fixed, ok = (q["value"] or raw), q["confidence"] > 0
    return {"value": fixed, "ok": ok, "changed": fixed != raw, "note": note}


def synth_mask(examples: List[str]) -> Dict[str, str]:
    """Infer an input mask and a validating regex from example values."""
    examples = [e for e in examples if isinstance(e, str) and e]
    if not examples:
        return {"mask": "", "regex": "", "placeholder": ""}

    def shape(s: str) -> str:
        return "".join("9" if c.isdigit() else ("A" if c.isalpha() else c) for c in s)

    shapes = [shape(e) for e in examples]
    if len(set(shapes)) == 1:
        mask = shapes[0]
    else:
        runs = [re.findall(r"9+|A+|[^9A]", s) for s in shapes]
        if len({len(r) for r in runs}) == 1 and all(len({r[i][0] for r in runs}) == 1 for i in range(len(runs[0]))):
            mask = "".join(max((r[i] for r in runs), key=len) for i in range(len(runs[0])))
        else:
            mask = max(shapes, key=len)
    regex = "^"
    for run in re.findall(r"9+|A+|[^9A]", mask):
        if run[0] == "9":
            lengths = sorted({len(r) for s in shapes for r in re.findall(r"9+", s)} or {len(run)})
            regex += r"\d{%d}" % len(run) if len(set(shapes)) == 1 else r"\d{%d,%d}" % (min(lengths[0], len(run)), len(run))
        elif run[0] == "A":
            regex += "[A-Za-z]{%d}" % len(run) if len(set(shapes)) == 1 else "[A-Za-z]{1,%d}" % len(run)
        else:
            regex += re.escape(run)
    placeholder = "".join("0" if c == "9" else ("X" if c == "A" else c) for c in mask)
    return {"mask": mask, "regex": regex + "$", "placeholder": placeholder}


_OPENERS = {"the", "a", "an", "this", "that", "these", "those", "our", "your", "their", "my", "we", "they", "it", "he", "she", "please", "when", "if", "after", "before"}


def entities(text: str) -> List[Dict[str, str]]:
    """Light-weight entity spotting for hover cards."""
    raw = text or ""
    found: List[Dict[str, str]] = []
    seen = set()

    def add(kind: str, value: str) -> None:
        value = value.strip().rstrip(".,;")
        if value and (kind, value) not in seen:
            seen.add((kind, value))
            found.append({"kind": kind, "text": value})

    for f in find_pii(raw, ["email", "phone"]):
        add(f["kind"], f["value"])
    for m in re.finditer(r"\b(?:https?://|www\.)[^\s,;]+", raw):
        add("url", m.group(0))
    for m in re.finditer(r"[$€£¥]\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|bn|million|billion)?\b", raw):
        add("money", m.group(0))
    for m in re.finditer(r"\b\d+(?:\.\d+)?\s?%", raw):
        add("percent", m.group(0))
    for m in re.finditer(r"\b(?:%s)\.?\s+\d{1,2}(?:,?\s+\d{4})?\b|\b\d{4}-\d{2}-\d{2}\b" % "|".join([mm.capitalize() for mm in MONTHS] + [mm[:3].capitalize() for mm in MONTHS]), raw):
        add("date", m.group(0))
    for m in re.finditer(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:%s)[a-z]*\.?(?:,?\s+\d{4})?\b" % "|".join(mm[:3].capitalize() for mm in MONTHS), raw):
        add("date", m.group(0))
    for m in re.finditer(r"\b[A-Z][\w&'\-]*(?:\s[A-Z][\w&'\-]*){0,3}\s(?:Inc|LLC|Ltd|GmbH|Corp|AG|PLC)\b\.?", raw):
        add("organization", m.group(0))
    for m in re.finditer(r"(?:^|(?<=[.!?]\s))([A-Z][a-zà-ÿ&]+(?:\s[A-Z][a-zà-ÿ&]+){1,2})(?=\s+(?:paid|owes?|ordered|signed|sent|bought|sold|shipped|announced|acquired|hired|invoiced|refunded|is|has|was|will)\b)", raw):
        if m.group(1).split()[0].lower() not in _OPENERS:
            add("organization", m.group(1))
    for m in re.finditer(r"\b(?:in|at|from|near|to|their|our|the)\s+([A-Z][a-zà-ÿ]+)\s+(?:office|branch|warehouse|store|headquarters|plant|site)\b", raw):
        add("place", m.group(1))
    for m in re.finditer(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-zà-ÿ]+(?:\s[A-Z][a-zà-ÿ]+){1,2})\b", raw):
        value = m.group(1)
        if not any(value in f["text"] for f in found) and value.split()[0].lower() not in MONTHS:
            add("person", value)
    return found
