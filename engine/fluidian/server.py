"""Engine: application supervisor, session hub and HTTP/SSE server."""
from __future__ import annotations

import hmac
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from . import PROTOCOL_VERSION, __version__
from . import components as C
from .capabilities.registry import REGISTRY
from .config import Config
from .kernel import Kernel, catalog
from .procs import stop_process
from .reflex import review as R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_DIR = os.path.join(ROOT, "runtime")
STATIC_TYPES = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8",
                ".svg": "image/svg+xml", ".json": "application/json; charset=utf-8", ".woff2": "font/woff2", ".png": "image/png",
                ".txt": "text/plain; charset=utf-8", ".map": "application/json"}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; "
       "media-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors %s; base-uri 'none'; form-action 'self'")


def csp(embed_origins: List[str]) -> str:
    """The content security policy; framing is refused unless origins were listed for ``<fluidian-app>``."""
    origins = [o for o in embed_origins if o == "*" or re.match(r"^https?://[\w.\-]+(:\d+)?$", o)]
    return CSP % (" ".join(["'self'"] + origins) if origins else "'none'")


def manifest(app_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Web app manifest: what makes the application installable from the browser on iOS, Android and desktop."""
    from . import colors
    name = str(app_meta.get("name") or "Fluidian")
    meta = app_meta.get("meta") if isinstance(app_meta.get("meta"), dict) else {}
    spec = colors.THEMES.get(str(meta.get("theme") or ""), colors.THEMES[colors.DEFAULT_THEME])
    tokens = {t["name"]: t["value"] for t in colors.preset_tokens(spec)}
    base = "/_fluidian/runtime/pwa/"
    return {"name": name, "short_name": str(meta.get("shortName") or name)[:24], "description": str(meta.get("description") or "%s, built with Fluidian." % name),
            "id": "/", "start_url": "/", "scope": "/", "display": "standalone", "orientation": "any",
            "background_color": tokens["--fl-bg"], "theme_color": str(meta.get("themeColor") or tokens["--fl-brand"]),
            "icons": [{"src": base + "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                      {"src": base + "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                      {"src": base + "maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}]}


def log(*parts: Any) -> None:
    print("[fluidian]", *parts, file=sys.stderr, flush=True)


class Session:
    def __init__(self, route: str, locale: str, viewport: Optional[Dict[str, Any]] = None):
        self.sid = "s" + secrets.token_hex(6)
        self.token = secrets.token_urlsafe(24)
        self.route = route or "/"
        self.locale = locale or "en-US"
        self.viewport = viewport or {}
        self.scene: Optional[Dict[str, Any]] = None
        self.fixes: List[str] = []
        self.signals: deque = deque(maxlen=400)
        self.history: deque = deque(maxlen=60)
        self.created = self.seen = time.time()
        self.streams = 0
        self._queue: deque = deque(maxlen=256)
        self._cond = threading.Condition()
        self._tokens, self._refill = 30.0, time.time()

    def push(self, kind: str, data: Dict[str, Any]) -> None:
        with self._cond:
            if kind == "scene":
                stale = [m for m in self._queue if m[0] == "scene"]
                for m in stale:
                    self._queue.remove(m)
            self._queue.append((kind, data))
            self._cond.notify_all()

    def drain(self, timeout: float) -> List[Any]:
        with self._cond:
            if not self._queue:
                self._cond.wait(timeout)
            items = list(self._queue)
            self._queue.clear()
            return items

    def throttle(self, cost: float = 1.0) -> bool:
        """Token bucket: 30 burst, refilled at 3 per second."""
        now = time.time()
        self._tokens = min(30.0, self._tokens + (now - self._refill) * 3.0)
        self._refill = now
        if self._tokens < cost:
            return False
        self._tokens -= cost
        return True


class AppProcess:
    """Runs the application process and speaks the wire protocol over its stdio."""

    def __init__(self, argv: List[str], cwd: Optional[str], on_message: Callable[[Dict[str, Any]], None],
                 on_exit: Callable[[int], None], trace: bool = False):
        self.argv, self.cwd, self.on_message, self.on_exit, self.trace = argv, cwd, on_message, on_exit, trace
        self.proc: Optional[subprocess.Popen] = None
        self.ready = threading.Event()
        self._lock = threading.Lock()
        self.stopping = False

    def start(self) -> None:
        env = dict(os.environ, FLUIDIAN="1", FLUIDIAN_PROTOCOL=str(PROTOCOL_VERSION), PYTHONUNBUFFERED="1")
        # In a source checkout the bundled SDKs are put on the interpreter search paths, so
        # `fluidian run -- python3 app.py` works before anything has been installed.
        sdks = os.path.join(ROOT, "sdks")
        if os.path.isdir(os.path.join(sdks, "python", "fluidian")):
            # The SDK goes first and the engine's own folder is left out: both packages are called `fluidian`.
            inherited = [p for p in (env.get("PYTHONPATH") or "").split(os.pathsep) if p and os.path.abspath(p) != os.path.join(ROOT, "engine")]
            env["PYTHONPATH"] = os.pathsep.join([os.path.join(sdks, "python")] + inherited)
        if os.path.isdir(os.path.join(sdks, "ruby", "lib")):
            env["RUBYLIB"] = os.pathsep.join(p for p in (env.get("RUBYLIB"), os.path.join(sdks, "ruby", "lib")) if p)
        if os.path.isfile(os.path.join(sdks, "lua", "fluidian.lua")):
            env["LUA_PATH"] = "%s;%s" % (os.path.join(sdks, "lua", "?.lua"), env.get("LUA_PATH") or ";")
        self.ready.clear()
        self.proc = subprocess.Popen(self.argv, cwd=self.cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, bufsize=0)
        threading.Thread(target=self._read_stdout, name="app-stdout", daemon=True).start()
        threading.Thread(target=self._read_stderr, name="app-stderr", daemon=True).start()

    def _read_stdout(self) -> None:
        proc = self.proc
        assert proc is not None and proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            msg = None
            if line.startswith("{"):
                try:
                    msg = json.loads(line)
                except ValueError:
                    msg = None
            if not isinstance(msg, dict) or "t" not in msg:
                log("app:", line[:500])
                continue
            if self.trace:
                log("app →", line[:300])
            if msg["t"] == "ready":
                self.ready.set()
            try:
                self.on_message(msg)
            except Exception as exc:  # never let a bad message kill the reader
                log("error handling app message:", repr(exc))
        code = proc.wait()
        if not self.stopping:
            self.on_exit(code)

    def _read_stderr(self) -> None:
        proc = self.proc
        assert proc is not None and proc.stderr is not None
        for raw in iter(proc.stderr.readline, b""):
            text = raw.decode("utf-8", "replace").rstrip()
            if text:
                log("app:", text[:1000])

    def send(self, msg: Dict[str, Any]) -> bool:
        proc = self.proc
        if proc is None or proc.poll() is not None or proc.stdin is None:
            return False
        data = (json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if self.trace:
            log("app ←", data.decode("utf-8")[:300].rstrip())
        with self._lock:
            try:
                proc.stdin.write(data)
                proc.stdin.flush()
                return True
            except (BrokenPipeError, OSError):
                return False

    def stop(self) -> None:
        self.stopping = True
        proc = self.proc
        if proc is None:
            return
        stop_process(proc, timeout=3.0, polite=lambda: self.send({"t": "shutdown"}))


class Engine:
    def __init__(self, cfg: Config, app_argv: Optional[List[str]] = None, app_cwd: Optional[str] = None,
                 scenes: Optional[Dict[str, Any]] = None, trace: bool = False, kernel: Optional[Kernel] = None):
        self.cfg = cfg
        self.kernel = kernel or Kernel(cfg)
        self.sessions: Dict[str, Session] = {}
        self.lock = threading.Lock()
        self.actions: List[Dict[str, Any]] = []
        self.app_meta: Dict[str, Any] = {"name": "Fluidian"}
        self.scenes = scenes or {}
        self.pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="fluidian-ai")
        self.app: Optional[AppProcess] = None
        self.restarts: deque = deque(maxlen=5)
        self.httpd: Optional[ThreadingHTTPServer] = None
        self._catalog: Optional[bytes] = None
        self.stopped = threading.Event()
        if app_argv:
            self.app = AppProcess(app_argv, app_cwd, self.on_app_message, self.on_app_exit, trace)

    # ----------------------------------------------------------- lifecycle
    def start_app(self, ready_timeout: float = 60.0) -> None:
        if not self.app:
            return
        self.app.start()
        if not self.app.ready.wait(ready_timeout):
            code = self.app.proc.poll() if self.app.proc else None
            self.app.stop()
            raise RuntimeError("the application did not send a `ready` message within %.0fs%s" % (
                ready_timeout, " (it exited with code %s)" % code if code is not None else ""))

    def on_app_exit(self, code: int) -> None:
        log("application exited with code %s" % code)
        for s in list(self.sessions.values()):
            s.push("toast", {"text": "The application stopped (exit code %s). Restarting…" % code, "tone": "danger"})
        now = time.time()
        self.restarts.append(now)
        if len([t for t in self.restarts if now - t < 60]) > 3 or self.stopped.is_set() or not self.app:
            log("application keeps crashing; not restarting")
            return
        time.sleep(0.5 * len(self.restarts))
        try:
            self.app.stopping = False
            self.start_app(30.0)
            for s in list(self.sessions.values()):
                self.app.send({"t": "open", "sid": s.sid, "route": s.route, "locale": s.locale, "viewport": s.viewport})
        except (RuntimeError, OSError) as exc:
            log("restart failed:", exc)

    def stop(self) -> None:
        self.stopped.set()
        if self.app:
            self.app.stop()
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        self.pool.shutdown(wait=False)

    # ------------------------------------------------------------ sessions
    def create_session(self, route: str, locale: str, viewport: Optional[Dict[str, Any]] = None) -> Session:
        s = Session(route, locale or self.cfg.locale, viewport)
        with self.lock:
            self.sessions[s.sid] = s
        self.open_route(s)
        return s

    def open_route(self, s: Session, first: bool = True) -> None:
        if self.app:
            if first:
                self.app.send({"t": "open", "sid": s.sid, "route": s.route, "locale": s.locale, "viewport": s.viewport})
            else:
                self.app.send({"t": "route", "sid": s.sid, "route": s.route})
        else:
            scene = self.scenes.get(s.route) or self.scenes.get("/") or next(iter(self.scenes.values()), None)
            if scene is None:
                scene = {"type": "Page", "props": {"title": "Nothing to show"}, "children": [
                    {"type": "EmptyState", "props": {"title": "No scene", "description": "Start an app with `fluidian run -- <command>`."}}]}
            self.set_scene(s, scene)

    def set_scene(self, s: Session, root: Any) -> None:
        scene, fixes = C.normalize(root, capabilities=set(REGISTRY))
        s.scene, s.fixes = scene, fixes
        s.push("scene", {"root": scene, "route": s.route, "fixes": fixes if self.cfg.dev else []})

    def close_session(self, sid: str) -> None:
        with self.lock:
            s = self.sessions.pop(sid, None)
        if s and self.app:
            self.app.send({"t": "close", "sid": sid})

    def reap(self) -> None:
        now = time.time()
        for s in list(self.sessions.values()):
            if s.streams <= 0 and now - s.seen > self.cfg.session_ttl:
                self.close_session(s.sid)

    # ---------------------------------------------------------- app → engine
    def on_app_message(self, msg: Dict[str, Any]) -> None:
        kind = msg.get("t")
        if kind == "ready":
            if msg.get("protocol") not in (None, PROTOCOL_VERSION):
                log("warning: application speaks protocol %s, engine speaks %s" % (msg.get("protocol"), PROTOCOL_VERSION))
            app = msg.get("app") if isinstance(msg.get("app"), dict) else {}
            self.app_meta = {"name": app.get("name") or "Fluidian", "sdk": msg.get("sdk"), "sdkVersion": msg.get("sdkVersion"),
                             "meta": app.get("meta") or {}}
            self.actions = [a for a in (msg.get("actions") or []) if isinstance(a, dict) and isinstance(a.get("name"), str)]
            return
        if kind == "log":
            log("app[%s]:" % msg.get("level", "info"), msg.get("message"))
            return
        s = self.sessions.get(str(msg.get("sid")))
        if kind == "ai.invoke":
            self.pool.submit(self._app_ai, msg, s)
            return
        if s is None:
            return
        if kind == "scene":
            self.set_scene(s, msg.get("root"))
        elif kind == "toast":
            s.push("toast", {"text": str(msg.get("text", "")), "tone": str(msg.get("tone") or "info")})
        elif kind == "navigate":
            s.route = str(msg.get("route") or "/")
            s.push("navigate", {"route": s.route})
        elif kind == "error":
            log("app error:", msg.get("message"))
            s.push("toast", {"text": str(msg.get("message") if self.cfg.dev else "Something went wrong."), "tone": "danger"})

    def _app_ai(self, msg: Dict[str, Any], s: Optional[Session]) -> None:
        result = self.invoke(str(msg.get("capability")), msg.get("input") if isinstance(msg.get("input"), dict) else {}, s)
        reply: Dict[str, Any] = {"t": "ai.result", "rid": msg.get("rid"), "ok": bool(result.get("ok"))}
        if result.get("ok"):
            reply["data"] = result.get("data")
            reply["provenance"] = result.get("provenance")
        else:
            reply["error"] = (result.get("error") or {}).get("message", "failed")
        if self.app:
            self.app.send(reply)

    # --------------------------------------------------------------- AI
    def invoke(self, capability: str, payload: Dict[str, Any], s: Optional[Session], mode: str = "auto",
               on_partial: Optional[Callable[[Any], None]] = None) -> Dict[str, Any]:
        return self.kernel.invoke(capability, payload, sid=s.sid if s else "", scene=s.scene if s else None, actions=self.actions,
                                  signals=list(s.signals) if s else None, history=list(s.history) if s else None, mode=mode,
                                  locale=s.locale if s else "", on_partial=on_partial)

    def dispatch(self, s: Session, event: Dict[str, Any]) -> None:
        name = str(event.get("name") or "")
        s.seen = time.time()
        if name == "@route":
            s.route = str(event.get("value") or "/")
            self.open_route(s, first=False)
            return
        s.history.append({"action": name, "label": name.replace("_", " "), "target": event.get("target"), "at": time.time()})
        if self.app:
            self.app.send({"t": "event", "sid": s.sid, "name": name, "target": event.get("target"), "value": event.get("value"),
                           "form": event.get("form") if isinstance(event.get("form"), dict) else {}, "payload": event.get("payload")})

    def devtools(self, s: Optional[Session]) -> Dict[str, Any]:
        scene = s.scene if s else None
        return {"version": __version__, "live": self.cfg.live, "app": self.app_meta, "actions": self.actions,
                "sessions": len(self.sessions), "route": s.route if s else "", "stats": C.stats(scene) if scene else {},
                "fixes": s.fixes if s else [], "digest": C.digest(scene, 4000) if scene else "",
                "lint": R.scene_lint(scene, [a["name"] for a in self.actions] or None) if scene else None,
                "ux": R.ux_review(scene) if scene else None, "a11y": R.a11y_audit(scene) if scene else None,
                "ledger": self.kernel.ledger.public(None, 25), "telemetry": self.kernel.telemetry.snapshot(),
                "router": self.kernel.router.table(), "budget": self.kernel.budget.status(s.sid if s else ""),
                "cache": self.kernel.cache.stats(), "signals": len(s.signals) if s else 0}

    def catalog_bytes(self) -> bytes:
        if self._catalog is None:
            self._catalog = json.dumps(catalog(), ensure_ascii=False).encode("utf-8")
        return self._catalog

    # -------------------------------------------------------------- http
    def serve(self, block: bool = True) -> int:
        engine = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            server_version = "Fluidian/" + __version__

            def log_message(self, *args: Any) -> None:
                pass

            # -- helpers ------------------------------------------------
            def _headers(self, status: int, ctype: str, length: Optional[int], extra: Optional[Dict[str, str]] = None) -> None:
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                if length is not None:
                    self.send_header("Content-Length", str(length))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", csp(engine.cfg.embed_origins))
                if not engine.cfg.embed_origins:
                    self.send_header("Cross-Origin-Opener-Policy", "same-origin")
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()

            def _json(self, status: int, payload: Any) -> None:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._headers(status, "application/json; charset=utf-8", len(body), {"Cache-Control": "no-store"})
                self.wfile.write(body)

            def _fail(self, status: int, message: str) -> None:
                self._json(status, {"ok": False, "error": {"code": str(status), "message": message}})

            def _host_ok(self) -> bool:
                host = (self.headers.get("Host") or "").lower()
                name = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
                if engine.cfg.host in ("0.0.0.0", "::") and not engine.cfg.allowed_hosts:
                    return True
                return name in {"localhost", "127.0.0.1", "[::1]", engine.cfg.host.lower()} | {h.lower() for h in engine.cfg.allowed_hosts}

            def _origin_ok(self) -> bool:
                origin = self.headers.get("Origin")
                if not origin or origin == "null":
                    return origin != "null"
                return urlparse(origin).netloc.lower() == (self.headers.get("Host") or "").lower()

            def _session(self, sid: Any, token: Any) -> Optional[Session]:
                s = engine.sessions.get(str(sid))
                if s is None or not isinstance(token, str) or not hmac.compare_digest(s.token, token):
                    return None
                s.seen = time.time()
                return s

            def _body(self, limit: int) -> Optional[Dict[str, Any]]:
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    length = -1
                if length < 0 or length > limit:
                    self._fail(413, "Request body too large.")
                    return None
                try:
                    data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                except (ValueError, UnicodeDecodeError):
                    self._fail(400, "Body must be JSON.")
                    return None
                if not isinstance(data, dict):
                    self._fail(400, "Body must be a JSON object.")
                    return None
                return data

            # -- GET ----------------------------------------------------
            def do_GET(self) -> None:  # noqa: N802
                if not self._host_ok():
                    return self._fail(403, "Host not allowed.")
                url = urlparse(self.path)
                path, query = url.path, parse_qs(url.query)
                if path == "/healthz":
                    health = {"ok": True, "version": __version__, "live": engine.cfg.live,
                              "app": bool(engine.app and engine.app.ready.is_set()) or not engine.app}
                    if os.environ.get("FLUIDIAN_INSTANCE"):   # lets a harness tell the server it started from any other on the same port
                        health["instance"] = os.environ["FLUIDIAN_INSTANCE"][:64]
                    return self._json(200, health)
                if path == "/_fluidian/events":
                    return self._events(query)
                if path == "/_fluidian/capabilities":
                    body = engine.catalog_bytes()
                    self._headers(200, "application/json; charset=utf-8", len(body), {"Cache-Control": "max-age=300"})
                    return self.wfile.write(body) and None
                if path == "/_fluidian/components":
                    return self._json(200, C.export_spec())
                if path == "/_fluidian/devtools":
                    if not engine.cfg.dev:
                        return self._fail(404, "Developer tools are disabled.")
                    s = self._session((query.get("sid") or [""])[0], (query.get("token") or [""])[0])
                    return self._json(200, engine.devtools(s))
                if path.startswith("/_fluidian/runtime/"):
                    return self._static(path[len("/_fluidian/runtime/"):])
                if path == "/favicon.ico" or path == "/favicon.svg":
                    return self._static("logo.svg")
                if path == "/manifest.webmanifest":
                    body = json.dumps(manifest(engine.app_meta), ensure_ascii=False).encode("utf-8")
                    self._headers(200, "application/manifest+json; charset=utf-8", len(body), {"Cache-Control": "max-age=300"})
                    return self.wfile.write(body) and None
                if path == "/sw.js":
                    return self._static("sw.js", {"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})
                if path == "/_fluidian/embed.js":
                    return self._static("embed.js", {"Access-Control-Allow-Origin": "*", "Cross-Origin-Resource-Policy": "cross-origin"})
                if path.startswith("/_fluidian/"):
                    return self._fail(404, "Not found.")
                return self._static("index.html", {"Cache-Control": "no-store"})

            def _static(self, rel: str, extra: Optional[Dict[str, str]] = None) -> None:
                full = os.path.realpath(os.path.join(RUNTIME_DIR, rel))
                ext = os.path.splitext(full)[1].lower()
                if not full.startswith(os.path.realpath(RUNTIME_DIR) + os.sep) or ext not in STATIC_TYPES or not os.path.isfile(full):
                    return self._fail(404, "Not found.")
                with open(full, "rb") as fh:
                    body = fh.read()
                headers = {"Cache-Control": "no-cache" if engine.cfg.dev else "public, max-age=3600"}
                headers.update(extra or {})
                self._headers(200, STATIC_TYPES[ext], len(body), headers)
                self.wfile.write(body)

            def _events(self, query: Dict[str, List[str]]) -> None:
                s = self._session((query.get("sid") or [""])[0], (query.get("token") or [""])[0])
                if s is None:
                    return self._fail(403, "Unknown session.")
                self._headers(200, "text/event-stream; charset=utf-8", None, {"Cache-Control": "no-store", "Connection": "close", "X-Accel-Buffering": "no"})
                self.close_connection = True
                s.streams += 1
                try:
                    if s.scene is not None:
                        s.push("scene", {"root": s.scene, "route": s.route, "fixes": s.fixes if engine.cfg.dev else []})
                    last = time.time()
                    once = (query.get("once") or [""])[0] == "1"
                    while not engine.stopped.is_set():
                        items = s.drain(1.0)
                        for kind, data in items:
                            self.wfile.write(("event: %s\ndata: %s\n\n" % (kind, json.dumps(data, ensure_ascii=False))).encode("utf-8"))
                        if items:
                            self.wfile.flush()
                            last = time.time()
                            if once:
                                break
                        elif time.time() - last > 15:
                            self.wfile.write(b": keep-alive\n\n")
                            self.wfile.flush()
                            last = time.time()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    s.streams -= 1
                    s.seen = time.time()

            # -- POST ---------------------------------------------------
            def do_POST(self) -> None:  # noqa: N802
                if not self._host_ok() or not self._origin_ok():
                    return self._fail(403, "Cross-origin request refused.")
                path = urlparse(self.path).path
                media = path in ("/_fluidian/ai", "/_fluidian/ai/stream")
                body = self._body(engine.cfg.max_media_bytes if media else engine.cfg.max_body_bytes)
                if body is None:
                    return
                if path == "/_fluidian/session":
                    engine.reap()
                    if len(engine.sessions) >= 500:
                        return self._fail(503, "Too many sessions.")
                    s = engine.create_session(str(body.get("route") or "/")[:400], str(body.get("locale") or "")[:20],
                                               body.get("viewport") if isinstance(body.get("viewport"), dict) else None)
                    return self._json(200, {"ok": True, "sid": s.sid, "token": s.token, "app": engine.app_meta, "live": engine.cfg.live,
                                            "dev": engine.cfg.dev, "version": __version__, "actions": engine.actions})
                s = self._session(body.get("sid"), self.headers.get("X-Fluidian-Token"))
                if s is None:
                    return self._fail(403, "Unknown session or bad token.")
                if path == "/_fluidian/event":
                    engine.dispatch(s, body)
                    return self._json(200, {"ok": True})
                if path == "/_fluidian/signals":
                    for e in (body.get("events") or [])[:100]:
                        if isinstance(e, dict):
                            s.signals.append({"t": e.get("t"), "kind": str(e.get("kind"))[:20], "target": str(e.get("target"))[:80],
                                              "meta": str(e.get("meta") or "")[:80]})
                    return self._json(200, {"ok": True})
                if path == "/_fluidian/close":
                    engine.close_session(s.sid)
                    return self._json(200, {"ok": True})
                if media:
                    if not s.throttle():
                        return self._fail(429, "Too many AI requests; slow down.")
                    capability = str(body.get("capability") or "")
                    payload = body.get("input") if isinstance(body.get("input"), dict) else {}
                    mode = body.get("mode") if body.get("mode") in ("auto", "reflex", "reason") else "auto"
                    if path == "/_fluidian/ai":
                        return self._json(200, engine.invoke(capability, payload, s, mode))
                    self._headers(200, "text/event-stream; charset=utf-8", None, {"Cache-Control": "no-store", "Connection": "close"})
                    self.close_connection = True

                    def partial(data: Any) -> None:
                        try:
                            self.wfile.write(("event: partial\ndata: %s\n\n" % json.dumps(data, ensure_ascii=False)).encode("utf-8"))
                            self.wfile.flush()
                        except OSError:
                            pass

                    result = engine.invoke(capability, payload, s, mode, partial)
                    try:
                        self.wfile.write(("event: result\ndata: %s\n\n" % json.dumps(result, ensure_ascii=False)).encode("utf-8"))
                        self.wfile.flush()
                    except OSError:
                        pass
                    return
                self._fail(404, "Not found.")

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True
            request_queue_size = 64

        self.httpd = Server((self.cfg.host, self.cfg.port), Handler)
        self.cfg.port = self.httpd.server_address[1]
        if block:
            try:
                self.httpd.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
            finally:
                self.stop()
        else:
            threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.1}, name="fluidian-http", daemon=True).start()
        return self.cfg.port


def load_scenes(path: str) -> Dict[str, Any]:
    """Load static scenes: a single scene, or ``{"routes": {"/": scene, ...}}``."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and isinstance(data.get("routes"), dict):
        return data["routes"]
    return {"/": data}
