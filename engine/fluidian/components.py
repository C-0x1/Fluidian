"""Component registry and scene model.

A *scene* is a tree of nodes::

    {"type": "Button", "id": "save", "props": {"label": "Save"},
     "on": {"click": {"action": "save"}}, "ai": [{"capability": "content.microcopy", "options": {}}],
     "children": []}

The registry below is the single source of truth for every component.  The
browser runtime, the fourteen SDK generators, the scene validator and the
reference documentation are all derived from it.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

TONE = "enum:neutral|brand|success|warning|danger|info|ai"
SIZE = "enum:sm|md|lg"
GAP = "enum:none|xs|sm|md|lg|xl"

COMPONENTS: List[Dict[str, Any]] = []
SPEC: Dict[str, Dict[str, Any]] = {}


def _snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def _c(type_: str, cat: str, summary: str, args: str = "", props: Optional[Dict[str, str]] = None,
       container: bool = False, events: str = "", ex: Optional[Dict[str, Any]] = None) -> None:
    arg_list = []
    for part in [a for a in args.split(",") if a.strip()]:
        name, _, kind = part.strip().partition(":")
        arg_list.append({"name": name, "kind": kind or "str"})
    prop_map: Dict[str, Dict[str, Any]] = {}
    for a in arg_list:
        prop_map[a["name"]] = {"kind": a["kind"], "default": None, "doc": "Positional argument.", "arg": True}
    for name, raw in (props or {}).items():
        head, _, doc = raw.partition(";")
        kind, _, default = head.strip().partition("=")
        prop_map[name] = {"kind": kind.strip(), "default": default.strip() or None, "doc": doc.strip(), "arg": False}
    spec = {
        "type": type_, "fn": _snake(type_), "category": cat, "summary": summary, "args": arg_list,
        "props": prop_map, "container": container, "events": [e for e in events.split(",") if e],
        "primary": arg_list[0]["name"] if arg_list and arg_list[0]["kind"] == "str" else None,
        "example": ex or {},
    }
    COMPONENTS.append(spec)
    SPEC[type_] = spec


# --- layout ---------------------------------------------------------------
_c("Page", "layout", "Top-level surface with a title block and a content column.", "title",
   {"subtitle": "str; Supporting line under the title.", "eyebrow": "str; Small label above the title.",
    "width": "enum:narrow|default|wide|full=default; Maximum content width."}, True,
   ex={"args": ["Quarterly review"], "props": {"subtitle": "Revenue, retention and risk"}})
_c("Shell", "layout", "Application frame with brand, navigation rail and a content region.", "brand",
   {"nav": "json; Navigation items: [{label, icon, route, badge, section, active}].",
    "tagline": "str; Line under the brand.", "user": "json; {name, role} shown at the foot of the rail.",
    "footer": "str; Small print at the foot of the rail."}, True, "navigate",
   ex={"args": ["Northwind"], "props": {"nav": [{"label": "Overview", "icon": "home", "route": "/", "active": True},
                                                 {"label": "Orders", "icon": "inbox", "route": "/orders", "badge": "12"}]}})
_c("Stack", "layout", "Vertical flow with consistent spacing.", "",
   {"gap": GAP + "=md; Space between children.", "align": "enum:stretch|start|center|end=stretch; Cross-axis alignment.",
    "justify": "enum:start|center|end|between=start; Main-axis distribution."}, True, ex={"props": {"gap": "sm"}})
_c("Row", "layout", "Horizontal flow that wraps on small viewports.", "",
   {"gap": GAP + "=md; Space between children.", "align": "enum:start|center|end|stretch|baseline=center; Cross-axis alignment.",
    "justify": "enum:start|center|end|between=start; Main-axis distribution.", "wrap": "bool=true; Allow wrapping."},
   True, ex={"props": {"justify": "between"}})
_c("Grid", "layout", "Responsive grid; fixed columns or auto-fit by minimum width.", "",
   {"columns": "num=3; Column count at full width.", "gap": GAP + "=md; Space between cells.",
    "minWidth": "num; Minimum cell width in px; enables auto-fit."}, True, ex={"props": {"columns": 2}})
_c("Split", "layout", "Two-pane layout with a ratio such as 2:1.", "",
   {"ratio": "str=1:1; Width ratio between panes.", "gap": GAP + "=lg; Space between panes."}, True,
   ex={"props": {"ratio": "2:1"}})
_c("Card", "layout", "Grouped surface with optional header.", "",
   {"title": "str; Header title.", "subtitle": "str; Header supporting text.", "eyebrow": "str; Small label above the title.",
    "tone": TONE + "=neutral; Accent colour.", "elevated": "bool; Raise with a shadow.",
    "padding": "enum:none|sm|md|lg=md; Inner spacing."}, True, ex={"props": {"title": "Pipeline", "subtitle": "Updated just now"}})
_c("Section", "layout", "Titled region inside a page.", "title",
   {"description": "str; Supporting text.", "divider": "bool; Draw a rule above the section."}, True,
   ex={"args": ["Billing"], "props": {"description": "Plans, invoices and payment methods"}})
_c("Tabs", "layout", "Tabbed container; children must be Tab nodes.", "",
   {"active": "num=0; Index of the selected tab.", "variant": "enum:line|pill=line; Visual style."}, True, "change",
   ex={"props": {"variant": "pill"}})
_c("Tab", "layout", "A single tab and its panel.", "label",
   {"icon": "str; Icon name.", "badge": "str; Small counter."}, True, ex={"args": ["Activity"], "props": {"badge": "3"}})
_c("Disclosure", "layout", "Collapsible region.", "title",
   {"open": "bool; Expanded initially.", "hint": "str; Text shown beside the title."}, True, "toggle",
   ex={"args": ["Advanced options"], "props": {"open": True}})
_c("Divider", "layout", "Horizontal rule with an optional label.", "", {"label": "str; Centered label."},
   ex={"props": {"label": "or"}})
_c("Spacer", "layout", "Fixed empty space.", "", {"size": "enum:xs|sm|md|lg|xl=md; Amount of space."}, ex={"props": {"size": "lg"}})
_c("Toolbar", "layout", "Compact row for actions and filters.", "",
   {"justify": "enum:start|center|end|between=between; Distribution."}, True, ex={})
_c("Modal", "layout", "Dialog layered over the page.", "title",
   {"open": "bool=true; Visibility.", "size": SIZE + "=md; Dialog width.", "subtitle": "str; Supporting text."}, True, "close",
   ex={"args": ["Invite teammates"], "props": {"open": False}})
_c("Drawer", "layout", "Panel that slides in from a screen edge.", "title",
   {"open": "bool=true; Visibility.", "side": "enum:left|right=right; Edge."}, True, "close",
   ex={"args": ["Filters"], "props": {"open": False}})
_c("Hero", "layout", "Large introductory block.", "title",
   {"eyebrow": "str; Small label above the title.", "subtitle": "str; Supporting paragraph.",
    "align": "enum:start|center=start; Text alignment.", "tone": "enum:plain|brand|aurora|glow|none=plain; Background treatment.",
    "size": "enum:md|lg|xl=md; Type scale.", "highlight": "str; Part of the title to accent with the theme gradient.",
    "badge": "str; Announcement shown in a pill above the title.", "badgeTag": "str; Short tag inside the pill."},
   True, ex={"args": ["Interfaces that think"], "props": {"eyebrow": "Fluidian", "tone": "aurora", "highlight": "think"}})
_c("Breadcrumbs", "layout", "Hierarchy trail.", "", {"items": "json; [{label, route}]."}, False, "navigate",
   ex={"props": {"items": [{"label": "Workspace", "route": "/"}, {"label": "Invoices", "route": "/invoices"}]}})

# --- content --------------------------------------------------------------
_c("Heading", "content", "Section heading, levels 1–4.", "text",
   {"level": "num=2; Heading level 1–4.", "eyebrow": "str; Small label above."}, ex={"args": ["Team activity"], "props": {"level": 3}})
_c("Text", "content", "Body text.", "content",
   {"tone": "enum:default|muted|strong|success|warning|danger|brand=default; Colour role.",
    "size": "enum:xs|sm|md|lg|xl=md; Type size.", "weight": "enum:regular|medium|bold=regular; Font weight.",
    "align": "enum:start|center|end=start; Alignment."}, ex={"args": ["Señor Ω ✓ — 日本語 🚀"], "props": {"tone": "muted"}})
_c("Markdown", "content", "Renders a safe Markdown subset: headings, emphasis, lists, links, code.", "source",
   ex={"args": ["**Bold**, _emphasis_ and `code`.\n\n- one\n- two"]})
_c("Badge", "content", "Compact status label.", "label",
   {"tone": TONE + "=neutral; Colour role.", "variant": "enum:soft|solid|outline=soft; Fill style.",
    "icon": "str; Icon name.", "dot": "bool; Show a status dot."}, ex={"args": ["Live"], "props": {"tone": "success", "dot": True}})
_c("Tag", "content", "Removable keyword chip.", "label",
   {"tone": TONE + "=neutral; Colour role.", "removable": "bool; Show a remove control."}, False, "remove",
   ex={"args": ["design-system"], "props": {"removable": True}})
_c("Icon", "content", "Glyph from the built-in icon set.", "name",
   {"size": "num=18; Pixel size.", "tone": TONE + "=neutral; Colour role."}, ex={"args": ["sparkles"], "props": {"size": 20}})
_c("Image", "content", "Responsive image with aspect ratio control.", "src",
   {"alt": "str; Alternative text.", "ratio": "str; Aspect ratio such as 16:9.", "fit": "enum:cover|contain=cover; Object fit.",
    "caption": "str; Caption under the image.", "rounded": "bool=true; Rounded corners."},
   ex={"args": ["data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'/>"], "props": {"alt": "Empty canvas", "ratio": "16:9"}})
_c("Avatar", "content", "Person or entity marker with initials fallback.", "name",
   {"src": "str; Image URL.", "size": SIZE + "=md; Size.", "status": "enum:online|away|busy|offline; Presence dot."},
   ex={"args": ["Ada Lovelace"], "props": {"status": "online"}})
_c("Code", "content", "Monospaced block with a copy affordance.", "source",
   {"language": "str; Language, used for the label and syntax colouring.", "title": "str; Header title.", "tone": "enum:light|dark=light; Surface.",
    "plain": "bool; Turn syntax colouring off."}, ex={"args": ["fluidian run -- python3 app.py"], "props": {"language": "bash"}})
_c("Kbd", "content", "Keyboard shortcut.", "keys", ex={"args": ["Ctrl+K"]})
_c("Link", "content", "Inline navigation.", "label,href",
   {"external": "bool; Open in a new tab.", "tone": "enum:brand|muted=brand; Colour role."}, False, "navigate",
   ex={"args": ["Read the protocol", "/docs/protocol"]})
_c("Callout", "content", "Highlighted message block.", "title",
   {"body": "str; Message text.", "tone": TONE + "=info; Colour role.", "icon": "str; Icon name."}, True,
   ex={"args": ["Heads up"], "props": {"body": "Exports include archived projects.", "tone": "warning"}})
_c("Banner", "content", "Full-width announcement.", "text",
   {"tone": TONE + "=brand; Colour role.", "icon": "str; Icon name.", "dismissible": "bool; Show a dismiss control."}, False, "dismiss",
   ex={"args": ["Scheduled maintenance on Sunday 02:00 UTC"], "props": {"tone": "info"}})
_c("Stat", "content", "Key figure with delta and sparkline.", "label,value",
   {"delta": "str; Change text such as +12.4%.", "trend": "enum:up|down|flat; Direction of change.",
    "hint": "str; Small supporting text.", "spark": "json; Number series drawn as a sparkline.",
    "tone": TONE + "=neutral; Colour role.", "icon": "str; Icon name."},
   ex={"args": ["Net revenue", "$84,210"], "props": {"delta": "+12.4%", "trend": "up", "spark": [3, 4, 4, 6, 5, 8, 9]}})
_c("Progress", "content", "Linear progress.", "value:num",
   {"max": "num=100; Upper bound.", "label": "str; Label.", "tone": TONE + "=brand; Colour role.",
    "indeterminate": "bool; Animated unknown progress.", "showValue": "bool=true; Print the percentage."},
   ex={"args": [62.5], "props": {"label": "Storage"}})
_c("Skeleton", "content", "Loading placeholder shaped like the content it replaces.", "",
   {"shape": "enum:text|block|circle|card=text; Placeholder shape.", "lines": "num=3; Line count for text.",
    "height": "num; Height in px for block shapes."}, ex={"props": {"shape": "card"}})
_c("EmptyState", "content", "Explains an empty region and offers a way forward.", "title",
   {"description": "str; Supporting text.", "icon": "str=inbox; Icon name."}, True,
   ex={"args": ["No invoices yet"], "props": {"description": "Create one or import from a spreadsheet."}})
_c("Timeline", "content", "Chronological list of events.", "", {"items": "json; [{title, time, detail, tone, icon}]."},
   ex={"props": {"items": [{"title": "Order placed", "time": "09:12"}, {"title": "Packed", "time": "11:40", "tone": "success"}]}})
_c("Steps", "content", "Progress through an ordered sequence.", "",
   {"items": "json; [{title, detail}].", "current": "num=0; Index of the active step.",
    "orientation": "enum:horizontal|vertical=horizontal; Layout."},
   ex={"props": {"items": [{"title": "Account"}, {"title": "Workspace"}, {"title": "Invite"}], "current": 1}})
_c("KeyValue", "content", "Label/value pairs.", "",
   {"items": "json; [{key, value}].", "columns": "num=1; Number of columns."},
   ex={"props": {"items": [{"key": "Plan", "value": "Scale"}, {"key": "Seats", "value": "24"}], "columns": 2}})
_c("List", "content", "Rows with title, detail and trailing metadata.", "",
   {"items": "json; [{title, detail, meta, icon, avatar, badge, tone}].", "dense": "bool; Compact rows.",
    "divided": "bool=true; Draw separators."}, False, "select",
   ex={"props": {"items": [{"title": "Design review", "detail": "Thursday 14:00", "meta": "45 min", "icon": "calendar"}]}})
_c("Tree", "content", "Nested hierarchy.", "", {"items": "json; [{label, icon, children}].", "expanded": "bool=true; Expand all levels."},
   False, "select", ex={"props": {"items": [{"label": "src", "children": [{"label": "app.py"}]}]}})
_c("Blockquote", "content", "Quoted passage.", "text", {"cite": "str; Attribution."}, ex={"args": ["Make it work, then make it obvious."], "props": {"cite": "Team handbook"}})
_c("Thread", "content", "Conversation thread with authors and timestamps.", "",
   {"messages": "json; [{author, time, content, tone}].", "title": "str; Thread title."},
   ex={"props": {"messages": [{"author": "Mira", "time": "10:02", "content": "Can we ship Friday?"}]}})
_c("Board", "content", "Columns of cards for staged work.", "",
   {"columns": "json; [{title, cards: [{title, detail, tags, assignee}]}]."}, False, "select",
   ex={"props": {"columns": [{"title": "Now", "cards": [{"title": "Wire the importer", "tags": ["api"]}]}]}})

# --- input ----------------------------------------------------------------
_c("Button", "input", "Action trigger.", "label",
   {"variant": "enum:primary|secondary|ghost|danger|ai=secondary; Emphasis.", "size": SIZE + "=md; Size.",
    "icon": "str; Leading icon.", "disabled": "bool; Disable interaction.", "loading": "bool; Show a spinner.",
    "block": "bool; Fill the available width.", "href": "str; Navigate instead of emitting an event.",
    "kbd": "str; Shortcut hint."}, False, "click", ex={"args": ["Save changes"], "props": {"variant": "primary", "icon": "check"}})
_c("Input", "input", "Single-line field.", "name",
   {"label": "str; Field label.", "value": "str; Current value.", "placeholder": "str; Placeholder.",
    "kind": "enum:text|email|password|url|tel|number|search|date|time=text; Input type.", "help": "str; Helper text.",
    "error": "str; Validation message.", "required": "bool; Mark as required.", "prefix": "str; Leading adornment.",
    "suffix": "str; Trailing adornment.", "icon": "str; Leading icon.", "disabled": "bool; Disable interaction."},
   False, "change,input,submit", ex={"args": ["email"], "props": {"label": "Work email", "kind": "email", "placeholder": "you@company.com"}})
_c("TextArea", "input", "Multi-line field.", "name",
   {"label": "str; Field label.", "value": "str; Current value.", "placeholder": "str; Placeholder.",
    "rows": "num=4; Visible rows.", "help": "str; Helper text.", "error": "str; Validation message."},
   False, "change,input", ex={"args": ["notes"], "props": {"label": "Notes", "rows": 3}})
_c("Select", "input", "Choose one option from a list.", "name",
   {"label": "str; Field label.", "options": "json; Strings or [{label, value}].", "value": "str; Selected value.",
    "placeholder": "str; Placeholder.", "help": "str; Helper text."}, False, "change",
   ex={"args": ["plan"], "props": {"label": "Plan", "options": ["Starter", "Scale", "Enterprise"], "value": "Scale"}})
_c("Checkbox", "input", "Binary choice.", "name,label", {"checked": "bool; Checked state.", "help": "str; Helper text."},
   False, "change", ex={"args": ["terms", "I accept the terms"], "props": {"checked": True}})
_c("Toggle", "input", "On/off switch.", "name,label", {"checked": "bool; On state.", "help": "str; Helper text."},
   False, "change", ex={"args": ["alerts", "Email alerts"], "props": {"checked": False}})
_c("RadioGroup", "input", "Choose one option; all options visible.", "name",
   {"label": "str; Group label.", "options": "json; Strings or [{label, value, detail}].", "value": "str; Selected value.",
    "layout": "enum:vertical|horizontal|cards=vertical; Arrangement."}, False, "change",
   ex={"args": ["cadence"], "props": {"label": "Billing", "options": ["Monthly", "Yearly"], "value": "Yearly"}})
_c("Slider", "input", "Numeric range.", "name",
   {"label": "str; Field label.", "min": "num=0; Lower bound.", "max": "num=100; Upper bound.", "step": "num=1; Increment.",
    "value": "num; Current value.", "unit": "str; Unit suffix."}, False, "change",
   ex={"args": ["seats"], "props": {"label": "Seats", "min": 1, "max": 50, "value": 12}})
_c("Segmented", "input", "Compact single choice.", "name",
   {"options": "json; Strings or [{label, value}].", "value": "str; Selected value.", "label": "str; Group label."},
   False, "change", ex={"args": ["range"], "props": {"options": ["Day", "Week", "Month"], "value": "Week"}})
_c("TagInput", "input", "Free-form list of tags.", "name",
   {"label": "str; Field label.", "value": "json; Current tags.", "placeholder": "str; Placeholder.",
    "suggestions": "json; Suggested tags."}, False, "change", ex={"args": ["labels"], "props": {"value": ["urgent", "billing"]}})
_c("Rating", "input", "Star rating.", "name", {"value": "num=0; Current rating.", "max": "num=5; Number of stars.", "label": "str; Field label."},
   False, "change", ex={"args": ["score"], "props": {"value": 4}})
_c("FileDrop", "input", "Drop zone for files.", "name",
   {"label": "str; Prompt text.", "accept": "str; Accepted types.", "hint": "str; Helper text."}, False, "drop",
   ex={"args": ["receipt"], "props": {"label": "Drop a receipt", "accept": "image/*"}})
_c("Form", "input", "Groups fields and emits a single submit event with every value.", "name", {}, True, "submit",
   ex={"args": ["profile"]})
_c("Search", "input", "Search field with shortcut hint.", "name",
   {"placeholder": "str=Search; Placeholder.", "value": "str; Current query.", "kbd": "str; Shortcut hint."},
   False, "search,input", ex={"args": ["q"], "props": {"placeholder": "Search orders", "kbd": "/"}})
_c("Mic", "input", "Voice capture that writes a transcript into a target field.", "name",
   {"target": "str; Name of the field that receives the transcript.", "label": "str=Dictate; Accessible label."},
   False, "transcript", ex={"args": ["voice"], "props": {"target": "notes"}})

# --- data -----------------------------------------------------------------
_c("Table", "data", "Sortable, paginated data table.", "",
   {"columns": "json; [{key, label, align, format, width}]; format is text|number|currency|percent|date|badge.",
    "rows": "json; Array of row objects.", "caption": "str; Table caption.", "dense": "bool; Compact rows.",
    "striped": "bool; Zebra rows.", "sortable": "bool=true; Enable header sorting.", "pageSize": "num; Rows per page.",
    "empty": "str=No rows; Message when there are no rows.", "query": "str; Active natural-language filter."},
   False, "rowClick,sort", ex={"props": {"columns": [{"key": "name", "label": "Customer"}, {"key": "mrr", "label": "MRR", "format": "currency", "align": "end"}],
                                         "rows": [{"name": "Acme", "mrr": 1200.5}, {"name": "Globex", "mrr": 860}]}})
_c("Chart", "data", "Bar, line, area, donut, scatter and sparkline charts rendered as SVG.", "kind",
   {"data": "json; Array of row objects.", "x": "str; Key for the category or x value.", "y": "json; Key or keys for values.",
    "title": "str; Chart title.", "height": "num=260; Height in px.", "legend": "bool=true; Show the legend.",
    "annotations": "json; [{x, label, tone}] markers.", "forecast": "json; Projected points drawn as a dashed line.",
    "stacked": "bool; Stack series.", "format": "enum:number|currency|percent|compact=compact; Value format.",
    "smooth": "bool=true; Curve line and area series.", "points": "bool; Draw a marker on each point (on by default for short line series).",
    "baseline": "enum:zero|auto=zero; Start the value axis at zero, or near the lowest value for line and area charts."},
   False, "pointClick", ex={"args": ["bar"], "props": {"data": [{"m": "Jan", "v": 12}, {"m": "Feb", "v": 18}], "x": "m", "y": "v"}})

# --- ai-native ------------------------------------------------------------
_c("IntentBar", "ai", "Natural-language command surface that routes utterances to registered actions.", "",
   {"placeholder": "str=Ask or command…; Placeholder.", "open": "bool; Visible.", "query": "str; Current utterance.",
    "suggestions": "json; [{label, detail, action, icon, kbd, group}].", "hint": "str; Footer hint."},
   False, "command", ex={"props": {"open": False, "suggestions": [{"label": "Create invoice", "action": "create_invoice", "icon": "plus"}]}})
_c("Copilot", "ai", "Scene-aware assistant with streaming replies and suggested prompts.", "",
   {"title": "str=Copilot; Header title.", "messages": "json; [{role, content}].", "suggestions": "json; Suggested prompts.",
    "placeholder": "str=Ask about this screen; Placeholder.", "mode": "enum:inline|dock=inline; Presentation.",
    "thinking": "bool; Show the thinking indicator."}, False, "message",
   ex={"props": {"messages": [{"role": "assistant", "content": "Churn rose 2 points in March."}], "suggestions": ["Why?"]}})
_c("Suggestions", "ai", "Next-best-action chips.", "",
   {"items": "json; [{label, action, value, icon, detail}].", "title": "str; Group label.", "variant": "enum:chips|list=chips; Layout."},
   False, "select", ex={"props": {"items": [{"label": "Send reminder", "action": "remind", "icon": "bell"}]}})
_c("Insight", "ai", "Generated finding with supporting points, confidence and provenance.", "title",
   {"body": "str; Finding text.", "bullets": "json; Supporting points.", "confidence": "num; 0–1 confidence.",
    "tone": TONE + "=ai; Colour role.", "source": "str; Provenance label.", "icon": "str=sparkles; Icon name."},
   True, ex={"args": ["Revenue is accelerating"], "props": {"body": "Up 18% over the trailing quarter.", "confidence": 0.82}})
_c("Provenance", "ai", "Discloses that content is generated: provider, model and confidence.", "",
   {"model": "str; Model identifier.", "provider": "str=reflex; openai, reflex, cache or replay.", "confidence": "num; 0–1 confidence.",
    "generatedAt": "str; Timestamp.", "note": "str; Extra context.", "compact": "bool; Badge-only."},
   ex={"props": {"provider": "openai", "model": "gpt-6-luna", "confidence": 0.9}})
_c("Confidence", "ai", "Visual encoding of model certainty.", "value:num",
   {"label": "str; Label.", "variant": "enum:bar|ring|dots=bar; Visual style."}, ex={"args": [0.75], "props": {"variant": "dots"}})
_c("Generative", "ai", "Region whose content is composed at runtime from an intent.", "intent",
   {"capability": "str=compose.intent; Capability that produces the scene.", "input": "json; Extra capability input.",
    "state": "enum:idle|thinking|ready|error=idle; Lifecycle state.", "auto": "bool=true; Compose on mount."},
   True, "ready", ex={"args": ["A compact order summary with total and status"], "props": {"auto": False}})
_c("SmartForm", "ai", "Form inferred from a JSON Schema: grouping, labels, help text and input types.", "name",
   {"schema": "json; JSON Schema describing the record.", "values": "json; Current values.",
    "submitLabel": "str=Save; Submit button label.", "title": "str; Form title."}, False, "submit",
   ex={"args": ["contact"], "props": {"schema": {"type": "object", "properties": {"email": {"type": "string", "format": "email"}}}}})
_c("Approval", "ai", "Human-in-the-loop checkpoint for an agent action, with a risk rating.", "title",
   {"summary": "str; What will happen.", "risk": "enum:low|medium|high=medium; Risk rating.", "details": "json; [{key, value}].",
    "status": "enum:pending|approved|rejected=pending; Decision state.", "agent": "str; Requesting agent.",
    "approveLabel": "str=Approve; Approve button label.", "rejectLabel": "str=Reject; Reject button label."},
   False, "approve,reject", ex={"args": ["Refund order #4821"], "props": {"summary": "Refund $129.00 to the original card.", "risk": "medium"}})
_c("AgentTimeline", "ai", "Step-by-step account of what an agent did and why.", "",
   {"steps": "json; [{title, status, detail, tool, duration}]; status is done|running|pending|failed.", "title": "str; Header title."},
   ex={"props": {"steps": [{"title": "Read invoice", "status": "done", "tool": "ocr"}, {"title": "Match vendor", "status": "running"}]}})
_c("Tour", "ai", "Guided walkthrough anchored to elements of the scene.", "",
   {"steps": "json; [{target, title, body}].", "active": "bool; Running.", "current": "num=0; Active step."},
   False, "finish", ex={"props": {"steps": [{"target": "save", "title": "Save", "body": "Stores the draft."}], "active": False}})
_c("StreamText", "ai", "Text that reveals progressively as tokens arrive.", "text",
   {"streaming": "bool; Still receiving.", "speed": "num=24; Characters per frame when replaying."},
   ex={"args": ["Drafting a summary of the last 30 days…"], "props": {"streaming": True}})
_c("Diff", "ai", "Before/after comparison for rewrites.", "before,after",
   {"mode": "enum:inline|split=inline; Layout.", "title": "str; Header title."},
   ex={"args": ["We can not do that", "That isn't available yet"], "props": {"title": "Tone: friendly"}})
_c("Thinking", "ai", "Progress indicator for multi-step reasoning.", "label",
   {"steps": "json; Step labels.", "current": "num=0; Active step."}, ex={"args": ["Composing layout"], "props": {"steps": ["Read data", "Choose view"], "current": 1}})

# --- marketing ------------------------------------------------------------
ART_DOC = "{kind, hue, hue2, seed, ratio, variant, label, tone}"
_c("Theme", "layout", "Applies a theme preset or custom tokens to everything inside it.", "",
   {"preset": "enum:deep|abyss|iris|midnight|aurora|sunset|ember|ocean|forest|moss|rose|grape|citrus|sand|graphite|paper|terminal|crimson|candy|mint|gold|sky|emerald|neon|ruby|lagoon|tangerine; Named palette and type pairing.", "scheme": "enum:auto|light|dark=auto; Force a colour scheme.",
    "fill": "bool=true; Paint the themed background.", "tokens": "json; Extra tokens: [{name, value}]."}, True,
   ex={"props": {"preset": "midnight"}})
_c("Landing", "marketing", "Full-bleed page frame for marketing and storefront pages.", "",
   {"backdrop": "enum:none|glow|grid|mesh|dots|beams|aurora=none; Decorative background."}, True, ex={"props": {"backdrop": "glow"}})
_c("NavBar", "marketing", "Top navigation with brand, links and actions.", "brand",
   {"links": "json; [{label, href, active, badge}].", "logo": "str=orb; Brand mark shape.", "tag": "str; Small label next to the brand.",
    "sticky": "bool; Stick to the top while scrolling.", "glass": "bool=true; Translucent blurred surface.", "variant": "enum:bar|pill=bar; Full-width bar or floating pill."},
   True, "navigate", ex={"args": ["Lumen"], "props": {"links": [{"label": "Product", "href": "/product"}, {"label": "Pricing", "href": "/pricing"}]}})
_c("Band", "marketing", "Page section with a centred heading and generous spacing.", "title",
   {"eyebrow": "str; Small label above the title.", "subtitle": "str; Supporting line.", "highlight": "str; Part of the title to accent.",
    "align": "enum:start|center=center; Heading alignment.", "tone": "enum:plain|soft|inverse|brand|glow|line=plain; Background treatment.",
    "width": "enum:narrow|default|wide|full=default; Content width.", "pad": "enum:none|sm|md|lg=md; Vertical padding."}, True,
   ex={"args": ["Everything you need"], "props": {"eyebrow": "Platform", "subtitle": "One runtime, fourteen languages."}})
_c("Bento", "marketing", "Mosaic grid of cells with individual spans.", "",
   {"columns": "num=6; Column tracks.", "rowHeight": "num; Fixed row height in px."}, True, ex={"props": {"columns": 6}})
_c("BentoCell", "marketing", "One cell of a Bento grid.", "",
   {"span": "num=2; Columns to span.", "rows": "num=1; Rows to span.", "title": "str; Cell title.", "subtitle": "str; Supporting text.",
    "eyebrow": "str; Small label.", "icon": "str; Icon name.", "tone": "enum:plain|soft|brand|inverse|glow|ai=plain; Surface treatment.",
    "padding": "enum:none|sm|md|lg=md; Inner padding."}, True, ex={"props": {"span": 3, "title": "Realtime sync"}})
_c("Feature", "marketing", "Icon, title and description for a capability or benefit.", "title",
   {"body": "str; Description.", "icon": "str; Icon name.", "number": "str; Ordinal shown instead of an icon.", "eyebrow": "str; Small label.",
    "link": "str; Call-to-action text.", "tone": TONE + "=brand; Accent colour.", "variant": "enum:card|plain|tile|row=card; Layout."}, True,
   ex={"args": ["Instant previews"], "props": {"body": "Every change renders in under a second.", "icon": "bolt"}})
_c("LogoCloud", "marketing", "Row of customer or partner wordmarks drawn from names.", "",
   {"names": "json; Organisation names.", "label": "str; Line above the logos.", "variant": "enum:row|grid=row; Layout."},
   ex={"props": {"label": "Trusted by teams at", "names": ["Arcwell", "Kestrel", "Oakline", "Lumina"]}})
_c("Metrics", "marketing", "A row of headline numbers.", "",
   {"items": "json; [{value, label, detail}].", "variant": "enum:plain|cards|divided=plain; Presentation.", "align": "enum:start|center=center; Alignment."},
   ex={"props": {"items": [{"value": "99.99%", "label": "Uptime"}, {"value": "42 ms", "label": "Median latency"}]}})
_c("Testimonial", "marketing", "A customer quote with attribution.", "quote",
   {"author": "str; Person quoted.", "role": "str; Their role.", "company": "str; Their organisation.", "rating": "num; Stars out of five.",
    "variant": "enum:card|large|compact=card; Size."}, ex={"args": ["We shipped in a week."], "props": {"author": "Ines Duarte", "role": "CTO", "company": "Oakline"}})
_c("PricingCard", "marketing", "A plan with price, features and a call to action.", "plan",
   {"price": "str; Displayed price.", "period": "str; Billing period.", "description": "str; Who the plan is for.", "features": "json; Strings or {label, included}.",
    "cta": "str=Choose plan; Button label.", "featured": "bool; Highlight this plan.", "badge": "str; Ribbon text."}, False, "select",
   ex={"args": ["Team"], "props": {"price": "$24", "period": "per seat / month", "features": ["Unlimited projects", "SSO"], "featured": True}})
_c("Comparison", "marketing", "Feature comparison across plans.", "",
   {"plans": "json; [{name, price, featured}].", "rows": "json; [{label, values}] or {group}.", "label": "str; Heading of the first column."},
   ex={"props": {"plans": [{"name": "Free"}, {"name": "Pro", "featured": True}], "rows": [{"label": "Projects", "values": ["3", "Unlimited"]}, {"label": "SSO", "values": [False, True]}]}})
_c("FAQ", "marketing", "Questions that expand to reveal answers.", "",
   {"items": "json; [{q, a}].", "open": "num=0; Index open at first; -1 for none."},
   ex={"props": {"items": [{"q": "Can I self-host?", "a": "Yes. The engine is one Python process."}]}})
_c("CTA", "marketing", "Closing call to action.", "title",
   {"subtitle": "str; Supporting line.", "eyebrow": "str; Small label.", "highlight": "str; Part of the title to accent.",
    "tone": "enum:gradient|brand|inverse|soft|plain=gradient; Background.", "align": "enum:start|center=center; Alignment."}, True,
   ex={"args": ["Start building today"], "props": {"subtitle": "Free for individuals."}})
_c("Footer", "marketing", "Site footer with link columns.", "brand",
   {"tagline": "str; Line under the brand.", "columns": "json; [{title, links}].", "note": "str; Small print.", "logo": "str=orb; Brand mark shape.",
    "social": "json; Icon names."}, ex={"args": ["Lumen"], "props": {"columns": [{"title": "Product", "links": ["Features", "Pricing"]}], "note": "© 2026 Lumen Labs"}})
_c("PromoTile", "marketing", "Large promotional tile with artwork.", "title",
   {"subtitle": "str; Supporting line.", "eyebrow": "str; Small label.", "highlight": "str; Part of the title to accent.", "art": "json; Artwork: " + ART_DOC + ".",
    "tone": "enum:light|dark|tint|brand=light; Surface.", "size": "enum:sm|md|lg|xl=md; Height.", "layout": "enum:stack|split|overlay=stack; Copy and art arrangement.",
    "align": "enum:start|center=center; Copy alignment."}, True, ex={"args": ["Halo One"], "props": {"subtitle": "See further.", "art": {"kind": "glasses", "hue": 250}}})

# --- commerce -------------------------------------------------------------
_c("ProductCard", "commerce", "A product with artwork, price and rating.", "name",
   {"price": "str; Displayed price.", "compareAt": "str; Struck-through former price.", "brand": "str; Maker.", "detail": "str; One-line description.",
    "rating": "num; Average rating out of five.", "reviews": "num; Review count.", "badge": "str; Corner label.", "art": "json; Artwork: " + ART_DOC + ".",
    "swatches": "json; Colour values.", "variant": "enum:card|plain|row=card; Layout."}, False, "select,add",
   ex={"args": ["Night Serum"], "props": {"price": "$48", "rating": 4.8, "reviews": 312, "art": {"kind": "bottle", "hue": 290}}})
_c("Cart", "commerce", "Line items with artwork and quantity steppers.", "",
   {"items": "json; [{name, variant, price, qty, art}]."}, False, "change", ex={"props": {"items": [{"name": "Night Serum", "variant": "30 ml", "price": "$48", "qty": 1}]}})
_c("OrderSummary", "commerce", "Totals for an order, with room for actions.", "",
   {"title": "str; Heading.", "lines": "json; [{label, value, tone}].", "total": "str; Grand total.", "totalLabel": "str=Total; Label of the total row.",
    "note": "str; Small print."}, True, ex={"props": {"lines": [{"label": "Subtotal", "value": "$96.00"}, {"label": "Shipping", "value": "Free", "tone": "success"}], "total": "$96.00"}})
_c("Swatches", "input", "Choose one option from colour or text chips.", "name",
   {"label": "str; Field label.", "options": "json; Strings or {label, color, disabled}.", "value": "str; Selected option.",
    "variant": "enum:color|text; Chip style."}, False, "change", ex={"args": ["colour"], "props": {"label": "Colour", "options": [{"label": "Sand", "color": "#d9c7a8"}, {"label": "Ink", "color": "#1d2230"}]}})
_c("Quantity", "input", "Numeric stepper.", "name", {"label": "str; Field label.", "value": "num=1; Current value.", "min": "num=1; Lowest value.", "max": "num=99; Highest value."},
   False, "change", ex={"args": ["qty"], "props": {"label": "Quantity", "value": 2}})
_c("PinInput", "input", "One box per digit for verification codes.", "name",
   {"label": "str; Field label.", "length": "num=6; Number of digits.", "value": "str; Current value.", "help": "str; Helper text."}, False, "complete",
   ex={"args": ["code"], "props": {"label": "Verification code", "length": 6}})
_c("RatingSummary", "commerce", "Average rating with a distribution of scores.", "",
   {"average": "num; Mean score.", "count": "num; Number of reviews.", "distribution": "json; Counts from five stars down to one."},
   ex={"props": {"average": 4.7, "count": 1284, "distribution": [940, 250, 60, 20, 14]}})
_c("MediaGallery", "commerce", "Large artwork with selectable thumbnails.", "",
   {"items": "json; Artwork specs: " + ART_DOC + ".", "active": "num=0; Selected index.", "layout": "enum:bottom|side=bottom; Thumbnail position."},
   ex={"props": {"items": [{"kind": "bottle", "hue": 290}, {"kind": "jar", "hue": 290}]}})

# --- visual ---------------------------------------------------------------
_c("Art", "visual", "Procedural artwork: product shots, landscapes and abstract backdrops.", "kind",
   {"hue": "num; Base hue in degrees; omit to follow the theme.", "hue2": "num; Secondary hue.", "seed": "num; Variation.", "ratio": "str=4:3; Aspect ratio.",
    "width": "num; Fixed width in px; fills the available width when omitted.", "variant": "str; Kind-specific variant.", "label": "str; Text drawn into the artwork.", "glyph": "str; Icon for the glyph kind.", "tone": "enum:light|dark=light; Backdrop.",
    "rounded": "bool=true; Round the corners.", "shadow": "bool; Raise with a shadow.", "bare": "bool; Product kinds only: omit the backdrop.",
    "fit": "enum:cover|contain=cover; How the drawing fills its box.", "caption": "str; Caption over the artwork.", "alt": "str; Accessible description."},
   ex={"args": ["peaks"], "props": {"hue": 220, "ratio": "16:9"}})
_c("DeviceFrame", "visual", "Phone, tablet, laptop or browser frame around any content.", "",
   {"kind": "enum:phone|tablet|laptop|browser|window=phone; Device.", "platform": "enum:ios|android|web; Platform skin for the content.",
    "theme": "enum:deep|abyss|iris|midnight|aurora|sunset|ember|ocean|forest|moss|rose|grape|citrus|sand|graphite|paper|terminal|crimson|candy|mint|gold|sky|emerald|neon|ruby|lagoon|tangerine; Theme preset inside the frame.", "scheme": "enum:auto|light|dark=auto; Colour scheme inside the frame.",
    "url": "str; Address shown by the browser frame.", "title": "str; Window title.", "time": "str=9:41; Status bar clock.",
    "width": "num; Frame width in px.", "height": "num; Screen height in px.", "scale": "num=1; Zoom factor.", "caption": "str; Label under the device."}, True,
   ex={"props": {"kind": "phone", "platform": "ios"}})
_c("Screen", "visual", "A mobile app screen: title bar, scrolling body, tab bar and floating action.", "title",
   {"subtitle": "str; Line under the title.", "large": "bool=true; Use a large title.", "leading": "str; Icon of the leading button.",
    "trailing": "json; Icon names of trailing buttons.", "avatar": "str; Name for a trailing avatar.", "tabs": "json; [{label, icon, active, badge, route}].",
    "fab": "json; {icon, label} for a floating action.", "tone": "enum:plain|brand|tint=plain; Bar treatment."}, True, "action,navigate",
   ex={"args": ["Today"], "props": {"tabs": [{"label": "Home", "icon": "home", "active": True}, {"label": "Search", "icon": "search"}]}})
_c("Rings", "visual", "Concentric progress rings.", "",
   {"items": "json; [{label, value, max, display, color}].", "size": "num=168; Diameter in px.", "center": "str; Text in the middle.", "legend": "bool=true; Show the legend."},
   ex={"props": {"items": [{"label": "Move", "value": 420, "max": 600}, {"label": "Exercise", "value": 24, "max": 30}], "center": "70%"}})
_c("Gauge", "visual", "Arc gauge for a single value.", "",
   {"value": "num; Current value.", "max": "num=100; Full scale.", "display": "str; Text shown instead of the value.", "unit": "str; Unit under the value.",
    "label": "str; Caption.", "detail": "str; Supporting line.", "tone": TONE + "=brand; Colour.", "size": "num=180; Diameter in px."},
   ex={"props": {"value": 72, "unit": "°F", "label": "Living room"}})
_c("Sparkline", "visual", "Compact trend line or bars.", "",
   {"values": "json; Numbers.", "kind": "enum:area|line|bar=area; Style.", "tone": TONE + "=brand; Colour.", "width": "num=160; Width in px.", "height": "num=44; Height in px."},
   ex={"props": {"values": [4, 6, 5, 9, 12, 10, 14]}})
_c("Heatmap", "visual", "Grid of cells shaded by value.", "",
   {"values": "json; Rows of numbers, or a flat list with `columns`.", "columns": "num=7; Row length for a flat list.", "rowLabels": "json; Labels at the left.",
    "colLabels": "json; Labels on top.", "max": "num; Value mapped to full intensity.", "tone": TONE + "=brand; Colour.", "shape": "enum:square|round=square; Cell shape.",
    "label": "str; Accessible description."}, ex={"props": {"values": [[1, 4, 2, 0, 5, 3, 1], [2, 5, 3, 1, 4, 6, 2]], "rowLabels": ["Mon", "Tue"]}})
_c("BarList", "visual", "Ranked list with proportional bars.", "",
   {"items": "json; [{label, value, display, detail, icon, hue, color}].", "format": "enum:number|compact|currency|percent=compact; Value format.", "max": "num; Full-width value.",
    "ranked": "bool; Show rank numbers.", "tone": TONE + "=brand; Colour.", "variant": "enum:bar|fill=bar; Bar under the row or behind it."},
   ex={"props": {"items": [{"label": "atlas-large", "value": 48200}, {"label": "quill-mini", "value": 31900}], "ranked": True}})
_c("Ticker", "visual", "Prices with change and a mini trend.", "",
   {"items": "json; [{symbol, name, price, change, spark}].", "layout": "enum:list|row=list; Arrangement."},
   ex={"props": {"items": [{"symbol": "NWD", "name": "Northwind", "price": "$184.20", "change": "+1.4%", "spark": [3, 4, 3, 5, 6]}]}})
_c("MapView", "visual", "Stylised city or world map with pins and routes.", "",
   {"kind": "enum:city|world=city; Map style.", "pins": "json; [{x, y, label, tone, pulse}] or [{lon, lat, …}] on the world map.", "routes": "json; [{points, tone, dashed}].",
    "height": "num=360; Height in px.", "seed": "num; Street layout variation.", "label": "str; Accessible description."}, True, "select",
   ex={"props": {"kind": "world", "pins": [{"lon": -74, "lat": 40.7, "label": "New York"}, {"lon": 139.7, "lat": 35.7, "label": "Tokyo"}]}})
_c("Candles", "data", "Candlestick chart with optional volume.", "",
   {"data": "json; [{t, o, h, l, c, v}].", "height": "num=280; Height in px.", "volume": "bool=true; Show volume bars.", "title": "str; Chart title.",
    "format": "enum:number|currency|compact=number; Axis format."}, ex={"props": {"data": [{"t": "09:30", "o": 10, "h": 12, "l": 9, "c": 11, "v": 30}, {"t": "10:00", "o": 11, "h": 13, "l": 10, "c": 12.5, "v": 44}]}})
_c("Funnel", "data", "Stages of a conversion funnel.", "",
   {"stages": "json; [{label, value}].", "format": "enum:number|compact|currency|percent=compact; Value format.", "tone": TONE + "=brand; Colour."},
   ex={"props": {"stages": [{"label": "Visited", "value": 12000}, {"label": "Signed up", "value": 3100}, {"label": "Paid", "value": 640}]}})
_c("Waveform", "visual", "Audio waveform with a played portion.", "",
   {"values": "json; Amplitudes; generated when omitted.", "bars": "num=56; Bars to generate.", "progress": "num=0; Played fraction from 0 to 1.", "height": "num=48; Height in px.",
    "seed": "num; Variation.", "tone": TONE + "=brand; Colour.", "label": "str; Accessible description."}, ex={"props": {"progress": 0.4}})
_c("Calendar", "data", "Month grid with events.", "month",
   {"events": "json; [{day, label, tone}].", "selected": "num; Selected day.", "today": "num; Day marked as today.", "compact": "bool; Small cells with dots."},
   False, "select,navigate", ex={"args": ["2026-11"], "props": {"events": [{"day": 12, "label": "Launch", "tone": "brand"}], "today": 19}})
_c("Schedule", "data", "Day agenda on an hourly grid, with optional lanes.", "",
   {"items": "json; [{start, end, title, detail, tone, lane}].", "from": "num=8; First hour.", "to": "num=18; Last hour.", "lanes": "json; Lane titles.",
    "now": "str; Current time marker.", "rowHeight": "num=46; Pixels per hour."}, False, "select",
   ex={"props": {"items": [{"start": "09:00", "end": "10:30", "title": "Design review"}], "from": 8, "to": 13}})
_c("Roadmap", "data", "Horizontal bars across time columns.", "",
   {"columns": "json; Column labels.", "rows": "json; [{label, avatar, bars: [{start, end, label, tone, progress}]}].", "today": "num; Position of the today marker.", "label": "str; Heading of the label column."},
   ex={"props": {"columns": ["W1", "W2", "W3", "W4"], "rows": [{"label": "Checkout", "bars": [{"start": 0, "end": 2.5, "label": "Build", "progress": 60}]}]}})
_c("Chat", "content", "Conversation with bubbles, tool calls and a composer.", "",
   {"messages": "json; [{from, name, text, time, status, rich, tool, citations, chips, art}]; from is me|them|ai|system.", "title": "str; Conversation title.",
    "subtitle": "str; Line under the title.", "status": "enum:online|away|busy; Presence of the other party.", "actions": "json; Icon names for header buttons.",
    "composer": "bool=true; Show the message box.", "placeholder": "str=Message; Composer placeholder.", "typing": "bool; Show a typing indicator.",
    "avatars": "bool=true; Show avatars.", "variant": "enum:bubbles|flat=bubbles; Message style."}, False, "send,action",
   ex={"props": {"title": "Ana Lima", "messages": [{"from": "them", "text": "Are we still on for 3?"}, {"from": "me", "text": "Yes — see you then."}]}})
_c("Terminal", "content", "Terminal window with commands and output.", "",
   {"lines": "json; Strings or {text, kind}; kind is cmd|out|ok|warn|err|dim.", "title": "str; Window title.", "tabs": "json; Tab labels.", "active": "num=0; Active tab.",
    "prompt": "str=$; Prompt symbol.", "cursor": "bool=true; Show a cursor."}, ex={"props": {"lines": ["$ fluidian new app --lang go", {"text": "Created app/main.go", "kind": "ok"}]}})
_c("Player", "content", "Media player with artwork, progress and transport controls.", "title",
   {"artist": "str; Artist or source.", "art": "json; Artwork: " + ART_DOC + ".", "progress": "num; Seconds played.", "duration": "num; Length in seconds.", "playing": "bool; Playing.",
    "variant": "enum:card|bar|large=card; Layout."}, False, "toggle,control", ex={"args": ["Low Tide"], "props": {"artist": "Marlowe Quartet", "progress": 74, "duration": 212}})
_c("AvatarStack", "content", "Overlapping avatars with an overflow count.", "",
   {"names": "json; People.", "max": "num=4; Avatars shown before the count.", "size": SIZE + "=sm; Avatar size.", "label": "str; Text after the stack."},
   ex={"props": {"names": ["Mira Okafor", "Jonas Weber", "Ana Lima", "Kenji Sato", "Priya Nair"], "label": "5 online"}})
_c("ControlTile", "input", "Toggle tile for a device, scene or quick action.", "title",
   {"icon": "str; Icon name.", "on": "bool; Active.", "value": "str; Text when on.", "offValue": "str=Off; Text when off.", "detail": "str; Supporting line.", "tone": TONE + "=brand; Accent."},
   False, "toggle", ex={"args": ["Living room"], "props": {"icon": "bulb", "on": True, "value": "70%"}})
_c("PromptBox", "ai", "Large prompt composer with modes and starter chips.", "",
   {"placeholder": "str; Placeholder text.", "value": "str; Initial text.", "chips": "json; Starter prompts.", "modes": "json; Mode labels.", "mode": "str; Selected mode.",
    "hint": "str; Small text beside the send button.", "button": "str; Send button label.", "rows": "num=2; Visible text rows."}, False, "submit",
   ex={"props": {"placeholder": "Describe the screen you need…", "chips": ["A pricing page", "An order tracker"], "modes": ["Plan", "Build"]}})

# --- logic ----------------------------------------------------------------
_c("State", "logic", "Declares client-side state for bindings and portable actions.", "",
   {"values": "json; Initial values by name."}, ex={"props": {"values": {"count": 0, "todos": []}}})
_c("Show", "logic", "Renders its children only while an expression is true.", "when", {}, True, ex={"args": ["count > 0"]})
_c("Each", "logic", "Repeats its children for every item of a list.", "items",
   {"as": "str=item; Name of the item in bindings.", "empty": "str; Text shown when the list is empty.", "layout": "enum:stack|row|grid=stack; Arrangement."}, True,
   ex={"args": ["todos"], "props": {"as": "todo"}})

TYPES: List[str] = [c["type"] for c in COMPONENTS]
_AUTO_ID = re.compile(r"^_r(\.\d+)*(~\d+)?$")


def is_auto_id(node_id: Any) -> bool:
    """True for ids assigned by :func:`normalize` (path based, e.g. ``_r.0.2``)."""
    return isinstance(node_id, str) and bool(_AUTO_ID.match(node_id))

CONTAINERS = {c["type"] for c in COMPONENTS if c["container"]}
MAX_NODES = 4000
MAX_DEPTH = 32


# ---------------------------------------------------------------------------
# Scene utilities
# ---------------------------------------------------------------------------
def _coerce(value: Any, kind: str) -> Tuple[Any, bool]:
    """Coerce ``value`` to ``kind``; returns (value, ok)."""
    if value is None:
        return None, True
    if kind == "str":
        if isinstance(value, str):
            return value, True
        if isinstance(value, (int, float, bool)):
            return (json.dumps(value) if isinstance(value, bool) else str(value)), True
        return value, False
    if kind == "num":
        if isinstance(value, bool):
            return value, False
        if isinstance(value, (int, float)):
            return value, True
        if isinstance(value, str):
            try:
                number = float(value)
                return (int(number) if number.is_integer() else number), True
            except ValueError:
                return value, False
        return value, False
    if kind == "bool":
        if isinstance(value, bool):
            return value, True
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true", True
        return value, False
    if kind.startswith("enum:"):
        return value, isinstance(value, str) and value in kind[5:].split("|")
    return value, True  # json


def normalize(node: Any, actions: Optional[List[str]] = None, capabilities: Optional[set] = None,
              drop_unknown: bool = False) -> Tuple[Dict[str, Any], List[str]]:
    """Validate and canonicalise a scene.

    * guarantees ``type``, ``id``, ``props``, ``children``, ``on`` and ``ai`` on every node
    * assigns stable path-based ids to nodes without one and de-duplicates ids
    * coerces prop types, optionally dropping props the component does not define
    * removes children from non-container components
    * with ``actions`` given, removes event bindings that reference unknown actions
      (portable actions, whose name starts with ``@``, run in the runtime and are kept)

    Returns ``(scene, fixes)`` where ``fixes`` lists every repair that was made.
    """
    fixes: List[str] = []
    seen: Dict[str, int] = {}
    count = [0]

    def visit(raw: Any, path: str, depth: int) -> Optional[Dict[str, Any]]:
        count[0] += 1
        if count[0] > MAX_NODES:
            if count[0] == MAX_NODES + 1:
                fixes.append("scene truncated at %d nodes" % MAX_NODES)
            return None
        if isinstance(raw, str):
            raw = {"type": "Text", "props": {"content": raw}}
        if not isinstance(raw, dict):
            fixes.append("%s: dropped non-object node" % path)
            return None
        type_ = raw.get("type")
        spec = SPEC.get(type_) if isinstance(type_, str) else None
        if spec is None:
            label = ""
            if isinstance(raw.get("props"), dict):
                label = next((str(v) for v in raw["props"].values() if isinstance(v, str)), "")
            kids = raw.get("children") if isinstance(raw.get("children"), list) else []
            if kids:
                fixes.append("%s: unknown component %r replaced with Stack" % (path, type_))
                raw = {"type": "Stack", "id": raw.get("id"), "props": {}, "children": kids}
            elif label or not drop_unknown:
                fixes.append("%s: unknown component %r replaced with Text" % (path, type_))
                raw = {"type": "Text", "id": raw.get("id"), "props": {"content": label or str(type_ or "")}}
            else:
                fixes.append("%s: removed unknown component %r" % (path, type_))
                return None
            type_ = raw["type"]
            spec = SPEC[type_]
        props_in = raw.get("props") if isinstance(raw.get("props"), dict) else {}
        props: Dict[str, Any] = {}
        for key, value in props_in.items():
            pspec = spec["props"].get(key)
            if pspec is None:
                if drop_unknown:
                    fixes.append("%s: dropped unknown prop %s.%s" % (path, type_, key))
                    continue
                props[key] = value
                continue
            if isinstance(value, str) and "{{" in value:
                props[key] = value  # a binding resolves to its real type in the runtime
                continue
            coerced, ok = _coerce(value, pspec["kind"])
            if not ok:
                fixes.append("%s: %s.%s expects %s" % (path, type_, key, pspec["kind"]))
                if drop_unknown:
                    continue
            props[key] = coerced
        node_id = raw.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            node_id = path
        else:
            node_id = node_id.strip()
        if node_id in seen:
            seen[node_id] += 1
            fixes.append("%s: duplicate id %r renamed" % (path, node_id))
            node_id = "%s~%d" % (node_id, seen[node_id])
        seen.setdefault(node_id, 0)
        on: Dict[str, Dict[str, Any]] = {}
        raw_on = raw.get("on") if isinstance(raw.get("on"), dict) else {}
        for event, binding in raw_on.items():
            if isinstance(binding, str):
                binding = {"action": binding}
            if not isinstance(binding, dict) or not isinstance(binding.get("action"), str):
                fixes.append("%s: dropped malformed binding for %r" % (path, event))
                continue
            if actions is not None and binding["action"] not in actions and not binding["action"].startswith("@"):
                fixes.append("%s: dropped binding to unknown action %r" % (path, binding["action"]))
                continue
            entry: Dict[str, Any] = {"action": binding["action"]}
            if "payload" in binding:
                entry["payload"] = binding["payload"]
            on[str(event)] = entry
        ai: List[Dict[str, Any]] = []
        raw_ai = raw.get("ai") if isinstance(raw.get("ai"), list) else []
        for binding in raw_ai:
            if isinstance(binding, str):
                binding = {"capability": binding}
            if not isinstance(binding, dict) or not isinstance(binding.get("capability"), str):
                fixes.append("%s: dropped malformed ai binding" % path)
                continue
            if capabilities is not None and binding["capability"] not in capabilities:
                fixes.append("%s: dropped unknown capability %r" % (path, binding["capability"]))
                continue
            options = binding.get("options")
            ai.append({"capability": binding["capability"], "options": options if isinstance(options, dict) else {}})
        children: List[Dict[str, Any]] = []
        raw_children = raw.get("children") if isinstance(raw.get("children"), list) else []
        if raw_children and not spec["container"]:
            fixes.append("%s: %s does not accept children" % (path, type_))
            raw_children = []
        if depth >= MAX_DEPTH and raw_children:
            fixes.append("%s: maximum depth reached" % path)
            raw_children = []
        for index, child in enumerate(raw_children):
            built = visit(child, "%s.%d" % (path, index), depth + 1)
            if built is not None:
                children.append(built)
        return {"type": type_, "id": node_id, "props": props, "children": children, "on": on, "ai": ai}

    root = visit(node, "_r", 0)
    if root is None:
        root = {"type": "Page", "id": "_r", "props": {"title": ""}, "children": [], "on": {}, "ai": []}
        fixes.append("scene root was invalid")
    return root, fixes


def from_transport(tnode: Any) -> Dict[str, Any]:
    """Decode the strict transport encoding produced by the model into a scene node.

    Nodes that are already in scene form (``props`` is an object) pass through.
    """
    if not isinstance(tnode, dict):
        return {"type": "Text", "props": {"content": str(tnode)}}
    if isinstance(tnode.get("props"), dict):
        out = dict(tnode)
        out["children"] = [from_transport(c) for c in (tnode.get("children") or [])]
        return out
    type_ = tnode.get("type")
    spec = SPEC.get(type_, SPEC["Text"])
    props: Dict[str, Any] = {}
    for pair in tnode.get("props") or []:
        if not isinstance(pair, dict) or "key" not in pair:
            continue
        value = pair.get("value")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                pass
        props[str(pair["key"])] = value
    text = tnode.get("text")
    if isinstance(text, str) and text and spec.get("primary") and spec["primary"] not in props:
        props[spec["primary"]] = text
    elif isinstance(text, str) and text and not spec.get("primary"):
        for candidate in ("title", "label", "body"):
            if candidate in spec["props"] and candidate not in props:
                props[candidate] = text
                break
    node: Dict[str, Any] = {"type": type_, "props": props,
                            "children": [from_transport(c) for c in (tnode.get("children") or [])]}
    if isinstance(tnode.get("id"), str) and tnode["id"]:
        node["id"] = tnode["id"]
    action = tnode.get("action")
    if isinstance(action, str) and action and spec.get("events"):
        node["on"] = {spec["events"][0]: {"action": action}}
    return node


def is_transport(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("props"), list) and "type" in value and "children" in value


def to_transport(node: Dict[str, Any]) -> Dict[str, Any]:
    """Encode a scene node into the transport form (inverse of :func:`from_transport`)."""
    spec = SPEC.get(node.get("type"), SPEC["Text"])
    props = dict(node.get("props") or {})
    text = None
    if spec.get("primary") and isinstance(props.get(spec["primary"]), str):
        text = props.pop(spec["primary"])
    return {
        "type": node.get("type", "Text"),
        "id": node.get("id") if isinstance(node.get("id"), str) and not is_auto_id(node.get("id")) else None,
        "text": text,
        "action": next((b.get("action") for b in (node.get("on") or {}).values() if isinstance(b, dict)), None),
        "props": [{"key": k, "value": json.dumps(v, ensure_ascii=False)} for k, v in props.items()],
        "children": [to_transport(c) for c in node.get("children") or []],
    }


def walk(node: Dict[str, Any], depth: int = 0, parent: Optional[Dict[str, Any]] = None
         ) -> Iterator[Tuple[Dict[str, Any], int, Optional[Dict[str, Any]]]]:
    yield node, depth, parent
    for child in node.get("children") or []:
        if isinstance(child, dict):
            yield from walk(child, depth + 1, node)


def find(node: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    for candidate, _, _ in walk(node):
        if candidate.get("id") == node_id:
            return candidate
    return None


def primary_text(node: Dict[str, Any]) -> str:
    props = node.get("props") or {}
    for key in ("title", "label", "text", "content", "brand", "name", "intent", "placeholder", "value"):
        value = props.get(key)
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
    return ""


def digest(node: Dict[str, Any], budget: int = 2400) -> str:
    """Compress a scene into an indented outline for use as model context.

    The outline keeps structure, visible text, field names and bound actions and
    drops presentation props, so a large screen fits in a few hundred tokens.
    """
    lines: List[str] = []
    used = 0
    for item, depth, _ in walk(node):
        props = item.get("props") or {}
        bits = [item.get("type", "?")]
        if item.get("id") and not is_auto_id(item.get("id")):
            bits.append("#" + str(item.get("id")))
        text = primary_text(item)
        if text:
            bits.append(json.dumps(text[:80], ensure_ascii=False))
        for key in ("name", "kind", "variant", "tone", "value", "error", "status", "risk"):
            if key in props and props[key] not in (None, "") and str(props[key]) != text:
                bits.append("%s=%s" % (key, str(props[key])[:40]))
        for key in ("rows", "items", "options", "data", "steps", "messages", "columns"):
            if isinstance(props.get(key), list):
                bits.append("%s[%d]" % (key, len(props[key])))
        for event, binding in (item.get("on") or {}).items():
            bits.append("@%s→%s" % (event, binding.get("action")))
        for binding in item.get("ai") or []:
            bits.append("✦" + binding.get("capability", ""))
        line = "  " * min(depth, 8) + " ".join(bits)
        if used + len(line) > budget:
            lines.append("  " * min(depth, 8) + "…")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


def stats(node: Dict[str, Any]) -> Dict[str, Any]:
    by_type: Dict[str, int] = {}
    depth_max = 0
    bindings = 0
    for item, depth, _ in walk(node):
        by_type[item.get("type", "?")] = by_type.get(item.get("type", "?"), 0) + 1
        depth_max = max(depth_max, depth)
        bindings += len(item.get("ai") or [])
    return {"nodes": sum(by_type.values()), "depth": depth_max, "byType": by_type, "aiBindings": bindings}


def diff(before: Optional[Dict[str, Any]], after: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Structural difference between two scenes, keyed by node id."""
    def index(root: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {n["id"]: n for n, _, _ in walk(root)} if root else {}

    a, b = index(before), index(after)
    changes: List[Dict[str, Any]] = []
    for node_id, node in b.items():
        if node_id not in a:
            changes.append({"op": "added", "id": node_id, "type": node["type"], "text": primary_text(node)})
            continue
        old = a[node_id]
        if old["type"] != node["type"]:
            changes.append({"op": "replaced", "id": node_id, "type": node["type"], "was": old["type"], "text": primary_text(node)})
            continue
        keys = sorted(set(old["props"]) | set(node["props"]))
        changed = [k for k in keys if old["props"].get(k) != node["props"].get(k)]
        if changed:
            changes.append({"op": "changed", "id": node_id, "type": node["type"], "props": changed, "text": primary_text(node)})
    for node_id, node in a.items():
        if node_id not in b:
            changes.append({"op": "removed", "id": node_id, "type": node["type"], "text": primary_text(node)})
    return changes


def export_spec() -> Dict[str, Any]:
    return {"version": 1, "components": COMPONENTS}
