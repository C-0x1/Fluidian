"""Capability registry.

A *capability* is one AI-native feature: a contract (input and output
schema), an instruction for the model, a local Reflex implementation, and a
declaration of how the runtime presents its result.

Three execution kinds exist:

``model``   Reason path calls the model; Reflex path is a local heuristic.
``hybrid``  Local code computes facts first; the model narrates or decides
            on top of them, so numbers are never invented.
``direct``  Deterministic kernel service; always runs locally.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from .. import components as C
from ..schema import compile_schema, node_defs, uses_node

# --- reusable output shapes --------------------------------------------------
TEXT = {"text": "str", "rationale?": "str"}
ITEMS = {"items": [{"label": "str", "detail?": "str", "value?": "str", "action?": "str", "icon?": "str", "score?": "num"}]}
NOTE = {"title": "str", "body": "str", "bullets": ["str"], "confidence": "num",
        "tone": "enum:neutral|success|warning|danger|info|ai"}
VERDICT = {"ok": "bool", "severity": "enum:info|warning|error", "message": "str", "suggestion?": "str"}
FIELDS = {"fields": [{"name": "str", "value": "str", "confidence": "num"}], "notes?": "str"}
VALUE = {"value": "str", "display": "str", "confidence": "num", "explanation?": "str"}
SCENE = {"scene": "node", "rationale": "str"}
REPORT = {"score": "num", "summary": "str",
          "findings": [{"id": "str", "severity": "enum:info|warning|error", "title": "str", "detail": "str",
                        "target?": "str", "fix?": "str"}]}
PLAN = {"summary": "str", "steps": [{"title": "str", "action?": "str", "args": "json",
                                     "risk": "enum:low|medium|high", "why?": "str"}]}
DIRECTIVES = {"state": "str", "confidence": "num",
              "directives": [{"kind": "str", "target?": "str", "value?": "str", "reason": "str"}]}

PRESENTERS = {
    "ghost": "Inline ghost text inside the field; Tab accepts.",
    "rewrite": "A ✦ menu on the field offers the transformation with a before/after preview.",
    "validate": "A coaching message under the field, updated on blur.",
    "fill": "Writes the resolved value (or several field values) into the form.",
    "suggest": "Chips or a ranked list rendered next to the component.",
    "annotate": "An insight panel attached to the component, with confidence and provenance.",
    "transform": "Replaces the component's text in place; a provenance badge allows reverting.",
    "compose": "Renders the returned scene inside the component.",
    "ask": "A popover answers questions about the element or screen.",
    "command": "The Intent Bar executes the matched action.",
    "chat": "Streaming replies inside the Copilot component.",
    "audit": "A findings list with severities; selecting a finding highlights its target.",
    "theme": "Applies design tokens to the document.",
    "media": "Produces or consumes audio and images.",
    "observe": "Runs on interaction signals and returns adaptation directives.",
    "service": "Invoked from application code, the CLI or the developer tools.",
}

CATEGORIES: Dict[str, Dict[str, str]] = {
    "compose": {"title": "Generative Composition", "blurb": "Interfaces assembled at runtime from intent, data, schemas and sketches."},
    "input": {"title": "Input Intelligence", "blurb": "Fields that complete, parse, heal and coach instead of rejecting."},
    "command": {"title": "Conversational Command", "blurb": "Language as a first-class way to operate an application."},
    "adapt": {"title": "Adaptive Personalisation", "blurb": "Interfaces that respond to how each person actually works."},
    "access": {"title": "Accessibility Intelligence", "blurb": "Inclusive defaults generated, audited and repaired automatically."},
    "design": {"title": "Design-System Intelligence", "blurb": "Themes, palettes, type and motion derived from intent and verified by maths."},
    "data": {"title": "Data & Visualisation Intelligence", "blurb": "Data that explains itself: the right chart, grounded insights, plain-language queries."},
    "content": {"title": "Content & Microcopy", "blurb": "Words that fit the space, the reader and the moment."},
    "flow": {"title": "Workflow & Agentic UI", "blurb": "Goal-driven flows and the controls that keep people in charge of agents."},
    "trust": {"title": "Trust, Safety & Governance", "blurb": "The guarantees that make generated interfaces safe to ship."},
    "perf": {"title": "Intelligence Infrastructure", "blurb": "Caching, routing, streaming and resilience for model-backed UI."},
    "dev": {"title": "Developer Experience", "blurb": "Review, testing, scaffolding and translation between fourteen languages."},
    "modal": {"title": "Multimodal", "blurb": "Voice, vision and generated imagery as interface primitives."},
    "collab": {"title": "Collaboration", "blurb": "Shared work summarised, mediated and kept moving."},
    "ambient": {"title": "Ambient & Emotional UX", "blurb": "Small moments of timing, tone and care."},
}


@dataclass
class Ctx:
    """Execution context handed to Reflex, facts and direct handlers."""
    scene: Optional[Dict[str, Any]] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    now: datetime = field(default_factory=datetime.now)
    locale: str = "en-US"
    signals: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    sid: str = ""
    kernel: Any = None
    facts: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Capability:
    id: str
    title: str
    summary: str
    why: str
    do: str
    inp: Dict[str, Any]
    out: Dict[str, Any]
    present: str = "service"
    tier: str = "fast"
    binds: List[str] = field(default_factory=list)
    example: Dict[str, Any] = field(default_factory=dict)
    reflex: Optional[Callable[[Dict[str, Any], Ctx], Dict[str, Any]]] = None
    direct: Optional[Callable[[Dict[str, Any], Ctx], Dict[str, Any]]] = None
    facts: Optional[Callable[[Dict[str, Any], Ctx], Dict[str, Any]]] = None
    post: Optional[Callable[[Dict[str, Any], Dict[str, Any], Ctx], Dict[str, Any]]] = None
    uses_scene: bool = False
    uses_actions: bool = False
    vision: bool = False
    consent: str = ""
    moderate: bool = False
    stream: bool = False
    cache: bool = True
    max_out: int = 900
    untrusted: List[str] = field(default_factory=list)
    _schemas: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def category(self) -> str:
        return self.id.split(".", 1)[0]

    @property
    def kind(self) -> str:
        return "direct" if self.direct else ("hybrid" if self.facts else "model")

    @property
    def native_reflex(self) -> bool:
        return self.reflex is not None or self.direct is not None

    @property
    def input_schema(self) -> Dict[str, Any]:
        if "in" not in self._schemas:
            self._schemas["in"] = compile_schema(self.inp, strict=False)
        return self._schemas["in"]

    @property
    def output_schema(self) -> Dict[str, Any]:
        if "out" not in self._schemas:
            schema = compile_schema(self.out, strict=True)
            if uses_node(schema):
                schema["$defs"] = node_defs(C.TYPES)
            self._schemas["out"] = schema
        return self._schemas["out"]

    def describe(self) -> Dict[str, Any]:
        return {"id": self.id, "title": self.title, "category": self.category, "summary": self.summary, "why": self.why,
                "present": self.present, "tier": self.tier, "kind": self.kind, "binds": self.binds,
                "example": self.example, "nativeReflex": self.native_reflex, "usesScene": self.uses_scene,
                "usesActions": self.uses_actions, "vision": self.vision, "consent": self.consent, "stream": self.stream,
                "inputSchema": self.input_schema, "outputSchema": self.output_schema}


REGISTRY: Dict[str, Capability] = {}


def cap(id: str, title: str, summary: str, *, why: str, do: str = "", inp: Dict[str, Any], out: Dict[str, Any],
        ex: Dict[str, Any], **kw: Any) -> Capability:
    if id in REGISTRY:
        raise ValueError("duplicate capability id: %s" % id)
    if id.split(".", 1)[0] not in CATEGORIES:
        raise ValueError("unknown category for %s" % id)
    c = Capability(id=id, title=title, summary=summary, why=why, do=do, inp=inp, out=out, example=ex, **kw)
    if c.present not in PRESENTERS:
        raise ValueError("unknown presenter %r for %s" % (c.present, id))
    REGISTRY[id] = c
    return c


# --- output helpers used by Reflex implementations ---------------------------
def note(title: str, body: str, bullets: Optional[List[str]] = None, confidence: float = 0.6, tone: str = "ai") -> Dict[str, Any]:
    return {"title": title, "body": body, "bullets": list(bullets or []), "confidence": float(confidence), "tone": tone}


def items(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = []
    for r in rows:
        out.append({"label": str(r.get("label", "")), "detail": r.get("detail"), "value": None if r.get("value") is None else str(r.get("value")),
                    "action": r.get("action"), "icon": r.get("icon"), "score": r.get("score")})
    return {"items": out}


def verdict(ok: bool, message: str, severity: str = "info", suggestion: Optional[str] = None) -> Dict[str, Any]:
    return {"ok": bool(ok), "severity": severity, "message": message, "suggestion": suggestion}


def fields(rows: List[Dict[str, Any]], notes: Optional[str] = None) -> Dict[str, Any]:
    return {"fields": [{"name": str(r["name"]), "value": str(r["value"]), "confidence": float(r.get("confidence", 0.6))} for r in rows],
            "notes": notes}


def value(v: Any, display: Optional[str] = None, confidence: float = 0.7, explanation: Optional[str] = None) -> Dict[str, Any]:
    return {"value": str(v), "display": str(display if display is not None else v), "confidence": float(confidence),
            "explanation": explanation}


def scene(node: Dict[str, Any], rationale: str) -> Dict[str, Any]:
    return {"scene": C.to_transport(node), "rationale": rationale}


def directives(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"state": str(result.get("state", "")), "confidence": float(result.get("confidence", 0.5)),
            "directives": [{"kind": d["kind"], "target": d.get("target"), "value": d.get("value"), "reason": d["reason"]}
                           for d in result.get("directives", [])]}


def texts_of(scene_node: Optional[Dict[str, Any]], limit: int = 60) -> List[str]:
    out: List[str] = []
    if not scene_node:
        return out
    for n, _, _ in C.walk(scene_node):
        for key in ("title", "label", "text", "content", "subtitle", "body", "description", "help", "placeholder"):
            v = (n.get("props") or {}).get(key)
            if isinstance(v, str) and v.strip() and v not in out:
                out.append(v)
                if len(out) >= limit:
                    return out
    return out


def load_all() -> Dict[str, Capability]:
    """Import every category module so the registry is populated."""
    if len(REGISTRY) < 10:
        from . import c_compose, c_input, c_command, c_adapt, c_design, c_content, c_trust, c_dev  # noqa: F401
    return REGISTRY
