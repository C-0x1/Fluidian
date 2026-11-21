"""Scene nodes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_MISSING = object()


class Node:
    """One element of a scene. Every method returns the node so calls can be chained."""

    __slots__ = ("type", "_id", "_props", "_children", "_on", "_ai")

    def __init__(self, type: str) -> None:
        self.type = type
        self._id: Optional[str] = None
        self._props: Dict[str, Any] = {}
        self._children: List["Node"] = []
        self._on: Dict[str, Dict[str, Any]] = {}
        self._ai: List[Dict[str, Any]] = []

    def prop(self, key: str, value: Any) -> "Node":
        """Set a property. Values may be any JSON-compatible data."""
        self._props[key] = value
        return self

    def id(self, value: str) -> "Node":
        """Give the node a stable identity (used for events, focus and AI targeting)."""
        self._id = value
        return self

    def on(self, event: str, action: str, payload: Any = _MISSING) -> "Node":
        """Bind a component event to a named action, optionally with a payload."""
        binding: Dict[str, Any] = {"action": action}
        if payload is not _MISSING:
            binding["payload"] = payload
        self._on[event] = binding
        return self

    def ai(self, capability: str, options: Optional[Dict[str, Any]] = None) -> "Node":
        """Attach an AI capability to this node."""
        self._ai.append({"capability": capability, "options": options or {}})
        return self

    def add(self, *children: Optional["Node"]) -> "Node":
        """Append child nodes (``None`` entries are skipped, which keeps conditionals tidy)."""
        self._children.extend(c for c in children if c is not None)
        return self

    def to_json(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"type": self.type, "props": self._props}
        if self._id is not None:
            out["id"] = self._id
        if self._children:
            out["children"] = [c.to_json() for c in self._children]
        if self._on:
            out["on"] = self._on
        if self._ai:
            out["ai"] = self._ai
        return out
