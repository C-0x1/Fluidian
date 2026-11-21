"""Reflex data intelligence: typing, chart choice, insights, anomalies, queries.

The functions here compute *facts* (statistics, types, filters).  In Reason
mode those facts are handed to the model so that narration is grounded in
numbers the engine calculated itself.
"""
from __future__ import annotations

import ast
import hashlib
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import parse as P
from . import text as T

Row = Dict[str, Any]


def to_number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, str):
        s = value.strip().replace(",", "")
        m = re.fullmatch(r"[$€£¥]?\s*(-?\d+(?:\.\d+)?)\s*(%|k|m|bn)?", s, re.IGNORECASE)
        if m:
            mult = {"k": 1e3, "m": 1e6, "bn": 1e9}.get((m.group(2) or "").lower(), 1)
            return float(m.group(1)) * mult
    return None


def _is_date(value: Any) -> bool:
    return isinstance(value, str) and bool(re.match(r"^\d{4}-\d{2}(-\d{2})?([T ]\d{2}:\d{2})?", value.strip()))


_MONTH_ABBR = [m[:3] for m in P.MONTHS]


def _is_temporal_label(value: Any) -> bool:
    if _is_date(value):
        return True
    if isinstance(value, str):
        s = value.strip().lower()
        return s[:3] in _MONTH_ABBR or bool(re.fullmatch(r"(q[1-4]|w\d{1,2}|week \d+|\d{4}|fy\d{2,4}|h[12])( ?'?\d{2,4})?", s)) \
            or s[:3] in [w[:3] for w in P.WEEKDAYS]
    return False


def column_types(rows: List[Row]) -> List[Dict[str, Any]]:
    """Infer a semantic type, display format and alignment for every column."""
    keys: List[str] = []
    for row in rows[:200]:
        for key in row:
            if key not in keys:
                keys.append(key)
    out = []
    for key in keys:
        values = [r.get(key) for r in rows if r.get(key) not in (None, "")]
        sample = values[:200]
        name = key.lower()
        unique = len({str(v) for v in sample})
        kind, fmt = "text", "text"
        if sample and all(isinstance(v, bool) for v in sample):
            kind, fmt = "boolean", "badge"
        elif sample and all(_is_date(v) for v in sample):
            kind, fmt = "date", "date"
        elif sample and all(to_number(v) is not None for v in sample):
            kind, fmt = "number", "number"
            strings = [v for v in sample if isinstance(v, str)]
            if any(re.match(r"^[$€£¥]", s.strip()) for s in strings) or re.search(r"(price|amount|revenue|cost|mrr|arr|total|spend|salary|budget|balance|fee)", name):
                kind, fmt = "currency", "currency"
            elif any(s.strip().endswith("%") for s in strings) or re.search(r"(rate|percent|pct|share|ratio|margin|churn|growth)", name):
                kind, fmt = "percent", "percent"
            elif re.search(r"(^id$|_id$|uuid|code$|zip|postal|year$)", name):
                kind, fmt = "id", "text"
        elif sample and all(isinstance(v, str) and re.fullmatch(r"[^@\s]+@[^@\s]+\.\w+", v) for v in sample):
            kind = "email"
        elif sample and all(isinstance(v, str) and re.match(r"^https?://", v) for v in sample):
            kind = "url"
        elif sample and all(isinstance(v, str) for v in sample):
            statusy = bool(re.search(r"(status|state|stage|priority|tier|plan|type|risk|level|category|role)", name))
            if (unique <= max(3, min(12, int(len(sample) * 0.6))) or (statusy and unique <= 12)) and all(len(v) <= 24 for v in sample):
                kind, fmt = "category", ("badge" if re.search(r"(status|state|stage|priority|risk|level)", name) else "text")
            elif _is_temporal_label(sample[0]) and all(_is_temporal_label(v) for v in sample):
                kind = "period"
        out.append({"key": key, "label": T.sentence_case(re.sub(r"[_\-]+", " ", re.sub(r"(?<=[a-z])(?=[A-Z])", " ", key))),
                    "type": kind, "format": fmt, "align": "end" if kind in ("number", "currency", "percent") else "start",
                    "unique": unique, "missing": len(rows) - len(values)})
    return out


def fmt(value: float, style: str = "number") -> str:
    if style == "currency":
        return "$" + ("{:,.0f}".format(value) if abs(value) >= 100 else "{:,.2f}".format(value))
    if style == "percent":
        return "{:.1f}%".format(value)
    if abs(value) >= 1e6:
        return "{:.1f}M".format(value / 1e6)
    if abs(value) >= 1e4:
        return "{:,.0f}".format(value)
    return "{:,.2f}".format(value).rstrip("0").rstrip(".")


