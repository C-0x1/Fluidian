"""Reflex composition: build scenes from intent, data, schemas, sketches and HTML."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from .. import components as C
from . import data as D
from . import design as G
from . import text as T

Node = Dict[str, Any]


def N(type_: str, *children: Any, id: Optional[str] = None, on: Optional[Dict[str, Any]] = None,
      ai: Optional[List[Any]] = None, **props: Any) -> Node:
    node: Node = {"type": type_, "props": {k: v for k, v in props.items() if v is not None}}
    kids = [c for c in children if c is not None]
    if kids:
        node["children"] = kids
    if id:
        node["id"] = id
    if on:
        node["on"] = on
    if ai:
        node["ai"] = ai
    return node


def label_of(name: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)
    return T.sentence_case(re.sub(r"[_\-.]+", " ", spaced).strip())


_ENTITIES: Dict[str, List[str]] = {
    "order": ["id", "customer", "total", "status", "date"],
    "invoice": ["id", "customer", "amount", "status", "due_date"],
    "customer": ["name", "email", "company", "plan", "status"],
    "user": ["name", "email", "role", "status", "last_seen_at"],
    "contact": ["name", "email", "company", "phone", "city"],
    "lead": ["name", "company", "stage", "amount", "owner"],
    "task": ["title", "assignee", "priority", "status", "due_date"],
    "ticket": ["subject", "customer", "priority", "status", "updated_at"],
    "product": ["product", "sku_id", "price", "quantity", "status"],
    "employee": ["name", "title", "city", "email", "start_date"],
    "transaction": ["date", "merchant_name", "category", "amount", "status"],
    "expense": ["date", "merchant_name", "category", "amount", "status"],
    "payment": ["date", "customer", "amount", "method", "status"],
    "project": ["name", "owner", "status", "due_date", "progress_pct"],
    "subscription": ["customer", "plan", "mrr", "status", "renewal_date"],
    "shipment": ["id", "customer", "city", "status", "date"],
}
_SELECT_OPTIONS = {"country": ["United States", "Canada", "United Kingdom", "Germany", "Japan", "Brazil"],
                   "plan": ["Starter", "Scale", "Enterprise"], "role": ["Viewer", "Editor", "Admin"],
                   "priority": ["Low", "Medium", "High", "Urgent"], "status": ["Draft", "Active", "Paused", "Archived"],
                   "category": ["General", "Billing", "Technical", "Feedback"], "type": ["Standard", "Custom"],
                   "department": ["Engineering", "Design", "Sales", "Support", "Finance"],
                   "currency": ["USD", "EUR", "GBP", "JPY"], "language": ["English", "Español", "Français", "Deutsch", "日本語"],
                   "size": ["Small", "Medium", "Large"], "frequency": ["Daily", "Weekly", "Monthly"]}


def field_for(name: str, schema: Optional[Dict[str, Any]] = None, required: bool = False) -> Node:
    """Choose the right input component for a field name and optional JSON Schema fragment."""
    schema = schema or {}
    key = re.sub(r"\s+", "_", name.strip().lower())
    label = schema.get("title") or label_of(name)
    help_text = schema.get("description")
    stype, sformat, enum = schema.get("type"), schema.get("format"), schema.get("enum")
    common: Dict[str, Any] = {"label": label, "help": help_text}
    if required:
        common["required"] = True
    if enum:
        if len(enum) <= 4:
            return N("RadioGroup" if len(enum) > 2 else "Segmented", name=key, options=[str(e) for e in enum],
                     value=schema.get("default"), label=label)
        return N("Select", name=key, options=[str(e) for e in enum], value=schema.get("default"), **common)
    if stype == "boolean" or re.search(r"^(is_|has_|enable|allow)|(terms|agree|subscribe|newsletter|remember|consent|opt_in|notifications?)$", key):
        return N("Checkbox" if re.search(r"(terms|agree|consent)", key) else "Toggle", name=key, label=label,
                 checked=bool(schema.get("default", False)), help=help_text)
    if stype in ("integer", "number"):
        if "minimum" in schema and "maximum" in schema and schema["maximum"] - schema["minimum"] <= 1000:
            return N("Slider", name=key, min=schema["minimum"], max=schema["maximum"], value=schema.get("default", schema["minimum"]), label=label)
        prefix = "$" if re.search(r"(amount|price|budget|cost|salary|total|fee)", key) else None
        return N("Input", name=key, kind="number", prefix=prefix, **common)
    if stype == "array":
        return N("TagInput", name=key, label=label, value=schema.get("default") or [])
    for base, options in _SELECT_OPTIONS.items():
        if key == base or key.endswith("_" + base):
            return N("Select", name=key, options=options, placeholder="Choose…", **common)
    if sformat == "email" or "email" in key:
        return N("Input", name=key, kind="email", placeholder="name@company.com", icon="mail", **common)
    if "password" in key or key in ("pin", "passcode"):
        return N("Input", name=key, kind="password", **common)
    if sformat in ("uri", "url") or re.search(r"(url|website|link|homepage)", key):
        return N("Input", name=key, kind="url", placeholder="https://", icon="link", **common)
    if re.search(r"(phone|mobile|tel)", key):
        return N("Input", name=key, kind="tel", icon="phone", **common)
    if sformat in ("date", "date-time") or re.search(r"(date|birthday|deadline|due|_at$|^when$)", key):
        return N("Input", name=key, kind="date", **common)
    if re.search(r"(?:^|_)(amount|price|budget|cost|quantity|qty|age|seats|count|total)(?:_|$)", key):
        return N("Input", name=key, kind="number", prefix="$" if re.search(r"(amount|price|budget|cost|total)", key) else None, **common)
    if re.search(r"(message|notes?|description|comments?|bio|details|feedback|summary|reason|address)", key) or schema.get("maxLength", 0) > 160:
        return N("TextArea", name=key, rows=3, **common)
    if re.search(r"(rating|stars|score)", key):
        return N("Rating", name=key, label=label)
    if re.search(r"(file|upload|attachment|photo|avatar|receipt|document|resume|cv)", key):
        return N("FileDrop", name=key, label="Drop %s here" % label.lower())
    if re.search(r"(tags|labels|keywords|skills)", key):
        return N("TagInput", name=key, label=label)
    return N("Input", name=key, placeholder=schema.get("examples", [None])[0] if isinstance(schema.get("examples"), list) else None, **common)


def _intent_fields(intent: str) -> List[str]:
    m = re.search(r"\b(?:with|including|fields?:?|asking for|collect(?:ing|s)?|capture[sd]?|containing|:)\s+(.+)$", intent, re.IGNORECASE)
    if not m:
        return []
    tail = re.split(r"\.\s|\bthen\b|\bso that\b", m.group(1))[0]
    parts = re.split(r",\s*(?:and\s+)?|\s+and\s+|\s*;\s*|\s*/\s*", tail)
    out = []
    for p in parts:
        p = re.sub(r"\b(a|an|the|their|your|optional|required|field|fields|input|inputs|dropdown|selector|picker|box|checkbox|toggle)\b", " ", p, flags=re.IGNORECASE)
        p = re.sub(r"[^\w\s\-]", "", p).strip()
        if 0 < len(p) <= 32 and len(p.split()) <= 4:
            out.append(p)
    return out[:14]


_DANGLING = {"a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with", "by", "at", "from", "after", "before", "into", "per"}
_COUNTS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_STEP_TITLES = ["Details", "Preferences", "Team", "Billing", "Integrations", "Review"]


def _intent_title(intent: str) -> str:
    s = re.sub(r"^\s*(please\s+)?(create|build|make|design|generate|show|give me|i need|i want|compose|draft|render)\s+(me\s+)?", "", intent.strip(), flags=re.IGNORECASE)
    s = re.sub(r"^(a|an|the)\s+", "", s, flags=re.IGNORECASE)
    s = re.split(r"\s+(?:with|including|that|which|for collecting|containing|showing|:)\s+", s, maxsplit=1)[0]
    words = s.split()
    if len(words) > 9:
        words = words[:9]
        while len(words) > 1 and words[-1].lower() in _DANGLING:
            words.pop()
    return T.title_case(" ".join(words)).rstrip(".,") or "Untitled"


def _entity(intent: str) -> Optional[str]:
    low = intent.lower()
    for name in _ENTITIES:
        if re.search(r"\b%ss?\b" % name, low) or (name.endswith("y") and re.search(r"\b%sies\b" % name[:-1], low)):
            return name
    return None


def _table_for(entity: str, count: int = 6, seed: str = "") -> Node:
    fields = _ENTITIES[entity]
    rows = D.fixtures(fields, count, seed or entity)
    cols = [{"key": c["key"], "label": c["label"], "format": c["format"], "align": c["align"]} for c in D.column_types(rows)]
    return N("Table", columns=cols, rows=rows, caption="%ss" % T.sentence_case(entity), dense=False)


def compose_intent(intent: str) -> Tuple[Node, str]:
    """Compose a scene for a plain-language description using archetype templates."""
    low = (intent or "").lower()
    title = _intent_title(intent or "")
    entity = _entity(low)
    fields = _intent_fields(intent or "")

    if re.search(r"\b(log ?in|sign ?in)\b", low):
        scene = N("Page", N("Card", N("Form", field_for("email", required=True), field_for("password", required=True),
                                       N("Row", N("Checkbox", name="remember", label="Keep me signed in"),
                                         N("Link", label="Forgot password?", href="/reset"), justify="between"),
                                       N("Button", label="Sign in", variant="primary", block=True), name="sign_in"),
                            title="Welcome back", subtitle="Sign in to continue", elevated=True), title=title, width="narrow")
        return scene, "Authentication archetype: two credentials, a recovery path and one primary action."
    if re.search(r"\b(pricing|plans?|tiers?)\b", low) and not fields:
        cards = []
        for name, price, feats, primary in (("Starter", "$0", ["3 projects", "Community support", "1 GB storage"], False),
                                            ("Scale", "$29", ["Unlimited projects", "Priority support", "100 GB storage"], True),
                                            ("Enterprise", "Custom", ["SSO and audit logs", "Dedicated manager", "Uptime SLA"], False)):
            cards.append(N("Card", N("Heading", text=price, level=2), N("List", items=[{"title": f, "icon": "check"} for f in feats], divided=False, dense=True),
                           N("Button", label="Choose %s" % name, variant="primary" if primary else "secondary", block=True),
                           title=name, tone="brand" if primary else "neutral", elevated=primary))
        return N("Page", N("Grid", *cards, columns=3), title=title, subtitle="Pick the plan that fits your team"), \
            "Pricing archetype: three comparable tiers with the recommended tier emphasised."
    if re.search(r"\b(dashboard|overview|analytics|metrics|kpis?|report|insights|performance|summary of)\b", low):
        ent = entity or "order"
        rows = D.fixtures(["month", "revenue", "orders", "churn_rate"], 8, low)
        for i, row in enumerate(rows):
            row["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"][i]
            row["revenue"] = round(42000 + i * 3100 + (row["orders"] % 9) * 700, 2)
        stats = [N("Stat", label=k["label"].capitalize(), value=k["value"], delta=k["delta"], trend=k["trend"], spark=k["spark"]) for k in D.kpis(rows, 3)]
        scene = N("Page", N("Grid", *stats, columns=3),
                  N("Split", N("Card", N("Chart", kind="area", data=rows, x="month", y="revenue", height=240), title="Revenue trend"),
                    N("Card", N("Chart", kind="bar", data=rows, x="month", y="orders", height=240), title="Orders"), ratio="3:2"),
                  N("Card", _table_for(ent, 5, low), title="Recent %ss" % ent, padding="none"),
                  title=title, subtitle="Updated moments ago")
        return scene, "Dashboard archetype: headline figures first, then trend, then the records behind them."
    if len(fields) < 2 and re.search(r"\b(feedback|survey|rate|rating|nps|satisfaction|csat)\b", low):
        scene = N("Page", N("Card", N("Form",
                                       N("Rating", name="rating", label="How satisfied are you?", max=5, value=0),
                                       N("Segmented", name="resolved", label="Was your issue resolved?", options=["Yes", "Partly", "No"]),
                                       N("TextArea", name="comments", label="What could we do better?", rows=3, placeholder="Optional"),
                                       N("Checkbox", name="contact_ok", label="You may contact me about this feedback"),
                                       N("Row", N("Button", label="Skip", variant="ghost"), N("Button", label="Send feedback", variant="primary", icon="send"), justify="end"),
                                       name="feedback"), subtitle="Takes less than a minute"), title=title, width="narrow")
        return scene, "Feedback archetype: one rating, one closed question, one open question and consent to follow up."
    steps_match = re.search(r"\b(\d|two|three|four|five|six)[- ]steps?\b", low)
    if steps_match or re.search(r"\b(wizard|onboard|onboarding|step[- ]by[- ]step|setup flow|multi[- ]step|checkout)\b", low):
        count = 3
        if steps_match:
            word = steps_match.group(1)
            count = max(2, min(6, int(word) if word.isdigit() else _COUNTS[word]))
        titles = _STEP_TITLES[:count - 1] + ["Review"]
        names = fields or ["name", "email", "company", "role"]
        scene = N("Page", N("Steps", items=[{"title": t} for t in titles], current=0),
                  N("Card", N("Form", N("Grid", *[field_for(n, required=i < 2) for i, n in enumerate(names[:4])], columns=2),
                              N("Row", N("Button", label="Back", variant="ghost", disabled=True), N("Button", label="Continue", variant="primary", icon="arrow-right"), justify="between"),
                              name="step_1"), title="Step 1 of %d · %s" % (count, titles[0]), subtitle="Tell us the basics"),
                  title=title)
        return scene, "Wizard archetype: %d steps, progress always visible, a small group of fields per step." % count
    if re.search(r"\b(chat|assistant|copilot|support bot|conversation)\b", low):
        return N("Page", N("Copilot", title=title, messages=[{"role": "assistant", "content": "Hi — what would you like to do?"}],
                           suggestions=["Summarise this page", "What changed this week?", "Draft a reply"]), title=title, width="narrow"), \
            "Conversational archetype: one focused thread with suggested openers."
    if re.search(r"\b(kanban|board|backlog|sprint|roadmap)\b", low):
        cards = D.fixtures(["title", "assignee"], 6, low)
        cols = [{"title": name, "cards": [{"title": c["title"], "assignee": c["assignee"], "tags": [tag]} for c in cards[i * 2:i * 2 + 2]]}
                for i, (name, tag) in enumerate((("Backlog", "idea"), ("In progress", "active"), ("Done", "shipped")))]
        return N("Page", N("Board", columns=cols), title=title), "Board archetype: work grouped by stage."
    if fields or re.search(r"\b(form|sign ?up|register|registration|create|new|add|edit|contact|survey|feedback|settings|preferences|profile|apply|application|request|booking|book|subscribe)\b", low):
        names = fields or (["name", "email", "message"] if re.search(r"\b(contact|feedback)\b", low) else
                           ["name", "email", "password", "terms"] if re.search(r"\b(sign ?up|register)", low) else
                           (_ENTITIES.get(entity or "", ["name", "email", "notes"])[:5]))
        inputs = [field_for(n, required=i == 0) for i, n in enumerate(names)]
        verb = "Create account" if re.search(r"\b(sign ?up|register)", low) else ("Send message" if re.search(r"\b(contact|feedback)\b", low) else
                                                                                   "Save changes" if re.search(r"\b(edit|settings|preferences|profile)\b", low) else "Submit")
        body = inputs
        if len(inputs) > 6:
            half = (len(inputs) + 1) // 2
            body = [N("Section", N("Grid", *inputs[:half], columns=2), title="Details"),
                    N("Section", N("Grid", *inputs[half:], columns=2), title="More information", divider=True)]
        scene = N("Page", N("Card", N("Form", *body, N("Row", N("Button", label="Cancel", variant="ghost"), N("Button", label=verb, variant="primary"), justify="end"),
                                       name=re.sub(r"\W+", "_", title.lower()).strip("_") or "form")), title=title, width="narrow")
        return scene, "Form archetype: %d fields with types inferred from their names and a single primary action." % len(inputs)
    if re.search(r"\b(detail|details|profile|record|view of|summary)\b", low):
        ent = entity or "customer"
        record = D.fixtures(_ENTITIES[ent], 1, low)[0]
        scene = N("Page", N("Split", N("Card", N("KeyValue", items=[{"key": label_of(k), "value": str(v)} for k, v in record.items()], columns=2), title="%s details" % T.sentence_case(ent)),
                            N("Card", N("Timeline", items=[{"title": "Created", "time": "Mar 2"}, {"title": "Updated", "time": "Mar 9", "tone": "info"}, {"title": "Reviewed", "time": "Mar 12", "tone": "success"}]), title="Activity"), ratio="2:1"),
                  title=title)
        return scene, "Detail archetype: attributes beside a chronological activity trail."
    if entity or re.search(r"\b(list|table|inbox|directory|catalog|manage|browse|search)\b", low):
        ent = entity or "task"
        scene = N("Page", N("Toolbar", N("Search", name="q", placeholder="Search %ss" % ent, kbd="/"),
                            N("Row", N("Button", label="Filter", icon="filter", variant="ghost"), N("Button", label="New %s" % ent, icon="plus", variant="primary"))),
                  N("Card", _table_for(ent, 7, low), padding="none"), title=title, subtitle="%d records" % 7)
        return scene, "Collection archetype: search and primary action above a sortable table."
    scene = N("Page", N("Hero", N("Row", N("Button", label="Get started", variant="primary"), N("Button", label="Learn more", variant="ghost")),
                        title=title, subtitle=T.clip(intent or "", 140), tone="aurora"),
              N("Grid", *[N("Card", N("Text", content=body, tone="muted"), title=head) for head, body in
                          (("Clear", "One idea per section keeps the page scannable."), ("Fast", "Content first; decoration never blocks reading."),
                           ("Yours", "Refine this draft by describing what should change."))], columns=3), title=title)
    return scene, "General archetype: a headline block followed by three supporting points."


def data_view(data: Any, title: str = "") -> Tuple[Node, str]:
    """Choose a presentation for arbitrary JSON based on its shape."""
    if isinstance(data, list) and data and all(isinstance(r, dict) for r in data):
        cols = D.column_types(data)
        table = N("Table", columns=[{"key": c["key"], "label": c["label"], "format": c["format"], "align": c["align"]} for c in cols],
                  rows=data, caption=title or None, pageSize=10 if len(data) > 10 else None)
        choice = D.choose_chart(data)
        kids: List[Node] = []
        stats = D.kpis(data, 4)
        if stats and len(data) >= 3:
            kids.append(N("Grid", *[N("Stat", label=s["label"].capitalize(), value=s["value"], delta=s["delta"], trend=s["trend"], spark=s["spark"]) for s in stats],
                          columns=min(4, len(stats))))
        if choice["kind"] != "table" and 2 <= len(data) <= 60:
            kids.append(N("Card", N("Chart", kind=choice["kind"], data=data, x=choice["x"], y=choice["y"] if len(choice["y"]) > 1 else choice["y"][0], height=240),
                          title=title or "Overview"))
        kids.append(N("Card", table, padding="none"))
        return N("Stack", *kids, gap="lg"), "A list of records: figures, a %s and the full table. %s" % (choice["kind"], choice["rationale"])
    if isinstance(data, list):
        return N("List", items=[{"title": str(v)} for v in data[:200]]), "A flat list of values reads best as rows."
    if isinstance(data, dict):
        scalars = {k: v for k, v in data.items() if not isinstance(v, (dict, list))}
        nested = {k: v for k, v in data.items() if isinstance(v, (dict, list))}
        kids = []
        numbers = {k: v for k, v in scalars.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if numbers and len(numbers) == len(scalars) and len(numbers) <= 6:
            kids.append(N("Grid", *[N("Stat", label=label_of(k), value=D.fmt(float(v))) for k, v in numbers.items()], columns=min(4, len(numbers))))
        elif scalars:
            kids.append(N("Card", N("KeyValue", items=[{"key": label_of(k), "value": "Yes" if v is True else ("No" if v is False else str(v))} for k, v in scalars.items()],
                                    columns=2 if len(scalars) > 4 else 1), title=title or None))
        for key, value in list(nested.items())[:8]:
            child, _ = data_view(value, label_of(key))
            kids.append(N("Section", child, title=label_of(key)))
        return N("Stack", *kids, gap="lg"), "An object: scalar attributes as pairs, nested collections as their own sections."
    return N("Text", content=str(data)), "A single value."


def schema_form(schema: Dict[str, Any], name: str = "form", values: Optional[Dict[str, Any]] = None,
                submit_label: str = "Save") -> Tuple[Node, str]:
    props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = set(schema.get("required") or [])
    groups: Dict[str, List[Node]] = {}
    for key, sub in props.items():
        sub = sub if isinstance(sub, dict) else {}
        field = field_for(key, sub, key in required)
        if values and key in values:
            field["props"]["checked" if field["type"] in ("Checkbox", "Toggle") else "value"] = values[key]
        group = sub.get("x-group") or (key.split("_")[0] if "_" in key and sum(1 for k in props if k.startswith(key.split("_")[0] + "_")) > 1 else "")
        groups.setdefault(str(group), []).append(field)
    body: List[Node] = []
    for group, fields in groups.items():
        block = N("Grid", *fields, columns=2) if len(fields) > 3 else N("Stack", *fields, gap="md")
        body.append(N("Section", block, title=label_of(group), divider=bool(body)) if group and len(groups) > 1 else block)
    body.append(N("Row", N("Button", label=submit_label, variant="primary"), justify="end"))
    title = schema.get("title")
    form = N("Form", *body, name=name)
    return (N("Card", form, title=title, subtitle=schema.get("description")) if title else form), \
        "%d fields in %d group%s; input types follow each property's type, format and name." % (
            len(props), len(groups), "" if len(groups) == 1 else "s")


def wireframe(text: str) -> Tuple[Node, str]:
    """Parse a plain-text sketch.

    ``# Title`` heading · ``[ Label ]`` button · ``[____] Label`` or ``Label: ____`` input ·
    ``[x] Label`` checkbox · ``( ) A ( ) B`` radio · ``---`` divider · ``| a | b |`` table ·
    ``* item`` list · ``> note`` callout · ``<Tab A | Tab B>`` tabs · anything else is text.
    """
    kids: List[Node] = []
    title = ""
    table_rows: List[List[str]] = []
    list_items: List[str] = []

    def flush() -> None:
        nonlocal table_rows, list_items
        if table_rows:
            header, body = table_rows[0], table_rows[1:]
            keys = [re.sub(r"\W+", "_", h.lower()).strip("_") or "col%d" % i for i, h in enumerate(header)]
            kids.append(N("Table", columns=[{"key": k, "label": h} for k, h in zip(keys, header)],
                          rows=[dict(zip(keys, r)) for r in body]))
            table_rows = []
        if list_items:
            kids.append(N("List", items=[{"title": i} for i in list_items]))
            list_items = []

    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if re.fullmatch(r"\|.*\|", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                table_rows.append(cells)
            continue
        m = re.match(r"^[*\-•]\s+(.+)$", line)
        if m and not re.fullmatch(r"-{3,}", line):
            list_items.append(m.group(1))
            continue
        flush()
        if re.fullmatch(r"[-=_]{3,}", line):
            kids.append(N("Divider"))
        elif line.startswith("#"):
            level = min(4, len(line) - len(line.lstrip("#")))
            heading = line.lstrip("#").strip()
            if level == 1 and not title:
                title = heading
            else:
                kids.append(N("Heading", text=heading, level=level))
        elif line.startswith(">"):
            kids.append(N("Callout", title=line[1:].strip(), tone="info"))
        elif re.fullmatch(r"<.+\|.+>", line):
            kids.append(N("Tabs", *[N("Tab", label=t.strip()) for t in line.strip("<>").split("|")]))
        elif re.match(r"^\[[xX ]\]\s+\S", line):
            kids.append(N("Checkbox", name=re.sub(r"\W+", "_", line[3:].strip().lower()).strip("_"), label=line[3:].strip(), checked=line[1] in "xX"))
        elif re.match(r"^\(\s?[ *o]?\s?\)", line):
            options = [o.strip() for o in re.split(r"\(\s?[ *o]?\s?\)", line) if o.strip()]
            kids.append(N("RadioGroup", name="choice_%d" % len(kids), options=options, layout="horizontal"))
        elif re.match(r"^\[_{2,}\]\s*(.*)$", line) or re.match(r"^(.+?):\s*_{2,}\s*$", line):
            m2 = re.match(r"^\[_{2,}\]\s*(.*)$", line) or re.match(r"^(.+?):\s*_{2,}\s*$", line)
            kids.append(field_for(m2.group(1).strip() or "field"))  # type: ignore[union-attr]
        elif re.fullmatch(r"(\[[^\]]+\]\s*)+", line):
            buttons = re.findall(r"\[\s*([^\]]+?)\s*\]", line)
            nodes = [N("Button", label=b.strip("* "), variant="primary" if (b.startswith("*") or i == len(buttons) - 1) else "secondary")
                     for i, b in enumerate(buttons)]
            kids.append(nodes[0] if len(nodes) == 1 else N("Row", *nodes))
        else:
            kids.append(N("Text", content=line))
    flush()
    return N("Page", *kids, title=title or "Sketch"), "Converted %d sketch elements into components." % len(kids)


class _HtmlImporter(HTMLParser):
    BLOCK = {"div", "section", "article", "main", "header", "footer", "aside", "body", "html", "fieldset", "span", "label"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: Node = {"type": "Stack", "props": {}, "children": []}
        self.stack: List[Tuple[str, Node]] = [("root", self.root)]
        self.text: List[str] = []
        self.skip = 0
        self.pending_label = ""
        self.title = ""
        self.table: Optional[Dict[str, Any]] = None
        self.cell: Optional[List[str]] = None

    def _flush(self) -> None:
        content = re.sub(r"\s+", " ", "".join(self.text)).strip()
        self.text = []
        if content:
            self.stack[-1][1].setdefault("children", []).append(N("Text", content=content))

    def _host(self) -> Node:
        """Nearest open element that can hold children (labels only carry text)."""
        for _, node in reversed(self.stack):
            if node.get("type") != "_Label":
                return node
        return self.root

    def _add(self, node: Node) -> None:
        self._host().setdefault("children", []).append(node)
        if self.stack[-1][1].get("type") == "_Label":
            self.stack[-1][1]["_control"] = node

    def _label_before_control(self) -> None:
        """``<label>Name <input></label>``: the text typed so far labels the control that follows."""
        if self.stack[-1][1].get("type") != "_Label":
            return
        text = re.sub(r"\s+", " ", "".join(self.text)).strip()
        self.text = []
        if text:
            self.pending_label = text

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag in ("script", "style", "noscript", "svg", "head"):
            self.skip += 1
            return
        if self.skip or (self.table is not None and tag not in ("tr", "td", "th", "thead", "tbody")):
            return
        if tag in ("td", "th"):
            self.cell = []
            return
        if tag in ("tr", "thead", "tbody"):
            if tag == "tr" and self.table is not None:
                self.table["row"] = []
            return
        if tag in ("strong", "b", "em", "i", "small", "code", "u", "br"):
            if tag == "br":
                self.text.append(" ")
            return
        if tag in ("input", "select", "textarea"):
            self._label_before_control()
        self._flush()
        if tag == "table":
            self.table = {"rows": [], "row": []}
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "button", "li", "option", "title", "label", "legend", "textarea"):
            node = {"h": "Heading", "p": "Text", "a": "Link", "b": "Button", "l": "Text", "o": "_Option", "t": "_Title"}[tag[0]]
            if tag in ("label", "legend"):
                node = "_Label"
            if tag == "textarea":
                node = "TextArea"
                if self.stack[-1][1].get("type") == "_Label":
                    self.stack[-1][1]["_control"] = {"props": {"label": self.pending_label or "-"}}
            self.stack.append((tag, {"type": node, "props": {"_attrs": a, "_level": int(tag[1]) if tag[0] == "h" else 0}, "children": []}))
        elif tag == "input":
            kind = a.get("type", "text").lower()
            name = a.get("name") or a.get("id") or re.sub(r"\W+", "_", (self.pending_label or a.get("placeholder", "field")).lower()).strip("_")
            label = self.pending_label or None
            self.pending_label = ""
            if kind in ("checkbox", "radio"):
                wrapped = self.stack[-1][1].get("type") == "_Label"
                self._add(N("Checkbox", name=name, label=label or ("" if wrapped else label_of(name)), checked="checked" in a))
            elif kind in ("submit", "button"):
                self._add(N("Button", label=a.get("value") or "Submit", variant="primary" if kind == "submit" else "secondary"))
            elif kind != "hidden":
                mapped = kind if kind in ("email", "password", "url", "tel", "number", "search", "date", "time") else "text"
                self._add(N("Input", name=name, label=label, kind=mapped, placeholder=a.get("placeholder") or None,
                            value=a.get("value") or None, required=True if "required" in a else None))
        elif tag == "select":
            label = self.pending_label or None
            self.pending_label = ""
            select = N("Select", name=a.get("name") or "select", label=label, options=[])
            if self.stack[-1][1].get("type") == "_Label":
                self.stack[-1][1]["_control"] = select
            self.stack.append((tag, select))
        elif tag == "img":
            self._add(N("Image", src=a.get("src", ""), alt=a.get("alt") or None))
        elif tag == "hr":
            self._add(N("Divider"))
        elif tag in ("ul", "ol"):
            self.stack.append((tag, N("List", items=[])))
        elif tag == "form":
            self.stack.append((tag, {"type": "Form", "props": {"name": a.get("name") or a.get("id") or "form"}, "children": []}))
        elif tag == "nav":
            self.stack.append((tag, {"type": "Row", "props": {"gap": "md"}, "children": []}))
        elif tag in self.BLOCK:
            self.stack.append((tag, {"type": "Stack", "props": {}, "children": []}))

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript", "svg", "head"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if self.table is not None:
            if tag in ("td", "th") and self.cell is not None:
                self.table["row"].append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
                self.cell = None
            elif tag == "tr" and self.table["row"]:
                self.table["rows"].append(self.table["row"])
                self.table["row"] = []
            elif tag == "table":
                rows = self.table["rows"]
                self.table = None
                if rows:
                    keys = [re.sub(r"\W+", "_", h.lower()).strip("_") or "col%d" % i for i, h in enumerate(rows[0])]
                    self._add(N("Table", columns=[{"key": k, "label": h} for k, h in zip(keys, rows[0])],
                                rows=[dict(zip(keys, r)) for r in rows[1:]]))
            return
        if tag in ("strong", "b", "em", "i", "small", "code", "u", "br", "input", "img", "hr"):
            return
        if not any(t == tag for t, _ in self.stack[1:]):
            return
        while self.stack[-1][0] != tag:
            self._close()
        self._close()

    def _close(self) -> None:
        tag, node = self.stack.pop()
        content = re.sub(r"\s+", " ", "".join(self.text)).strip()
        self.text = []
        parent = self._host()
        meta = node.get("props", {})
        attrs = meta.pop("_attrs", {}) if isinstance(meta, dict) else {}
        level = meta.pop("_level", 0) if isinstance(meta, dict) else 0
        kind = node["type"]
        if kind == "_Title":
            self.title = content
            return
        if kind == "_Label":
            control = node.get("_control")
            if control is None:
                self.pending_label = content
            elif not control["props"].get("label"):
                control["props"]["label"] = content or label_of(str(control["props"].get("name") or "field"))
            return
        if kind == "_Option":
            if parent.get("type") == "Select" and content:
                parent["props"]["options"].append(content)
            return
        if tag == "li":
            if parent.get("type") == "List":
                parent["props"]["items"].append({"title": content or C.primary_text(node["children"][0]) if (content or node.get("children")) else ""})
            return
        if kind == "Heading" and content:
            parent.setdefault("children", []).append(N("Heading", text=content, level=min(4, max(1, level))))
        elif kind == "Text" and content:
            parent.setdefault("children", []).append(N("Text", content=content))
        elif kind == "Link" and content:
            parent.setdefault("children", []).append(N("Link", label=content, href=attrs.get("href") or "#"))
        elif kind == "Button" and content:
            parent.setdefault("children", []).append(N("Button", label=content, variant="primary" if attrs.get("type") == "submit" or "primary" in attrs.get("class", "") else "secondary"))
        elif kind == "TextArea":
            label = self.pending_label or None
            self.pending_label = ""
            parent.setdefault("children", []).append(N("TextArea", name=attrs.get("name") or "text", label=label, value=content or None))
        elif kind in ("Select", "List", "Form", "Row", "Stack"):
            if content:
                node.setdefault("children", []).append(N("Text", content=content))
            children = node.get("children") or []
            if kind == "Stack" and len(children) == 1:
                parent.setdefault("children", []).append(children[0])
            elif kind == "Stack" and not children:
                return
            elif kind in ("Select", "List"):
                node.pop("children", None)
                parent.setdefault("children", []).append(node)
            else:
                parent.setdefault("children", []).append(node)

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif self.table is None:
            self.text.append(data)

    def finish(self) -> Node:
        self._flush()
        while len(self.stack) > 1:
            self._close()
        return self.root


def html_import(html: str) -> Tuple[Node, str]:
    """Convert an HTML fragment into a scene (semantic tags only; styling is discarded)."""
    parser = _HtmlImporter()
    parser.feed(html or "")
    parser.close()
    root = parser.finish()
    kids = root.get("children") or []
    title = parser.title
    if not title:
        def lift(parent: Node) -> str:
            children = parent.get("children") or []
            for index, child in enumerate(children):
                if child.get("type") == "Heading" and int(child["props"].get("level") or 2) <= 2:
                    return str(children.pop(index)["props"].get("text") or "")
                if child.get("type") in ("Stack", "Form"):
                    found = lift(child)
                    if found:
                        return found
            return ""
        title = lift(root)
    scene = N("Page", *kids, title=title or "Imported page")
    count = sum(1 for _ in C.walk(scene))
    return scene, "Mapped semantic HTML to %d components; presentation rules were dropped in favour of design tokens." % count


def empty_state(context: str, actions: Optional[List[str]] = None) -> Node:
    low = (context or "").lower()
    listed = re.search(r"\b(?:list|table|board|grid|collection|feed|queue|set) of ([a-z][a-z ]*?)(?:\s+(?:for|in|by|from|on|at|with)\b|[,.]|$)", low)
    noun = listed.group(1).strip() if listed else next((w for w in T.keywords(context, 3)), "items")
    if re.search(r"\b(search|filter|results?|match)\b", low):
        title, desc, icon, verbs = "No matches", "Try fewer filters or a broader search term.", "search", ["Clear filters"]
    elif re.search(r"\b(error|failed|offline|unavailable)\b", low):
        title, desc, icon, verbs = "We couldn't load this", "Check your connection and try again.", "alert", ["Retry"]
    elif re.search(r"\b(inbox|notification|done|complete|caught up)\b", low):
        title, desc, icon, verbs = "You're all caught up", "New %s will appear here." % noun, "check", []
    else:
        title = "No %s yet" % noun
        desc = "Create your first one, or import existing %s to get started." % noun
        icon, verbs = G.match_icon(context, 1)[0]["value"], ["Create %s" % noun.rstrip("s"), "Import"]
    verbs = [T.sentence_case(re.sub(r"[_\-]+", " ", str(a))) for a in actions] if actions else verbs
    buttons = [N("Button", label=v, variant="primary" if i == 0 else "ghost") for i, v in enumerate(verbs[:2])]
    return N("EmptyState", *( [N("Row", *buttons, justify="center")] if buttons else []), title=title, description=desc, icon=icon)


_SKELETON = {"Table": ("block", 220), "Chart": ("block", 240), "Image": ("block", 180), "Stat": ("card", 0), "Card": ("card", 0),
             "Avatar": ("circle", 0), "List": ("text", 0), "Board": ("block", 260), "Timeline": ("text", 0)}


def skeleton_for(scene: Optional[Node] = None, description: str = "") -> Node:
    """Predict placeholders that match the shape of the content about to load."""
    if scene is None:
        scene, _ = compose_intent(description or "list")

    def convert(node: Node, depth: int) -> Optional[Node]:
        kind = node.get("type")
        kids = [k for k in (convert(c, depth + 1) for c in node.get("children") or []) if k]
        if kind in _SKELETON and not (kind == "Card" and kids):
            shape, height = _SKELETON[kind]
            return N("Skeleton", shape=shape, height=height or None, lines=4 if kind in ("List", "Timeline") else None)
        if kind in C.CONTAINERS:
            props = {k: v for k, v in (node.get("props") or {}).items() if k in ("columns", "gap", "ratio", "width", "justify", "align")}
            if kind in ("Page", "Section", "Hero", "Card"):
                kids.insert(0, N("Skeleton", shape="text", lines=1))
            return N("Stack" if kind in ("Page", "Form", "Section", "Hero", "Tab", "Tabs", "Shell") else kind, *kids, **props)
        if kind in ("Heading", "Text", "Markdown", "KeyValue", "Callout"):
            return N("Skeleton", shape="text", lines=1 if kind == "Heading" else 2)
        if kind in ("Input", "Select", "TextArea", "Button", "Search"):
            return N("Skeleton", shape="block", height=38)
        return None

    return convert(scene, 0) or N("Skeleton", shape="card")


def linearize(scene: Node) -> Tuple[Node, str]:
    """Flatten a dense screen into a one-thing-at-a-time sequence."""
    groups: List[Tuple[str, List[Node]]] = []
    loose: List[Node] = []
    for node, _, parent in C.walk(scene):
        if node.get("type") in ("Card", "Section", "Tab", "Form") and any(c.get("type") not in ("Card", "Section", "Tab", "Form", "Grid", "Split", "Stack", "Row") for c in node.get("children") or []):
            groups.append((C.primary_text(node) or "Step %d" % (len(groups) + 1), [c for c in node.get("children") or []]))
        elif parent is scene and node.get("type") not in C.CONTAINERS:
            loose.append(node)
    if loose:
        groups.insert(0, ("Overview", loose))
    if not groups:
        groups = [("Everything", list(scene.get("children") or []))]
    steps = [{"title": title, "detail": "%d item%s" % (len(nodes), "" if len(nodes) == 1 else "s")} for title, nodes in groups]
    panels = [N("Section", *nodes, title="%d. %s" % (i + 1, title), divider=i > 0) for i, (title, nodes) in enumerate(groups)]
    return N("Page", N("Steps", items=steps, current=0, orientation="vertical"), *panels, title=C.primary_text(scene) or "Step by step", width="narrow"), \
        "Reorganised %d regions into a single reading order with explicit progress." % len(groups)


def goal_wizard(goal: str) -> Tuple[Node, str]:
    fields = _intent_fields(goal)
    low = goal.lower()
    if re.search(r"\b(invite|team|member)", low):
        steps = [("Who", ["email", "role"]), ("Access", ["projects", "notifications"]), ("Confirm", [])]
    elif re.search(r"\b(import|migrate|upload)", low):
        steps = [("Source", ["file"]), ("Map fields", ["name", "email"]), ("Review", [])]
    elif re.search(r"\b(campaign|launch|publish|announce)", low):
        steps = [("Audience", ["segment", "language"]), ("Message", ["subject", "message"]), ("Schedule", ["date"]), ("Review", [])]
    elif fields:
        third = max(1, (len(fields) + 1) // 2)
        steps = [("Basics", fields[:third]), ("Details", fields[third:]), ("Review", [])]
    else:
        steps = [("Goal", ["name", "description"]), ("Details", ["owner", "due_date", "priority"]), ("Review", [])]
    first_title, first_fields = steps[0]
    scene = N("Page", N("Steps", items=[{"title": t} for t, _ in steps], current=0),
              N("Card", N("Form", *[field_for(f) for f in first_fields],
                          N("Row", N("Button", label="Back", variant="ghost", disabled=True),
                            N("Button", label="Continue", variant="primary", icon="arrow-right"), justify="between"), name="wizard"),
                title=first_title, subtitle="Step 1 of %d" % len(steps)),
              title=_intent_title(goal), width="narrow")
    return scene, "Split the goal into %d steps so each screen asks one kind of question." % len(steps)


def tour(scene: Node, limit: int = 6) -> List[Dict[str, str]]:
    """Pick the elements worth introducing and explain each in one sentence."""
    steps: List[Dict[str, str]] = []
    templates = {"Search": "Find anything here. Press the shortcut to jump straight in.",
                 "IntentBar": "Describe what you want in plain language and the right action runs.",
                 "Copilot": "Ask questions about what is on screen; answers stay grounded in this page.",
                 "Table": "Every record lives here. Click a header to sort, or filter in plain language.",
                 "Chart": "The trend at a glance. Hover any point for the exact value.",
                 "Form": "Fill this in to continue. Fields validate as you type.",
                 "Tabs": "Switch between views of the same data without losing your place.",
                 "Stat": "Headline figures with the change since the previous period.",
                 "Insight": "Generated findings, each with a confidence level you can inspect."}
    for node, _, _ in C.walk(scene):
        kind = node.get("type")
        text = C.primary_text(node)
        if kind == "Button" and (node.get("props") or {}).get("variant") == "primary":
            steps.append({"target": node["id"], "title": text or "Primary action", "body": "This is the main action on this screen."})
        elif kind in templates and not any(s["title"] == (text or kind) for s in steps):
            steps.append({"target": node["id"], "title": text or kind, "body": templates[kind]})
        if len(steps) >= limit:
            break
    if not steps:
        steps.append({"target": scene.get("id", ""), "title": C.primary_text(scene) or "Welcome", "body": "Start here: this screen shows everything you need."})
    return steps


def decompose(goal: str) -> Tuple[Node, str]:
    parts = [p.strip() for p in re.split(r"[.;\n]|,\s*(?:and\s+)?|\s+and then\s+|\s+then\s+", goal or "") if len(p.strip()) > 3]
    verbs = ["Define scope for", "Draft", "Review", "Build", "Test", "Ship"]
    key = " ".join(T.keywords(goal, 3)) or "the work"
    tasks = [T.sentence_case(p) for p in parts[:6]] if len(parts) >= 3 else ["%s %s" % (v, key) for v in verbs]
    third = max(1, (len(tasks) + 2) // 3)
    cols = [{"title": name, "cards": [{"title": t, "tags": [tag]} for t in tasks[i * third:(i + 1) * third]]}
            for i, (name, tag) in enumerate((("Now", "start"), ("Next", "queued"), ("Later", "planned")))]
    return N("Board", columns=cols), "Broke the goal into %d tasks ordered by dependency." % len(tasks)


def faq(text: str, limit: int = 5) -> Node:
    items = []
    for sentence in T.sentences(text)[:limit * 2]:
        keys = T.keywords(sentence, 3)
        if len(keys) < 2 or len(items) >= limit:
            continue
        question = T.question_from(sentence) or "What should I know about %s?" % " and ".join(keys[:2])
        items.append(N("Disclosure", N("Text", content=sentence), title=question, open=not items))
    return N("Stack", *items, gap="sm") if items else N("EmptyState", title="Nothing to answer yet", description="Add content to generate questions.")


def recap(text: str) -> Node:
    sents = T.sentences(text)
    decisions = [s for s in sents if re.search(r"\b(decided|agreed|approved|will go with|chose|confirmed|settled)\b", s, re.IGNORECASE)]
    actions = [s for s in sents if re.search(r"\b(will|to do|action|by (monday|tuesday|wednesday|thursday|friday|next|eod|tomorrow)|needs? to|should|owner|follow up)\b", s, re.IGNORECASE) and s not in decisions]
    return N("Card", N("Text", content=T.summarize(text, 2)),
             N("Section", N("List", items=[{"title": T.clip(d, 120), "icon": "check"} for d in decisions[:4]] or [{"title": "No explicit decisions recorded", "icon": "info"}], divided=False), title="Decisions"),
             N("Section", N("List", items=[{"title": T.clip(a, 120), "icon": "arrow-right"} for a in actions[:5]] or [{"title": "No follow-ups identified", "icon": "info"}], divided=False), title="Next steps"),
             title=T.title_of(text) or "Recap", eyebrow="Recap")


def story(rows: List[Dict[str, Any]], title: str = "") -> Tuple[Node, str]:
    choice = D.choose_chart(rows)
    note = D.insights(rows)
    x = choice["x"]
    measures = choice["y"] or []
    sections: List[Node] = [N("Hero", title=title or note["title"], subtitle=note["body"], eyebrow="Data story")]
    for i, measure in enumerate(measures[:3]):
        per = D.insights(rows, x, measure)
        sections.append(N("Section", N("Split", N("Chart", kind=choice["kind"] if choice["kind"] != "table" else "bar", data=rows, x=x, y=measure, height=220),
                                           N("Insight", title=per["title"], body=per["body"], bullets=per["bullets"], confidence=per["confidence"], source="reflex"), ratio="3:2"),
                          title="%d. %s" % (i + 1, label_of(measure)), divider=i > 0))
    return N("Stack", *sections, gap="lg"), "A headline followed by one annotated view per measure."


def remix(scene: Node, count: int = 3) -> List[Dict[str, Any]]:
    """Alternative arrangements of the same content."""
    kids = list(scene.get("children") or [])
    props = dict(scene.get("props") or {})
    base_type = scene.get("type", "Page") if scene.get("type") in C.CONTAINERS else "Page"
    variants = [{"name": "Focused column", "rationale": "A single reading order; best for first-time and mobile use.",
                 "scene": N(base_type, N("Stack", *kids, gap="lg"), **{**props, "width": "narrow"} if base_type == "Page" else props)}]
    if len(kids) >= 2:
        variants.append({"name": "Primary and rail", "rationale": "The first block leads; the rest becomes a supporting rail.",
                         "scene": N(base_type, N("Split", kids[0], N("Stack", *kids[1:], gap="md"), ratio="2:1"), **props)})
        variants.append({"name": "Tabbed sections", "rationale": "Each block gets full width; switching costs one click.",
                         "scene": N(base_type, N("Tabs", *[N("Tab", k, label=C.primary_text(k) or "View %d" % (i + 1)) for i, k in enumerate(kids)]), **props)})
        variants.append({"name": "Dense grid", "rationale": "Everything visible at once for monitoring use.",
                         "scene": N(base_type, N("Grid", *kids, columns=2 if len(kids) < 5 else 3), **{**props, "width": "wide"} if base_type == "Page" else props)})
    return variants[:max(1, count)]


def refine(scene: Node, instruction: str) -> Tuple[Node, str]:
    """Apply a plain-language edit to an existing scene."""
    import copy
    out = copy.deepcopy(scene)
    low = (instruction or "").lower()
    notes: List[str] = []
    if re.search(r"\b(compact|dense|tighter|smaller)\b", low):
        for node, _, _ in C.walk(out):
            if node["type"] in ("Table", "List"):
                node["props"]["dense"] = True
            if node["type"] in ("Stack", "Grid", "Row"):
                node["props"]["gap"] = "sm"
        notes.append("tightened spacing")
    if re.search(r"\b(spacious|roomy|airy|more space)\b", low):
        for node, _, _ in C.walk(out):
            if node["type"] in ("Stack", "Grid"):
                node["props"]["gap"] = "xl"
        notes.append("opened up spacing")
    m = re.search(r"\b(?:remove|delete|drop|hide)\s+(?:the\s+)?(.+?)(?:\s+(?:section|card|field|button|table|chart))?$", low)
    if m:
        target = m.group(1).strip()
        removed = [0]

        def prune(node: Node) -> None:
            keep = []
            for child in node.get("children") or []:
                text = (C.primary_text(child) + " " + child["type"] + " " + str((child.get("props") or {}).get("name", ""))).lower()
                if target and target in text:
                    removed[0] += 1
                else:
                    prune(child)
                    keep.append(child)
            if "children" in node:
                node["children"] = keep

        prune(out)
        notes.append("removed %d element%s matching “%s”" % (removed[0], "" if removed[0] == 1 else "s", target))
    m = re.search(r"\badd\s+(?:an?\s+)?(.+?)(?:\s+(?:at the|to the)\s+(top|bottom))?$", low)
    if m:
        what, where = m.group(1), m.group(2) or "bottom"
        if "search" in what:
            new = N("Search", name="q", placeholder="Search")
        elif "button" in what:
            new = N("Button", label=T.sentence_case(re.sub(r"\bbutton\b", "", what).strip() or "Continue"), variant="primary")
        elif "chart" in what or "graph" in what:
            new = N("Chart", kind="bar", data=D.fixtures(["month", "revenue"], 6, what), x="month", y="revenue")
        elif "table" in what or "list" in what:
            new = _table_for(_entity(what) or "task", 4, what)
        elif "note" in what or "callout" in what or "warning" in what:
            new = N("Callout", title=T.sentence_case(what), tone="info")
        else:
            new = field_for(re.sub(r"\b(field|input)\b", "", what).strip() or "field")
        form = next((n for n, _, _ in C.walk(out) if n["type"] == "Form"), None) if new["type"] in ("Input", "TextArea", "Select", "Checkbox", "Toggle") else None
        host = form or out
        kids = host.setdefault("children", [])
        position = 0 if where == "top" else (max(0, len(kids) - 1) if form else len(kids))
        kids.insert(position, new)
        notes.append("added %s" % new["type"])
    m = re.search(r"\b(two|three|four|2|3|4)\s+columns?\b", low)
    if m:
        n = {"two": 2, "three": 3, "four": 4}.get(m.group(1), None) or int(m.group(1))
        grids = [node for node, _, _ in C.walk(out) if node["type"] == "Grid"]
        if grids:
            for g in grids:
                g["props"]["columns"] = n
        else:
            out["children"] = [N("Grid", *(out.get("children") or []), columns=n)]
        notes.append("arranged in %d columns" % n)
    if re.search(r"\btabs?\b", low) and not re.search(r"\b(remove|delete)\b", low) and len(out.get("children") or []) > 1:
        out["children"] = [N("Tabs", *[N("Tab", k, label=C.primary_text(k) or "View %d" % (i + 1)) for i, k in enumerate(out["children"])])]
        notes.append("grouped sections into tabs")
    m = re.search(r"\b(?:rename|retitle|title)\b.*?\bto\s+[\"“']?(.+?)[\"”']?$", instruction or "", re.IGNORECASE)
    if m:
        key = "title" if "title" in C.SPEC[out["type"]]["props"] else (C.SPEC[out["type"]]["primary"] or "title")
        out.setdefault("props", {})[key] = m.group(1).strip()
        notes.append("retitled")
    return out, ("Applied: " + "; ".join(notes) + ".") if notes else "No recognised edit; the scene is unchanged."


def continuation(scene: Node) -> Tuple[Node, str]:
    """Predict the screen a user is most likely to need next."""
    types = {n["type"] for n, _, _ in C.walk(scene)}
    title = C.primary_text(scene)
    names = {str((n.get("props") or {}).get("name", "")) for n, _, _ in C.walk(scene)}
    if "password" in names:
        nxt, why = compose_intent("overview dashboard")
        return nxt, "After signing in, people land on an overview."
    if "Form" in types or "SmartForm" in types:
        nxt = N("Page", N("Card", N("EmptyState", N("Row", N("Button", label="View record", variant="primary"), N("Button", label="Create another", variant="ghost"), justify="center"),
                                    title="Saved", description="Your changes to “%s” are stored." % (title or "the form"), icon="check")), title="Confirmation", width="narrow")
        return nxt, "A submitted form is followed by confirmation and the two most common next steps."
    if "Table" in types or "List" in types:
        ent = _entity(title.lower()) or "customer"
        nxt, _ = compose_intent("%s detail" % ent)
        return nxt, "From a collection, the next step is almost always one record's detail."
    nxt, _ = compose_intent("list of tasks")
    return nxt, "With no stronger signal, a task list is the safest continuation."


def priorities(scene: Node) -> List[Dict[str, Any]]:
    """Rank regions by importance for progressive disclosure and semantic reflow."""
    weights = {"Stat": 9, "Form": 9, "SmartForm": 9, "Table": 8, "Chart": 7, "Insight": 7, "Callout": 8, "Banner": 8, "Approval": 10,
               "Copilot": 5, "IntentBar": 6, "List": 6, "Timeline": 4, "KeyValue": 6, "Board": 6, "Thread": 5, "Image": 3,
               "Hero": 7, "Card": 5, "Section": 5, "Tabs": 6, "Text": 3, "Markdown": 3, "Disclosure": 2, "Tree": 4, "Steps": 7}
    out = []
    top = scene.get("children") or []
    for index, node in enumerate(top):
        score = weights.get(node["type"], 4)
        score += max((weights.get(n["type"], 0) for n, _, _ in C.walk(node)), default=0) * 0.4
        score += 1.5 if any((n.get("props") or {}).get("variant") == "primary" for n, _, _ in C.walk(node)) else 0
        score -= index * 0.35
        out.append({"id": node["id"], "type": node["type"], "text": C.primary_text(node), "score": round(score, 2), "index": index})
    return sorted(out, key=lambda r: -r["score"])
