"""Fluidian SDK for Python.

    from fluidian import App, ui

    app = App("Counter")

    @app.view
    def view(ctx):
        return ui.page("Counter",
            ui.text("Count: %d" % ctx.state.get("count", 0)),
            ui.button("Add one").on("click", "increment"))

    @app.on("increment")
    def increment(ctx, event):
        ctx.state["count"] = ctx.state.get("count", 0) + 1

    app.run()

Run it with ``fluidian run -- python3 app.py``.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from typing import Any, Callable, Dict, List, Optional

from .node import Node
from . import ui

__version__ = "1.2.0"
PROTOCOL = 1
__all__ = ["App", "Ctx", "Event", "Node", "AIError", "ui"]


class AIError(Exception):
    """Raised by :meth:`Ctx.ai` when a capability cannot be fulfilled."""


class Event:
    """An interaction delivered to a handler."""

    __slots__ = ("name", "target", "value", "form", "payload")

    def __init__(self, msg: Dict[str, Any]) -> None:
        self.name: str = msg.get("name") or ""
        self.target: Optional[str] = msg.get("target")
        self.value: Any = msg.get("value")
        self.form: Dict[str, Any] = msg.get("form") or {}
        self.payload: Any = msg.get("payload")


class _Session:
    __slots__ = ("state", "route", "locale")

    def __init__(self, route: str, locale: str) -> None:
        self.state: Dict[str, Any] = {}
        self.route = route
        self.locale = locale


class Ctx:
    """Per-session context: state, navigation, notifications and AI."""

    def __init__(self, app: "App", sid: str, session: _Session) -> None:
        self._app, self._session = app, session
        self.sid = sid
        self.state = session.state

    @property
    def route(self) -> str:
        return self._session.route

    @property
    def locale(self) -> str:
        return self._session.locale

    def toast(self, text: str, tone: str = "info") -> None:
        self._app._send({"t": "toast", "sid": self.sid, "text": text, "tone": tone})

    def navigate(self, route: str) -> None:
        self._session.route = route
        self._app._send({"t": "navigate", "sid": self.sid, "route": route})

    def ai(self, capability: str, input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke a capability and wait for its result."""
        return self._app._ai(self.sid, capability, input or {})


class App:
    def __init__(self, name: str, **meta: Any) -> None:
        self.name, self.meta = name, meta
        self._view: Optional[Callable[[Ctx], Node]] = None
        self._handlers: Dict[str, Callable[[Ctx, Event], Any]] = {}
        self._actions: List[Dict[str, Any]] = []
        self._sessions: Dict[str, _Session] = {}
        self._backlog: deque = deque()
        self._rid = 0
        self._in = sys.stdin.buffer
        self._out = sys.stdout.buffer

    # -- registration ------------------------------------------------------
    def view(self, fn: Callable[[Ctx], Node]) -> Callable[[Ctx], Node]:
        """Register the function that renders a session's scene."""
        self._view = fn
        return fn

    def on(self, action: str, fn: Optional[Callable[[Ctx, Event], Any]] = None) -> Any:
        """Register a handler: ``app.on("save", fn)`` or as a decorator."""
        if fn is not None:
            self._handlers[action] = fn
            return fn

        def register(f: Callable[[Ctx, Event], Any]) -> Callable[[Ctx, Event], Any]:
            self._handlers[action] = f
            return f

        return register

    def action(self, name: str, description: str, params: Optional[Dict[str, str]] = None,
               fn: Optional[Callable[[Ctx, Event], Any]] = None) -> Any:
        """Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in ``event.payload``."""
        self._actions.append({"name": name, "description": description, "params": params or {}})
        return self.on(name, fn)

    # -- wire ----------------------------------------------------------------
    def _send(self, msg: Dict[str, Any]) -> None:
        self._out.write((json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
        self._out.flush()

    def _read(self) -> Optional[Dict[str, Any]]:
        while True:
            raw = self._in.readline()
            if not raw:
                return None
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if isinstance(msg, dict):
                return msg

    def _ai(self, sid: str, capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._rid += 1
        rid = "r%d" % self._rid
        self._send({"t": "ai.invoke", "rid": rid, "sid": sid, "capability": capability, "input": payload})
        while True:
            msg = self._read()
            if msg is None:
                raise AIError("engine disconnected")
            if msg.get("t") == "ai.result" and msg.get("rid") == rid:
                if msg.get("ok"):
                    return msg.get("data") or {}
                raise AIError(str(msg.get("error") or "capability failed"))
            self._backlog.append(msg)

    def _render(self, sid: str) -> None:
        session = self._sessions.get(sid)
        if session is None or self._view is None:
            return
        root = self._view(Ctx(self, sid, session))
        self._send({"t": "scene", "sid": sid, "root": root.to_json()})

    def _handle(self, msg: Dict[str, Any]) -> bool:
        kind, sid = msg.get("t"), str(msg.get("sid") or "")
        if kind == "open":
            self._sessions[sid] = _Session(msg.get("route") or "/", msg.get("locale") or "en-US")
            self._render(sid)
        elif kind == "route":
            if sid in self._sessions:
                self._sessions[sid].route = msg.get("route") or "/"
                self._render(sid)
        elif kind == "event":
            session = self._sessions.get(sid)
            handler = self._handlers.get(msg.get("name") or "")
            if session is None:
                self._send({"t": "log", "level": "warn", "message": "event for unknown session %s" % sid})
            elif handler is None:
                self._send({"t": "log", "level": "warn", "message": "no handler for action %s" % msg.get("name")})
            else:
                try:
                    handler(Ctx(self, sid, session), Event(msg))
                except Exception as exc:  # report and keep serving other sessions
                    self._send({"t": "error", "sid": sid, "message": "%s: %s" % (type(exc).__name__, exc)})
                else:
                    self._render(sid)
        elif kind == "close":
            self._sessions.pop(sid, None)
        elif kind == "shutdown":
            return False
        return True

    def run(self) -> None:
        """Serve the wire protocol on stdin/stdout until the engine shuts the app down."""
        self._send({"t": "ready", "protocol": PROTOCOL, "sdk": "python", "sdkVersion": __version__,
                    "app": {"name": self.name, "meta": self.meta}, "actions": self._actions})
        while True:
            msg = self._backlog.popleft() if self._backlog else self._read()
            if msg is None or not self._handle(msg):
                break