def choose_chart(rows: List[Row], question: str = "") -> Dict[str, Any]:
    """Pick the chart form that best answers the question for this data shape."""
    cols = column_types(rows)
    numeric = [c for c in cols if c["type"] in ("number", "currency", "percent")]
    temporal = [c for c in cols if c["type"] in ("date", "period")]
    category = [c for c in cols if c["type"] in ("category", "text", "period") and c["unique"] <= 40]
    q = (question or "").lower()
    if not numeric:
        return {"kind": "table", "x": "", "y": [], "rationale": "No numeric measure to plot; a table keeps every value readable.", "confidence": 0.7}
    y = [c["key"] for c in numeric[:3]]
    if temporal:
        kind = "area" if re.search(r"\b(cumulative|total|volume|stack)", q) else "line"
        why = "Values are ordered in time, so a %s shows direction and rate of change." % kind
        x = temporal[0]["key"]
    elif len(numeric) >= 2 and not category or re.search(r"\b(correlat|relationship|versus|vs\.?|against)\b", q):
        kind, x, y = "scatter", numeric[0]["key"], [numeric[1]["key"] if len(numeric) > 1 else numeric[0]["key"]]
        why = "Two measures per record: a scatter plot exposes correlation and outliers."
    else:
        x = (category[0]["key"] if category else cols[0]["key"])
        share = re.search(r"\b(share|proportion|breakdown|split|composition|percent of|mix)\b", q)
        if share and len(rows) <= 6 and len(y) >= 1:
            kind, y = "donut", y[:1]
            why = "A part-to-whole question with few categories reads fastest as a donut."
        else:
            kind = "bar"
            why = "Comparing a measure across categories: bars make ranking and gaps obvious."
    return {"kind": kind, "x": x, "y": y, "rationale": why, "confidence": 0.8 if temporal or category else 0.65}


def _series(rows: List[Row], key: str) -> List[float]:
    return [v for v in (to_number(r.get(key)) for r in rows) if v is not None]


def linear_fit(values: List[float]) -> Tuple[float, float, float]:
    """Least-squares slope, intercept and r² over index positions."""
    n = len(values)
    if n < 2:
        return 0.0, (values[0] if values else 0.0), 0.0
    mx, my = (n - 1) / 2, sum(values) / n
    sxx = sum((i - mx) ** 2 for i in range(n))
    sxy = sum((i - mx) * (v - my) for i, v in enumerate(values))
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    ss_tot = sum((v - my) ** 2 for v in values)
    ss_res = sum((v - (intercept + slope * i)) ** 2 for i, v in enumerate(values))
    return slope, intercept, (1 - ss_res / ss_tot) if ss_tot else 0.0


def facts(rows: List[Row], x: str = "", y: str = "") -> Dict[str, Any]:
    """Statistics the narrative capabilities are grounded on."""
    cols = column_types(rows)
    if not y:
        y = next((c["key"] for c in cols if c["type"] in ("number", "currency", "percent")), "")
    if not x:
        x = next((c["key"] for c in cols if c["type"] in ("date", "period", "category", "text")), "")
    style = next((c["format"] for c in cols if c["key"] == y), "number")
    pairs = [(str(r.get(x, i)), to_number(r.get(y))) for i, r in enumerate(rows)]
    pairs = [(label, v) for label, v in pairs if v is not None]
    values = [v for _, v in pairs]
    if not values:
        return {"x": x, "y": y, "count": 0, "format": style}
    total, mean = sum(values), sum(values) / len(values)
    hi = max(pairs, key=lambda p: p[1])
    lo = min(pairs, key=lambda p: p[1])
    slope, _, r2 = linear_fit(values)
    change = ((values[-1] - values[0]) / abs(values[0]) * 100) if values[0] else 0.0
    steps = [(pairs[i][0], values[i] - values[i - 1]) for i in range(1, len(values))]
    jump = max(steps, key=lambda s: abs(s[1])) if steps else ("", 0.0)
    ordered = any(c["key"] == x and c["type"] in ("date", "period") for c in cols)
    return {"x": x, "y": y, "format": style, "count": len(values), "total": total, "mean": mean,
            "max": {"label": hi[0], "value": hi[1]}, "min": {"label": lo[0], "value": lo[1]},
            "first": values[0], "last": values[-1], "changePct": change, "slope": slope, "r2": r2,
            "trend": "up" if slope > 0 and r2 > 0.3 else ("down" if slope < 0 and r2 > 0.3 else "flat"),
            "biggestStep": {"label": jump[0], "delta": jump[1]}, "ordered": ordered,
            "topShare": (hi[1] / total * 100) if total else 0.0}


def insights(rows: List[Row], x: str = "", y: str = "") -> Dict[str, Any]:
    f = facts(rows, x, y)
    if not f.get("count"):
        return {"title": "Nothing to analyse yet", "body": "There are no numeric values in this data.", "bullets": [],
                "confidence": 0.3, "tone": "neutral"}
    style, label = f["format"], T.sentence_case(re.sub(r"[_\-]+", " ", f["y"]))
    bullets = ["Highest: %s (%s)" % (f["max"]["label"], fmt(f["max"]["value"], style)),
               "Lowest: %s (%s)" % (f["min"]["label"], fmt(f["min"]["value"], style)),
               "Average %s across %d points" % (fmt(f["mean"], style), f["count"])]
    if f["ordered"] and f["count"] > 2:
        noisy = f["trend"] == "flat" and abs(f["changePct"]) >= 10
        direction = "uneven, with no clear trend" if noisy else {"up": "rising", "down": "falling", "flat": "holding steady"}[f["trend"]]
        title = "%s is %s" % (label, direction)
        body = "%s moved from %s to %s, a %+.1f%% change over the period." % (
            label, fmt(f["first"], style), fmt(f["last"], style), f["changePct"])
        if noisy:
            body += " The swings between points are larger than the overall trend."
        if f["biggestStep"]["label"]:
            bullets.append("Largest single move: %s%s at %s" % ("+" if f["biggestStep"]["delta"] >= 0 else "−",
                                                              fmt(abs(f["biggestStep"]["delta"]), style), f["biggestStep"]["label"]))
        tone = "success" if f["trend"] == "up" else ("warning" if f["trend"] == "down" else "info")
        confidence = 0.55 + 0.4 * min(1.0, max(0.0, f["r2"]))
    else:
        title = "%s leads %s" % (f["max"]["label"], label.lower())
        body = "%s accounts for %.0f%% of the total (%s of %s)." % (
            f["max"]["label"], f["topShare"], fmt(f["max"]["value"], style), fmt(f["total"], style))
        tone, confidence = "info", 0.78
    return {"title": title, "body": body, "bullets": bullets[:4], "confidence": round(confidence, 2), "tone": tone}


def _median(values: List[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def anomalies(values: List[float], labels: Optional[List[str]] = None, threshold: float = 3.5) -> List[Dict[str, Any]]:
    """Robust outlier detection on the residuals around a Theil-Sen trend.

    A straight median/MAD test misses spikes in a series that is steadily
    rising or falling, because the trend itself inflates the spread.  The
    trend is therefore removed first with a slope estimate that outliers
    cannot drag, and the residuals are scored with the modified z-score.
    """
    idx = [i for i, v in enumerate(values) if v is not None]
    if len(idx) < 5:
        return []
    vals = [float(values[i]) for i in idx]
    n = len(idx)
    if n <= 300:
        pairs = [(a, b) for a in range(n) for b in range(a + 1, n)]
    else:
        half = n // 2
        pairs = [(a, a + half) for a in range(n - half)]
    slope = _median([(vals[b] - vals[a]) / (idx[b] - idx[a]) for a, b in pairs])
    intercept = _median([v - slope * i for i, v in zip(idx, vals)])
    resid = [v - (intercept + slope * i) for i, v in zip(idx, vals)]
    centre = _median(resid)
    level = _median([abs(v) for v in vals])
    mad = max(_median([abs(r - centre) for r in resid]), level * 0.01, 1e-9)
    out = []
    for i, v, r in zip(idx, vals, resid):
        z = 0.6745 * (r - centre) / mad
        if abs(z) >= threshold and abs(r - centre) >= level * 0.05:
            expected = intercept + slope * i + centre
            out.append({"index": i, "label": labels[i] if labels and i < len(labels) else str(i), "value": values[i],
                        "direction": "high" if z > 0 else "low", "z": round(z, 1), "expected": round(expected, 4)})
    return out


def forecast(values: List[float], horizon: int = 3) -> List[Dict[str, float]]:
    slope, intercept, _ = linear_fit(values)
    n = len(values)
    resid = [v - (intercept + slope * i) for i, v in enumerate(values)]
    spread = (sum(r * r for r in resid) / max(1, n - 2)) ** 0.5 if n > 2 else 0.0
    out = []
    for h in range(1, max(1, min(horizon, 24)) + 1):
        point = intercept + slope * (n - 1 + h)
        band = 1.28 * spread * math.sqrt(1 + h / max(1, n))
        out.append({"step": h, "value": round(point, 4), "low": round(point - band, 4), "high": round(point + band, 4)})
    return out


_OPS = [(r"(?:>=|at least|no less than|minimum of)", "gte"), (r"(?:<=|at most|no more than|up to|maximum of)", "lte"),
        (r"(?:>|over|above|greater than|more than|exceeds?|higher than)", "gt"),
        (r"(?:<|under|below|less than|fewer than|lower than)", "lt"),
        (r"(?:!=|is not|isn't|not equal to|except|excluding)", "neq"), (r"(?:contains?|including|with|like|matching)", "contains"),
        (r"(?:=|is|equals?|equal to)", "eq")]


def _match_column(phrase: str, cols: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    phrase = phrase.strip().lower()
    if not phrase:
        return None
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()  # noqa: E731
    target = norm(phrase)
    for c in cols:
        if target in (norm(c["key"]), norm(c["label"])):
            return c
    for c in cols:
        names = {norm(c["key"]), norm(c["label"])}
        if any(target.rstrip("s") == n.rstrip("s") or target in n.split() or n in target.split() for n in names):
            return c
    return None


def nl_query(question: str, rows: List[Row]) -> Dict[str, Any]:
    """Translate "overdue invoices over $5k, newest first" into filter / sort / limit."""
    cols = column_types(rows)
    q = " " + re.sub(r"\s+", " ", (question or "").lower().strip()) + " "
    filters: List[Dict[str, Any]] = []
    sort: List[Dict[str, str]] = []
    limit = 0
    notes: List[str] = []
    numeric = [c for c in cols if c["type"] in ("number", "currency", "percent")]
    names = sorted({n for c in cols for n in (c["key"].lower(), c["label"].lower())}, key=len, reverse=True)
    col_alt = "|".join(re.escape(n) for n in names) or "$^"

    m = re.search(r"\b(top|first|bottom|last|lowest|highest|largest|smallest|best|worst)\s+(\d+)(?:\s+\w+)?(?:\s+by\s+([\w ]+?))?(?=\s+(?:where|with|over|under|above|below|and|,|$)|\s*$)", q)
    if m:
        limit = int(m.group(2))
        col = _match_column(m.group(3) or "", cols) or (numeric[0] if numeric else None)
        if col:
            sort.append({"column": col["key"], "dir": "asc" if m.group(1) in ("bottom", "lowest", "smallest", "worst") else "desc"})
    m = re.search(r"\b(?:sort(?:ed)?|order(?:ed)?|rank(?:ed)?)\s+by\s+(%s)(?:\s+(asc|ascending|desc|descending|low to high|high to low))?" % col_alt, q)
    if m:
        col = _match_column(m.group(1), cols)
        if col:
            direction = "desc" if (m.group(2) or "").startswith(("desc", "high")) else "asc"
            sort = [{"column": col["key"], "dir": direction}]
    for word, direction in (("newest", "desc"), ("latest", "desc"), ("most recent", "desc"), ("oldest", "asc"), ("earliest", "asc")):
        date_col = next((c for c in cols if c["type"] == "date"), None)
        if word in q and date_col and not sort:
            sort.append({"column": date_col["key"], "dir": direction})
    for word, direction in (("highest", "desc"), ("largest", "desc"), ("biggest", "desc"), ("most", "desc"), ("lowest", "asc"), ("smallest", "asc"), ("least", "asc"), ("cheapest", "asc")):
        m = re.search(r"\b%s\s+(%s)\b" % (word, col_alt), q)
        if m and not sort:
            col = _match_column(m.group(1), cols)
            if col:
                sort.append({"column": col["key"], "dir": direction})

    for pattern, op in _OPS:
        for m in re.finditer(r"\b(%s)\s+%s\s+([$€£¥]?\s?-?[\d.,]+\s?(?:k|m|bn|%%)?|\"[^\"]+\"|'[^']+'|[\w\-@.]+)" % (col_alt, pattern), q):
            col = _match_column(m.group(1), cols)
            if not col or any(f["column"] == col["key"] and f["span"] == m.span(1) for f in filters):
                continue
            raw = m.group(2).strip().strip("\"'")
            number = to_number(raw)
            value: Any = number if (number is not None and col["type"] in ("number", "currency", "percent", "id")) else raw
            if isinstance(value, str) and op in ("gt", "lt", "gte", "lte"):
                continue
            filters.append({"column": col["key"], "op": op, "value": value, "span": m.span(1)})
    if not any(f["op"] in ("gt", "gte", "lt", "lte") for f in filters) and numeric:
        for pattern, op in _OPS[:4]:
            m = re.search(r"\s%s\s+([$€£¥]?\s?-?[\d.,]+\s?(?:k|m|bn|%%)?)(?=\s|,|$)" % pattern, q)
            if m and to_number(m.group(1).strip()) is not None:
                money = re.search(r"[$€£¥]", m.group(1))
                col = next((c for c in numeric if c["type"] == "currency"), numeric[0]) if money else numeric[0]
                filters.append({"column": col["key"], "op": op, "value": to_number(m.group(1).strip()), "span": (0, 0)})
                break
    m = re.search(r"\bbetween\s+([$€£¥]?[\d.,]+\s?(?:k|m)?)\s+and\s+([$€£¥]?[\d.,]+\s?(?:k|m)?)", q)
    if m and numeric:
        filters.append({"column": numeric[0]["key"], "op": "gte", "value": to_number(m.group(1)), "span": (0, 0)})
        filters.append({"column": numeric[0]["key"], "op": "lte", "value": to_number(m.group(2)), "span": (0, 0)})
    used = {f["column"] for f in filters}
    for c in cols:
        if c["type"] not in ("category", "boolean") or c["key"] in used:
            continue
        distinct = sorted({str(r.get(c["key"])) for r in rows if r.get(c["key"]) not in (None, "")}, key=len, reverse=True)
        for value in distinct:
            if re.search(r"\b%s\b" % re.escape(value.lower()), q):
                negated = re.search(r"\b(not|non|except|excluding|without)\s+%s\b" % re.escape(value.lower()), q)
                filters.append({"column": c["key"], "op": "neq" if negated else "eq", "value": value, "span": (0, 0)})
                break
    for f in filters:
        f.pop("span", None)
    for f in filters:
        notes.append("%s %s %s" % (f["column"], {"eq": "=", "neq": "≠", "gt": ">", "gte": "≥", "lt": "<", "lte": "≤", "contains": "contains"}[f["op"]], f["value"]))
    for srt in sort:
        notes.append("sorted by %s %s" % (srt["column"], "descending" if srt["dir"] == "desc" else "ascending"))
    if limit:
        notes.append("first %d rows" % limit)
    return {"filters": filters, "sort": sort, "limit": limit,
            "explanation": "; ".join(notes) if notes else "No filter recognised — showing every row.",
            "confidence": 0.85 if notes else 0.2}


def apply_query(rows: List[Row], spec: Dict[str, Any]) -> List[Row]:
    def keep(row: Row) -> bool:
        for f in spec.get("filters") or []:
            cell, target, op = row.get(f.get("column")), f.get("value"), f.get("op")
            a, b = to_number(cell), to_number(target)
            if op in ("gt", "gte", "lt", "lte"):
                if a is None or b is None:
                    return False
                if not {"gt": a > b, "gte": a >= b, "lt": a < b, "lte": a <= b}[op]:
                    return False
            elif op == "contains":
                if str(target).lower() not in str(cell).lower():
                    return False
            else:
                same = (a == b) if (a is not None and b is not None) else str(cell).lower() == str(target).lower()
                if same != (op == "eq"):
                    return False
        return True

    out = [r for r in rows if keep(r)]
    for srt in reversed(spec.get("sort") or []):
        key = srt.get("column")
        numbers = all(to_number(r.get(key)) is not None for r in out if r.get(key) not in (None, ""))
        out.sort(key=lambda r, key=key, numbers=numbers: ((to_number(r.get(key)) or 0.0) if numbers else str(r.get(key) or "").lower()),
                 reverse=srt.get("dir") == "desc")
    limit = spec.get("limit") or 0
    return out[:limit] if limit else out


def _trigrams(text: str) -> set:
    s = "  " + re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip() + " "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def dedupe(records: List[Any], keys: Optional[List[str]] = None, threshold: float = 0.72) -> List[Dict[str, Any]]:
    """Group records that are probably the same entity (trigram similarity)."""
    def flat(r: Any) -> str:
        if isinstance(r, dict):
            return " ".join(str(r.get(k, "")) for k in (keys or list(r.keys())))
        return str(r)

    grams = [_trigrams(flat(r)) for r in records]
    cluster = list(range(len(records)))
    scores: Dict[int, float] = {}
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            union = len(grams[i] | grams[j])
            sim = len(grams[i] & grams[j]) / union if union else 0.0
            if sim >= threshold:
                root_i, root_j = cluster[i], cluster[j]
                for k in range(len(cluster)):
                    if cluster[k] == root_j:
                        cluster[k] = root_i
                scores[root_i] = max(scores.get(root_i, 0.0), sim)
    groups: Dict[int, List[int]] = {}
    for idx, root in enumerate(cluster):
        groups.setdefault(root, []).append(idx)
    return [{"indices": members, "similarity": round(scores.get(root, 1.0), 2)}
            for root, members in groups.items() if len(members) > 1]


_ALLOWED_FUNCS = {"sum": sum, "avg": lambda xs: sum(xs) / len(xs) if xs else 0.0, "min": min, "max": max,
                  "count": len, "round": round, "abs": abs}


def formula_from_text(description: str, columns: List[str]) -> Dict[str, Any]:
    """Derive a computed-column expression from a plain description."""
    d = " " + (description or "").lower() + " "
    cols = sorted(columns, key=len, reverse=True)

    def find_cols() -> List[str]:
        found = []
        for c in cols:
            names = {c.lower(), re.sub(r"[_\-]+", " ", c.lower())}
            pos = min((d.find(n) for n in names if n in d), default=-1)
            if pos >= 0:
                found.append((pos, c))
        return [c for _, c in sorted(found)]

    hit = find_cols()
    expr, why = "", ""
    const = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(%|percent)?", d)
    if len(hit) == 1 and const:
        col, n, pct = hit[0], float(const.group(1)), bool(const.group(2))
        num = lambda v: ("%.4f" % v).rstrip("0").rstrip(".")
        if pct and re.search(r"\b(plus|add|adding|with|including|incl|tax|vat|markup|increase[d]?)\b", d):
            expr, why = "%s * %s" % (col, num(1 + n / 100)), "The column increased by %s%%." % num(n)
        elif pct and re.search(r"\b(minus|less|discount|off|reduce[d]?)\b", d):
            expr, why = "%s * %s" % (col, num(1 - n / 100)), "The column reduced by %s%%." % num(n)
        elif pct:
            expr, why = "%s * %s" % (col, num(n / 100)), "%s%% of the column." % num(n)
        elif re.search(r"\b(times|multiplied by|x)\b|\*", d):
            expr, why = "%s * %s" % (col, num(n)), "The column scaled by a constant."
        elif re.search(r"\b(divided by|over)\b|/", d):
            expr, why = "%s / %s" % (col, num(n)), "The column divided by a constant."
        elif re.search(r"\b(plus|add)\b|\+", d):
            expr, why = "%s + %s" % (col, num(n)), "A constant added to the column."
        elif re.search(r"\b(minus|less|subtract)\b", d):
            expr, why = "%s - %s" % (col, num(n)), "A constant subtracted from the column."
    if expr:
        pass
    elif re.search(r"\b(percent(age)? (change|growth|increase)|growth|change) (from|between)\b", d) and len(hit) >= 2:
        expr, why = "(%s - %s) / %s * 100" % (hit[1], hit[0], hit[0]), "Percentage change from the first value to the second."
    elif re.search(r"\b(margin)\b", d) and len(hit) >= 2:
        expr, why = "(%s - %s) / %s * 100" % (hit[0], hit[1], hit[0]), "Margin as a percentage of the first value."
    elif re.search(r"\b(percent|percentage|share|ratio)\b.*\bof\b", d) and len(hit) >= 2:
        expr, why = "%s / %s * 100" % (hit[0], hit[1]), "The first value as a percentage of the second."
    elif re.search(r"\b(times|multiplied by|product of|\*|x)\b", d) and len(hit) >= 2:
        expr, why = " * ".join(hit[:3]), "Product of the referenced columns."
    elif re.search(r"\b(minus|less|subtract|difference|net of|-)\b", d) and len(hit) >= 2:
        expr, why = "%s - %s" % (hit[0], hit[1]), "Difference between the two columns."
    elif re.search(r"\b(divided by|per|over|/)\b", d) and len(hit) >= 2:
        expr, why = "%s / %s" % (hit[0], hit[1]), "Ratio of the two columns."
    elif re.search(r"\b(average|mean|avg)\b", d) and hit:
        expr, why = "avg(%s)" % hit[0], "Mean of the column across all rows."
    elif re.search(r"\b(total|sum|add up|plus|\+)\b", d) and hit:
        expr, why = (" + ".join(hit) if len(hit) > 1 else "sum(%s)" % hit[0]), "Sum of the referenced values."
    elif re.search(r"\b(maximum|max|highest|largest)\b", d) and hit:
        expr, why = "max(%s)" % hit[0], "Largest value in the column."
    elif re.search(r"\b(minimum|min|lowest|smallest)\b", d) and hit:
        expr, why = "min(%s)" % hit[0], "Smallest value in the column."
    elif re.search(r"\b(count|number of|how many)\b", d):
        expr, why = "count(%s)" % (hit[0] if hit else (columns[0] if columns else "rows")), "Number of rows."
    return {"expression": expr, "explanation": why or "No formula pattern recognised.", "columns": hit,
            "confidence": 0.8 if expr else 0.1}


def evaluate(expression: str, row: Row, rows: Optional[List[Row]] = None) -> Optional[float]:
    """Safely evaluate an arithmetic expression over a row (no attribute access, no calls beyond the allow-list)."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None

    def ev(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            return to_number(row.get(node.id)) or 0.0
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -ev(node.operand) if isinstance(node.op, ast.USub) else ev(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            a, b = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            return a / b if b else 0.0
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCS:
            name = node.func.id
            if name in ("sum", "avg", "min", "max", "count") and len(node.args) == 1 and isinstance(node.args[0], ast.Name):
                column = [to_number(r.get(node.args[0].id)) for r in (rows or [row])]
                column = [v for v in column if v is not None]
                return _ALLOWED_FUNCS[name](column) if column else 0.0
            return _ALLOWED_FUNCS[name](*[ev(a) for a in node.args])
        raise ValueError("unsupported expression")

    try:
        return float(ev(tree))
    except (ValueError, TypeError, ZeroDivisionError):
        return None


EMBED_DIMS = 256


def embed(text: str, dims: int = EMBED_DIMS) -> List[float]:
    """Deterministic local embedding: hashed word and character-trigram features, L2 normalised."""
    vec = [0.0] * dims
    tokens = T.words(text)
    feats = [(w, 1.0) for w in tokens if w not in T.STOP]
    feats += [(a + "_" + b, 0.6) for a, b in zip(tokens, tokens[1:])]
    for w in tokens:
        padded = "^" + w + "$"
        feats += [(padded[i:i + 3], 0.35) for i in range(len(padded) - 2)]
    for feat, weight in feats:
        h = int(hashlib.md5(feat.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % dims] += weight if (h >> 9) & 1 else -weight
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def search(query: str, docs: List[str], k: int = 5) -> List[Dict[str, Any]]:
    qv, qwords = embed(query), set(T.words(query)) - T.STOP
    scored = []
    for i, doc in enumerate(docs):
        overlap = len(qwords & set(T.words(doc))) / (len(qwords) or 1)
        scored.append((0.7 * cosine(qv, embed(doc)) + 0.3 * overlap, i))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [{"index": i, "score": round(max(0.0, s), 3), "text": docs[i]} for s, i in scored[:k] if s > 0.02]


_FIRST = ["Ada", "Grace", "Linus", "Mira", "Noor", "Kenji", "Sofia", "Omar", "Ines", "Tariq", "Lena", "Diego", "Yuki", "Amara", "Jonas", "Priya"]
_LAST = ["Lovelace", "Hopper", "Okafor", "Chen", "Haddad", "Tanaka", "Rossi", "Nasser", "Duarte", "Lindqvist", "Meyer", "Alvarez", "Sato", "Adeyemi", "Berg", "Raman"]
_COMPANY = ["Northwind", "Globex", "Initech", "Umbra Labs", "Heliotrope", "Kestrel & Co", "Brightwater", "Quanta", "Lumen Works", "Tidewater", "Ironbark", "Solstice"]
_CITY = ["Lisbon", "Osaka", "Toronto", "Nairobi", "Berlin", "Austin", "Oslo", "Mumbai", "Lyon", "Seoul", "Porto", "Denver"]
_STATUS = ["active", "pending", "paid", "overdue", "draft"]
_PRODUCT = ["Starter", "Scale", "Enterprise", "Add-on seats", "Priority support", "Audit pack"]


def fixtures(fields: List[Any], count: int = 5, seed: str = "fluidian") -> List[Row]:
    """Deterministic, realistic sample rows for a list of fields or a JSON Schema."""
    if isinstance(fields, dict):
        props = fields.get("properties", fields)
        fields = [{"name": k, "type": (v.get("type") if isinstance(v, dict) else None),
                   "format": (v.get("format") if isinstance(v, dict) else None),
                   "enum": (v.get("enum") if isinstance(v, dict) else None)} for k, v in props.items()]
    rows: List[Row] = []
    for i in range(max(0, min(count, 500))):
        row: Row = {}
        for f in fields:
            name = f.get("name") if isinstance(f, dict) else str(f)
            kind = (f.get("type") if isinstance(f, dict) else None) or ""
            enum = f.get("enum") if isinstance(f, dict) else None
            fmt_hint = (f.get("format") if isinstance(f, dict) else None) or ""
            pick = int(hashlib.md5(("%s|%s|%d" % (seed, name, i)).encode()).hexdigest()[:8], 16)
            low = name.lower()
            first, last = _FIRST[pick % len(_FIRST)], _LAST[(pick // 7) % len(_LAST)]
            if enum:
                value: Any = enum[pick % len(enum)]
            elif kind == "boolean" or low.startswith(("is_", "has_")) or low in ("active", "enabled", "verified"):
                value = pick % 3 != 0
            elif "email" in low or fmt_hint == "email":
                value = "%s.%s@%s.io" % (first.lower(), last.lower(), re.sub(r"[^a-z]", "", _COMPANY[pick % len(_COMPANY)].lower()))
            elif low in ("id", "uuid") or low.endswith("_id"):
                value = 1000 + i if kind in ("integer", "number") or low == "id" else "%s-%04d" % (low.split("_")[0][:3].upper() or "ID", 1000 + i)
            elif "first" in low:
                value = first
            elif "last" in low or "surname" in low:
                value = last
            elif "name" in low and ("company" in low or "account" in low or "org" in low):
                value = _COMPANY[pick % len(_COMPANY)]
            elif low in ("company", "customer", "account", "vendor", "organization", "client"):
                value = _COMPANY[pick % len(_COMPANY)]
            elif "name" in low or low in ("owner", "assignee", "author", "contact", "user"):
                value = "%s %s" % (first, last)
            elif "city" in low:
                value = _CITY[pick % len(_CITY)]
            elif "status" in low or "state" in low or "stage" in low:
                value = _STATUS[pick % len(_STATUS)]
            elif "product" in low or "plan" in low or "item" in low:
                value = _PRODUCT[pick % len(_PRODUCT)]
            elif "date" in low or low.endswith("_at") or fmt_hint in ("date", "date-time") or low in ("due", "created", "updated"):
                value = "2026-%02d-%02d" % (1 + pick % 12, 1 + (pick // 13) % 28)
            elif "phone" in low:
                value = "+1 (415) 555-%04d" % (pick % 10000)
            elif "url" in low or "website" in low or fmt_hint == "uri":
                value = "https://%s.example" % re.sub(r"[^a-z]", "", _COMPANY[pick % len(_COMPANY)].lower())
            elif re.search(r"(rate|percent|pct|margin|churn|growth)", low):
                value = round(1 + (pick % 2400) / 100.0, 1)
            elif re.search(r"(amount|price|revenue|total|mrr|arr|cost|budget|balance|salary)", low):
                value = round(120 + (pick % 98000) / 10.0, 2)
            elif kind in ("integer",) or re.search(r"(count|qty|quantity|seats|age|units|orders|users|score)", low):
                value = 1 + pick % 240
            elif kind == "number":
                value = round((pick % 100000) / 100.0, 2)
            elif "title" in low or "subject" in low:
                value = ["Renewal review", "Onboarding call", "Security questionnaire", "Pricing follow-up", "Quarterly sync"][pick % 5]
            else:
                value = ["Reviewed and approved.", "Waiting on the customer.", "Needs a second look.", "Scheduled for next sprint.", "No action required."][pick % 5]
            row[name] = value
        rows.append(row)
    return rows


def _headline(value: float, style: str) -> str:
    """Headline figures stay short: millions and billions are abbreviated."""
    for limit, suffix in ((1e9, "B"), (1e6, "M")):
        if abs(value) >= limit:
            return "%s%.2f%s" % ("$" if style == "currency" else "", value / limit, suffix)
    return fmt(value, style)


def kpis(rows: List[Row], limit: int = 4) -> List[Dict[str, Any]]:
    """Summarise numeric columns as headline figures with a half-over-half delta."""
    out = []
    for c in column_types(rows):
        if c["type"] not in ("number", "currency", "percent") or len(out) >= limit:
            continue
        values = _series(rows, c["key"])
        if not values:
            continue
        mean = c["type"] == "percent"
        headline = sum(values) / len(values) if mean else sum(values)
        half = len(values) // 2
        delta = 0.0
        if half:
            a, b = sum(values[:half]) / half, sum(values[half:]) / (len(values) - half)
            delta = (b - a) / abs(a) * 100 if a else 0.0
        out.append({"label": ("Avg " if mean else "Total ") + c["label"].lower(), "value": _headline(headline, c["format"]),
                    "delta": "%+.1f%%" % delta, "trend": "up" if delta > 0.5 else ("down" if delta < -0.5 else "flat"),
                    "spark": [round(v, 2) for v in values[-12:]]})
    return out


def pivots(rows: List[Row]) -> List[Dict[str, str]]:
    cols = column_types(rows)
    cats = [c for c in cols if c["type"] in ("category", "period") and 1 < c["unique"] <= 20]
    nums = [c for c in cols if c["type"] in ("number", "currency", "percent")]
    out = []
    for cat in cats[:3]:
        for num in nums[:2]:
            agg = "average" if num["type"] == "percent" else "sum"
            out.append({"label": "%s of %s by %s" % (agg.capitalize(), num["label"].lower(), cat["label"].lower()),
                        "detail": "%d groups" % cat["unique"], "value": "%s(%s) by %s" % (agg, num["key"], cat["key"]),
                        "group": cat["key"], "measure": num["key"], "aggregate": agg})
    return out


def parse_time(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    for pattern in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19] if "S" in pattern else value[:16] if "M" in pattern else value[:10], pattern)
        except ValueError:
            continue
    return None
