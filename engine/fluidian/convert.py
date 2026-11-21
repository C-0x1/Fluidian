"""Cross-language conversion.

``fluidian convert`` takes an application written with any Fluidian SDK and
writes the same application as a runnable project in any of the other
languages. It works on what an application *serves* rather than on its
source text, which is why every language can be both a source and a target:

1. **Capture.** The source application is started and asked for the scene of
   every route. Routes are discovered by following the links, navigation
   items and ``go`` actions found in the scenes themselves.
2. **Emit.** Each scene is written as builder code for the target SDK, one
   function per route, with the declared actions and a handler for every
   action the scenes bind.
3. **Verify.** The generated project is built and run, the same routes are
   requested, and each scene is compared with the source node for node.

Views, bindings, portable logic (``State``, ``Show``, ``Each``, ``{{ }}``
expressions, ``@`` actions) and AI attachments are data, so they convert
exactly. Handlers written in the source language are code. Three things can
happen to them:

* by default a stub keeps the action's name, description and parameters;
* with ``probe`` each handler is fired once per call site and, when all it
  does is notify or navigate, the same behaviour is emitted and replayed
  against the generated application;
* with ``port`` the source file is translated by the ``dev.port`` capability
  and the translation replaces the deterministic project only if it builds
  and reproduces every captured scene and probe.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import codegen
from . import components as C
from .procs import stop_process

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SDKS = os.path.join(ROOT, "sdks")
LANGS = codegen.LANGS
ALIASES = {"js": "javascript", "node": "javascript", "ts": "typescript", "c#": "csharp", "cs": "csharp", "dotnet": "csharp", "c++": "cpp",
           "cxx": "cpp", "py": "python", "rb": "ruby", "ex": "elixir", "exs": "elixir", "golang": "go", "rs": "rust", "kt": "kotlin"}
SID = "convert"
OPEN = {"locale": "en-US", "viewport": {"w": 1280, "h": 800}}
ROUTE_LIMIT = 200


class ConvertError(Exception):
    """A conversion step failed in a way the user can act on."""


def language(name: str) -> str:
    key = (name or "").strip().lower()
    key = ALIASES.get(key, key)
    if key not in LANGS:
        raise ConvertError("Unknown language %r. Choose from: %s." % (name, ", ".join(LANGS)))
    return key


def languages(spec: str, exclude: Optional[str] = None) -> List[str]:
    """Parse ``--to``: a comma separated list of languages, or ``all``."""
    if not spec or spec.strip().lower() == "all":
        return [name for name in LANGS if name != exclude]
    out: List[str] = []
    for part in spec.split(","):
        if part.strip():
            name = language(part)
            if name not in out:
                out.append(name)
    return out


# --- running applications ----------------------------------------------------
def _which(*names: str) -> Optional[str]:
    from .testkit.conformance import _which as which
    return which(*names)


def sdk_env(base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Environment in which SDKs from this checkout can be imported without installing them."""
    env = dict(base if base is not None else os.environ)
    # The SDK goes first, and the engine's own folder is left out: both packages are called `fluidian`.
    engine = os.path.join(ROOT, "engine")
    inherited = [p for p in (env.get("PYTHONPATH") or "").split(os.pathsep) if p and os.path.abspath(p) != engine]
    env["PYTHONPATH"] = os.pathsep.join([os.path.join(SDKS, "python")] + inherited)
    env["RUBYLIB"] = os.pathsep.join(p for p in (env.get("RUBYLIB"), os.path.join(SDKS, "ruby", "lib")) if p)
    env["LUA_PATH"] = "%s;%s" % (os.path.join(SDKS, "lua", "?.lua"), env.get("LUA_PATH") or ";")
    env.setdefault("GOFLAGS", "-mod=mod")
    env.setdefault("GOTOOLCHAIN", "local")
    env.setdefault("DOTNET_CLI_TELEMETRY_OPTOUT", "1")
    env.setdefault("DOTNET_NOLOGO", "1")
    return env


_TOOL_NAMES = {"python3": ("python3", "python"), "node": ("node", "nodejs"), "lua5.4": ("lua5.4", "lua5.3", "lua", "luajit"),
               "g++": ("g++", "clang++", "c++")}


def resolve(argv: List[str]) -> List[str]:
    """Replace the program name with the installed tool, looking in the toolchain folders ``setup-ubuntu.sh`` uses."""
    if not argv:
        return argv
    names = _TOOL_NAMES.get(argv[0], (argv[0],))
    return [_which(*names) or argv[0]] + list(argv[1:])


def missing_tools(project: Dict[str, Any]) -> List[str]:
    tools = [cmd[0] for cmd in list(project.get("build") or []) + [project.get("run") or []] if cmd]
    return sorted({t for t in tools if not os.path.sep in t and not _which(*_TOOL_NAMES.get(t, (t,)))})


def build_project(project: Dict[str, Any], directory: str, timeout: float = 900.0) -> None:
    env = sdk_env()
    for cmd in project.get("build") or []:
        argv = resolve(cmd) + (["--offline"] if cmd[:2] == ["cargo", "build"] else [])
        try:
            done = subprocess.run(argv, cwd=directory, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ConvertError("build step `%s` could not run: %s" % (" ".join(cmd[:3]), exc))
        if done.returncode != 0:
            raise ConvertError("build step `%s` failed:\n%s" % (" ".join(cmd[:3]), done.stdout.decode("utf-8", "replace")[-2400:]))


def run_argv(project: Dict[str, Any]) -> List[str]:
    run = list(project["run"])
    return resolve(run) + (["--offline"] if run[:2] == ["cargo", "run"] else [])


class Session:
    """A conversation with a running application over the wire protocol."""

    def __init__(self, argv: List[str], cwd: str, env: Optional[Dict[str, str]] = None, startup: float = 180.0,
                 answer: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None):
        from .testkit.conformance import _Proc
        self._proc = _Proc(argv, env or {}, cwd)
        self._answer = answer
        self._n = 0
        try:
            self.ready = self._proc.read(startup)
        except (TimeoutError, EOFError, ValueError) as exc:
            self.close()
            raise ConvertError("the application did not start: %s" % exc)
        if self.ready.get("t") != "ready":
            self.close()
            raise ConvertError("expected a `ready` message first, got `%s`" % self.ready.get("t"))

    def _until_scene(self, timeout: float = 30.0) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
        """Read until the next scene (or error); returns it with the side effects seen on the way."""
        effects: List[Dict[str, Any]] = []
        deadline = time.time() + timeout
        while True:
            try:
                msg = self._proc.read(max(0.5, deadline - time.time()))
            except TimeoutError:
                return None, effects
            except (EOFError, ValueError) as exc:
                raise ConvertError("the application stopped answering: %s" % exc)
            kind = msg.get("t")
            if kind == "scene":
                return msg.get("root"), effects
            if kind == "ai.invoke":
                reply = {"t": "ai.result", "rid": msg.get("rid"), "ok": False, "error": "capabilities are not available during conversion"}
                if self._answer is not None:
                    result = self._answer(str(msg.get("capability")), msg.get("input") if isinstance(msg.get("input"), dict) else {})
                    if result.get("ok"):
                        reply = {"t": "ai.result", "rid": msg.get("rid"), "ok": True, "data": result.get("data")}
                self._proc.send(reply, False)
            elif kind in ("toast", "navigate"):
                effects.append({k: v for k, v in msg.items() if k != "sid"})
            elif kind == "error":
                effects.append({"t": "error"})
                return None, effects

    def open(self, route: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Open a fresh session on ``route``; returns its id and first scene."""
        self._n += 1
        sid = "%s%d" % (SID, self._n)
        self._proc.send(dict(OPEN, t="open", sid=sid, route=route), False)
        scene, _ = self._until_scene()
        return sid, scene

    def scene(self, route: str) -> Optional[Dict[str, Any]]:
        sid, scene = self.open(route)
        self._proc.send({"t": "close", "sid": sid}, False)
        return scene

    def fire(self, route: str, action: str, target: Optional[str], payload: Any, repeat: bool = False) -> Dict[str, Any]:
        """Open a fresh session, deliver one event and report what the application did.

        With ``repeat`` the same event is delivered a second time in the same
        session; a handler whose second answer differs depends on state.
        """
        sid, before = self.open(route)
        event = {"t": "event", "sid": sid, "name": action, "target": target, "value": None, "form": {}, "payload": payload}
        self._proc.send(event, False)
        after, effects = self._until_scene(12.0)
        landed = next((e.get("route") for e in reversed(effects) if e.get("t") == "navigate"), None)
        again: Optional[List[Dict[str, Any]]] = None
        if repeat and after is not None:
            self._proc.send(event, False)
            again = self._until_scene(12.0)[1]
        self._proc.send({"t": "close", "sid": sid}, False)
        return {"effects": effects, "before": before, "after": after, "landed": landed, "again": again}

    def close(self) -> None:
        proc = self._proc.proc
        stop_process(proc, timeout=5.0, polite=lambda: self._proc.send({"t": "shutdown"}, False))
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass


# --- locating the source -----------------------------------------------------
_BY_EXT = {".py": ("python", ["python3"]), ".js": ("javascript", ["node"]), ".cjs": ("javascript", ["node"]), ".mjs": ("javascript", ["node"]),
           ".rb": ("ruby", ["ruby"]), ".php": ("php", ["php"]), ".lua": ("lua", ["lua5.4"]), ".exs": ("elixir", ["elixir"]),
           ".dart": ("dart", ["dart", "run"])}
_BY_FILE = [("app.py", "python"), ("app.js", "javascript"), ("app.ts", "typescript"), ("main.go", "go"), ("Cargo.toml", "rust"),
            ("Main.java", "java"), ("app.kt", "kotlin"), ("Program.cs", "csharp"), ("app.cpp", "cpp"), ("app.rb", "ruby"),
            ("app.php", "php"), ("app.dart", "dart"), ("app.exs", "elixir"), ("app.lua", "lua")]


def read_manifest(directory: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(directory, codegen.MANIFEST)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("run"), list) else None


def locate(target: Optional[str], command: Optional[List[str]] = None) -> Dict[str, Any]:
    """Work out how to start the source application.

    ``target`` is a source file in an interpreted language, a project folder
    (one made by ``fluidian new`` or ``fluidian convert``, or one that follows
    the same layout), or a scene bundle in JSON. ``command`` is an explicit
    start command and wins over detection.
    """
    if command:
        file = target if target and os.path.isfile(target) else next((a for a in command if os.path.isfile(a) and not os.access(a, os.X_OK)), None)
        return {"kind": "command", "argv": list(command), "cwd": os.getcwd(), "build": [], "file": file, "language": None}
    if not target:
        raise ConvertError("Give a source file, a project folder, or a start command after `--`.")
    path = os.path.abspath(target)
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            return {"kind": "bundle", "file": path, "language": None}
        if ext in _BY_EXT:
            lang, argv = _BY_EXT[ext]
            return {"kind": "command", "argv": argv + [path], "cwd": os.path.dirname(path), "build": [], "file": path, "language": lang}
        if os.path.basename(path) in dict(_BY_FILE) or ext in (".go", ".rs", ".java", ".kt", ".cs", ".cpp", ".ts"):
            return locate(os.path.dirname(path))
        raise ConvertError("Cannot tell how to run %s. Pass the start command after `--`, for example: fluidian convert --to go -- ./my-app" % target)
    if os.path.isdir(path):
        manifest = read_manifest(path)
        if manifest:
            return {"kind": "command", "argv": manifest["run"], "cwd": path, "build": manifest.get("build") or [],
                    "file": os.path.join(path, str(manifest.get("main") or "")), "language": manifest.get("language")}
        for name, lang in _BY_FILE:
            if os.path.isfile(os.path.join(path, name)) or (lang == "rust" and os.path.isfile(os.path.join(path, "src", "main.rs"))):
                project = codegen.layout(lang, "", SDKS)
                return {"kind": "command", "argv": project["run"], "cwd": path, "build": project["build"],
                        "file": os.path.join(path, project["main"]), "language": lang}
        raise ConvertError("No application found in %s. Pass the start command after `--`." % target)
    raise ConvertError("%s does not exist." % target)


# --- capture -------------------------------------------------------------------
_GO = re.compile(r"""(?:^|;)\s*@?go\s+['"](/[^'"]*)['"]""")


def find_routes(value: Any, out: Optional[List[str]] = None) -> List[str]:
    """Internal routes referenced anywhere in a scene: nav items, links, breadcrumbs, payloads and ``@go`` actions."""
    out = [] if out is None else out
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("route", "href", "to") and isinstance(item, str) and item.startswith("/") and not item.startswith("//") and "{{" not in item:
                route = item.split("#")[0].split("?")[0] or "/"
                if route not in out:
                    out.append(route)
            else:
                find_routes(item, out)
    elif isinstance(value, list):
        for item in value:
            find_routes(item, out)
    elif isinstance(value, str) and "go" in value and value.lstrip().startswith("@"):
        for route in _GO.findall(value):
            if route not in out:
                out.append(route)
    return out


def bound_actions(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Every server-side action bound in a scene, one entry per call site."""
    found: List[Dict[str, Any]] = []
    for node, _, _ in C.walk(scene):
        for event, binding in (node.get("on") or {}).items():
            name = binding if isinstance(binding, str) else (binding or {}).get("action")
            if name and not str(name).startswith("@"):
                found.append({"action": str(name), "event": event, "target": node.get("id"),
                              "payload": binding.get("payload") if isinstance(binding, dict) else None})
    return found


def _normalise(root: Any) -> Tuple[Dict[str, Any], List[str]]:
    """Canonical form used for emitting and comparing.

    On top of :func:`components.normalize`, a positional argument the source
    left out is given its empty value, because every SDK factory sets it: a
    section built without a title is ``section("")`` in all fourteen languages.
    """
    scene, fixes = C.normalize(root)
    for node, _, _ in C.walk(scene):
        spec = C.SPEC.get(node.get("type"))
        for arg in (spec or {}).get("args") or []:
            if node["props"].get(arg["name"]) is None:
                node["props"][arg["name"]] = "" if arg["kind"] == "str" else 0
    return scene, fixes


def capture(source: Dict[str, Any], routes: Optional[List[str]] = None, follow: bool = True, probe: bool = False,
            limit: int = ROUTE_LIMIT, progress: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
    """Record an application: its identity, declared actions, the scene of every route and, optionally, what its handlers do."""
    say = progress or (lambda text: None)
    if source["kind"] == "bundle":
        return load_bundle(source["file"])
    if source.get("build"):
        say("building the source application")
        build_project({"build": source["build"]}, source["cwd"])
    session = Session(resolve(list(source["argv"])), source["cwd"], sdk_env(), answer=_offline_answer())
    try:
        ready = session.ready
        app = ready.get("app") if isinstance(ready.get("app"), dict) else {}
        bundle: Dict[str, Any] = {"name": str(app.get("name") or "Application"), "meta": app.get("meta") or {}, "sdk": str(ready.get("sdk") or ""),
                                  "language": source.get("language") or str(ready.get("sdk") or ""), "actions": list(ready.get("actions") or []),
                                  "routes": {}, "notes": [], "probes": [], "file": source.get("file")}
        queue = ["/"] + [r for r in (routes or []) if r != "/"]
        while queue and len(bundle["routes"]) < limit:
            route = queue.pop(0)
            if route in bundle["routes"]:
                continue
            raw = session.scene(route)
            if raw is None:
                bundle["notes"].append("%s: the application returned no scene" % route)
                continue
            scene, fixes = _normalise(raw)
            if fixes:
                bundle["notes"].append("%s: %d repair%s while normalising (%s)" % (route, len(fixes), "" if len(fixes) == 1 else "s", fixes[0]))
            bundle["routes"][route] = scene
            say("captured %s (%d nodes)" % (route, C.stats(scene)["nodes"]))
            if follow:
                queue.extend(r for r in find_routes(scene) if r not in bundle["routes"] and r not in queue)
        if queue:
            bundle["notes"].append("stopped after %d routes; %d more were referenced" % (limit, len(queue)))
        if probe:
            bundle["probes"] = _probe(session, bundle, say)
        return bundle
    finally:
        session.close()


def _offline_answer() -> Callable[[str, Dict[str, Any]], Dict[str, Any]]:
    state: Dict[str, Any] = {}

    def answer(capability: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "kernel" not in state:
            from .config import load_config
            from .kernel import Kernel
            state["kernel"] = Kernel(load_config(overrides={"offline": True}))
        try:
            return state["kernel"].invoke(capability, payload, sid=SID, mode="reflex")
        except Exception as exc:  # a capability failing must not end the capture
            return {"ok": False, "error": str(exc)}

    return answer


def _probe(session: Session, bundle: Dict[str, Any], say: Callable[[str], None]) -> List[Dict[str, Any]]:
    """Fire every bound action once per distinct call site and record what the application did."""
    probes: List[Dict[str, Any]] = []
    seen = set()
    for route, scene in bundle["routes"].items():
        for site in bound_actions(scene):
            key = (site["action"], json.dumps(site["payload"], sort_keys=True, ensure_ascii=False))
            if key in seen or len([p for p in probes if p["action"] == site["action"]]) >= 6:
                continue
            seen.add(key)
            got = session.fire(route, site["action"], site["target"], site["payload"], repeat=True)
            before, after = _normalise(got["before"])[0] if got["before"] else None, _normalise(got["after"])[0] if got["after"] else None
            landed = got["landed"]
            expected = bundle["routes"].get(landed) if landed else before
            probes.append({"route": route, "action": site["action"], "target": site["target"], "payload": site["payload"],
                           "effects": got["effects"], "after": after,
                           "pure": after is not None and expected is not None and after == expected and got["again"] == got["effects"]
                           and not any(e.get("t") == "error" for e in got["effects"])})
    say("probed %d handler call%s" % (len(probes), "" if len(probes) == 1 else "s"))
    return probes


def load_bundle(path: str) -> Dict[str, Any]:
    """Read a scene file: one scene, ``{route: scene}``, or a bundle written by ``fluidian convert``."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and isinstance(data.get("routes"), dict) and "type" not in data:
        routes, name, actions = data["routes"], str(data.get("name") or "Application"), list(data.get("actions") or [])
    elif isinstance(data, dict) and "type" in data:
        routes, name, actions = {"/": data}, os.path.splitext(os.path.basename(path))[0].replace("-", " ").replace("_", " ").title(), []
    elif isinstance(data, dict) and data and all(isinstance(k, str) and k.startswith("/") for k in data):
        routes, name, actions = data, "Application", []
    else:
        raise ConvertError("%s is not a scene, a map of routes to scenes, or a conversion bundle." % path)
    bundle: Dict[str, Any] = {"name": name, "meta": {}, "sdk": "", "language": "scene", "actions": actions, "routes": {}, "notes": [],
                              "probes": list(data.get("probes") or []) if isinstance(data, dict) and "routes" in data else [], "file": None}
    for route, raw in routes.items():
        bundle["routes"][route] = _normalise(raw)[0]
    if "/" not in bundle["routes"] and bundle["routes"]:
        bundle["notes"].append("no scene for `/`; %s is served there" % next(iter(bundle["routes"])))
    return bundle


# --- handler plans -------------------------------------------------------------
def plan_handlers(bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Decide what each handler in the generated project does.

    Every action the scenes bind and every declared action gets a handler. A
    handler is ``observed`` when probing showed that it only notifies or
    navigates, with the same shape at every call site; otherwise it is a stub.
    """
    declared = {str(a.get("name")): a for a in bundle["actions"] if isinstance(a, dict) and a.get("name")}
    names: List[str] = []
    for scene in bundle["routes"].values():
        for site in bound_actions(scene):
            if site["action"] not in names:
                names.append(site["action"])
    names += [n for n in declared if n not in names]
    plans = []
    for name in names:
        probes = [p for p in bundle.get("probes") or [] if p["action"] == name]
        steps = _steps(probes)
        plans.append({"action": name, "declared": declared.get(name), "status": "observed" if steps is not None else "stub",
                      "steps": steps if steps is not None else [], "probes": len(probes)})
    return plans


def _steps(probes: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """The statements that reproduce a handler, or ``None`` when probing cannot establish them."""
    if not probes or not all(p.get("pure") for p in probes):
        return None
    shapes = [[e.get("t") for e in p["effects"]] for p in probes]
    if any(shape != shapes[0] for shape in shapes) or not shapes[0]:
        return None
    steps: List[Dict[str, Any]] = []
    for index, kind in enumerate(shapes[0]):
        effects = [p["effects"][index] for p in probes]
        if kind == "toast":
            if any(e.get("text") != effects[0].get("text") or e.get("tone") != effects[0].get("tone") for e in effects):
                return None
            steps.append({"do": "toast", "text": str(effects[0].get("text") or ""), "tone": str(effects[0].get("tone") or "info")})
        elif kind == "navigate":
            targets = [e.get("route") for e in effects]
            key = next((k for k in (probes[0]["payload"] or {}) if isinstance(probes[0]["payload"], dict)
                        and all(isinstance(p["payload"], dict) and p["payload"].get(k) == t for p, t in zip(probes, targets))), None)
            if key is not None:
                steps.append({"do": "navigate_payload", "key": str(key)})
            elif all(t == targets[0] for t in targets):
                steps.append({"do": "navigate", "route": str(targets[0])})
            else:
                return None
        else:
            return None
    return steps


# --- emit ----------------------------------------------------------------------
# Per language: the file, one screen function, one route entry, a handler with and without a declaration, and the
# statements a handler body is made of. `{ev}` is the event parameter, named only when the body reads it.
_T: Dict[str, Dict[str, str]] = {
    "python": {
        "file": 'from fluidian import App, ui\n\napp = App({title})\n\n\n{screens}ROUTES = {{\n{routes}}}\n\n\n@app.view\ndef view(ctx):\n    return ROUTES.get(ctx.route, {home})()\n\n\n{handlers}app.run()\n',
        "screen": 'def {name}():\n    return {scene}\n\n\n', "pad": "    ", "route": '    {route}: {name},\n',
        "on": '@app.on({a})\ndef {f}(ctx, event):\n{body}\n\n\n', "action": '@app.action({a}, {d}, {p})\ndef {f}(ctx, event):\n{body}\n\n\n',
        "toast": '    ctx.toast({m}, {tone})', "navigate": '    ctx.navigate({r})', "navigate_payload": '    ctx.navigate(event.payload[{k}])',
        "comment": '    # {text}', "case": "snake"},
    "javascript": {
        "file": 'const {{ App, ui }} = require("fluidian");\n\nconst app = new App({title});\n\n{screens}const routes = {{\n{routes}}};\n\napp.view((ctx) => (routes[ctx.route] || {home})());\n\n{handlers}app.run();\n',
        "screen": 'const {name} = () =>\n  {scene};\n\n', "pad": "  ", "route": '  {route}: {name},\n',
        "on": 'app.on({a}, (ctx, event) => {{\n{body}\n}});\n\n', "action": 'app.action({a}, {d}, {p}, (ctx, event) => {{\n{body}\n}});\n\n',
        "toast": '  ctx.toast({m}, {tone});', "navigate": '  ctx.navigate({r});', "navigate_payload": '  ctx.navigate(event.payload[{k}]);',
        "comment": '  // {text}', "case": "camel"},
    "typescript": {
        "file": 'import {{ App, Node, ui }} from "fluidian";\n\nconst app = new App({title});\n\n{screens}const routes: {{ [route: string]: () => Node }} = {{\n{routes}}};\n\napp.view((ctx) => (routes[ctx.route] || {home})());\n\n{handlers}app.run();\n',
        "screen": 'const {name} = (): Node =>\n  {scene};\n\n', "pad": "  ", "route": '  {route}: {name},\n',
        "on": 'app.on({a}, (ctx, event) => {{\n{body}\n}});\n\n', "action": 'app.action({a}, {d}, {p}, (ctx, event) => {{\n{body}\n}});\n\n',
        "toast": '  ctx.toast({m}, {tone});', "navigate": '  ctx.navigate({r});', "navigate_payload": '  ctx.navigate(event.payload[{k}]);',
        "comment": '  // {text}', "case": "camel"},
    "go": {
        "file": 'package main\n\nimport fl "github.com/fluidian/fluidian/sdks/go"\n\n{screens}var routes = map[string]func() *fl.Node{{\n{routes}}}\n\nfunc main() {{\n\tapp := fl.NewApp({title})\n\tapp.View(func(ctx *fl.Ctx) *fl.Node {{\n\t\tif screen, ok := routes[ctx.Route()]; ok {{\n\t\t\treturn screen()\n\t\t}}\n\t\treturn {home}()\n\t}})\n{handlers}\tapp.Run()\n}}\n',
        "screen": 'func {name}() *fl.Node {{\n\treturn {scene}\n}}\n\n', "pad": "\t", "route": '\t{route}: {name},\n',
        "on": '\tapp.On({a}, func(ctx *fl.Ctx, ev fl.Event) {{\n{body}\n\t}})\n', "action": '\tapp.Action({a}, {d}, {p}, func(ctx *fl.Ctx, ev fl.Event) {{\n{body}\n\t}})\n',
        "toast": '\t\tctx.Toast({m}, {tone})', "navigate": '\t\tctx.Navigate({r})',
        "navigate_payload": '\t\tif payload, ok := ev.Payload.(fl.M); ok {{\n\t\t\tif route, ok := payload[{k}].(string); ok {{\n\t\t\t\tctx.Navigate(route)\n\t\t\t}}\n\t\t}}',
        "comment": '\t\t// {text}', "case": "camel"},
    "rust": {
        "file": '#![allow(unused_imports)]\nuse fluidian::{{jarr, jobj, ui, App, Json, Node}};\n\n{screens}fn main() {{\n    let mut app = App::new({title});\n    app.view(|ctx| match ctx.route() {{\n{routes}        _ => {home}(),\n    }});\n{handlers}    app.run();\n}}\n',
        "screen": 'fn {name}() -> Node {{\n    {scene}\n}}\n\n', "pad": "    ", "route": '        {route} => {name}(),\n',
        "on": '    app.on({a}, |ctx, {ev}| {{\n{body}\n        Ok(())\n    }});\n', "action": '    app.action({a}, {d}, {p}, |ctx, {ev}| {{\n{body}\n        Ok(())\n    }});\n',
        "toast": '        ctx.toast({m}, {tone});', "navigate": '        ctx.navigate({r});',
        "navigate_payload": '        let route = ev.payload.get({k}).to_string();\n        ctx.navigate(&route);',
        "comment": '        // {text}', "case": "snake", "ev": "ev", "noev": "_ev"},
    "java": {
        "file": 'import dev.fluidian.*;\n\npublic class Main {{\n{screens}    public static void main(String[] args) {{\n        App app = new App({title});\n        app.view(ctx -> {{\n            switch (ctx.route()) {{\n{routes}                default: return {home}();\n            }}\n        }});\n{handlers}        app.run();\n    }}\n}}\n',
        "screen": '    static Node {name}() {{\n        return {scene};\n    }}\n\n', "pad": "        ", "route": '                case {route}: return {name}();\n',
        "on": '        app.on({a}, (ctx, ev) -> {{\n{body}\n        }});\n', "action": '        app.action({a}, {d}, {p}, (ctx, ev) -> {{\n{body}\n        }});\n',
        "toast": '            ctx.toast({m}, {tone});', "navigate": '            ctx.navigate({r});',
        "navigate_payload": '            ctx.navigate(String.valueOf(ev.payloadMap().get({k})));',
        "comment": '            // {text}', "case": "camel"},
    "kotlin": {
        "file": 'import dev.fluidian.*\n\n{screens}fun main() {{\n    val app = App({title})\n    app.view {{ ctx ->\n        when (ctx.route) {{\n{routes}            else -> {home}()\n        }}\n    }}\n{handlers}    app.run()\n}}\n',
        "screen": 'fun {name}(): Node =\n    {scene}\n\n', "pad": "    ", "route": '            {route} -> {name}()\n',
        "on": '    app.on({a}) {{ ctx, {ev} ->\n{body}\n    }}\n', "action": '    app.action({a}, {d}, {p}) {{ ctx, {ev} ->\n{body}\n    }}\n',
        "toast": '        ctx.toast({m}, {tone})', "navigate": '        ctx.navigate({r})',
        "navigate_payload": '        ctx.navigate(ev.payloadMap[{k}].toString())',
        "comment": '        // {text}', "case": "camel", "ev": "ev", "noev": "_"},
    "csharp": {
        "file": 'using Fluidian;\n\nvar app = new App({title});\n\n{screens}app.View(ctx => ctx.Route switch\n{{\n{routes}    _ => {home}(),\n}});\n\n{handlers}app.Run();\n',
        "screen": 'Node {name}() =>\n    {scene};\n\n', "pad": "    ", "route": '    {route} => {name}(),\n',
        "on": 'app.On({a}, (ctx, ev) =>\n{{\n{body}\n}});\n\n', "action": 'app.Action({a}, {d}, {p}, (ctx, ev) =>\n{{\n{body}\n}});\n\n',
        "toast": '    ctx.Toast({m}, {tone});', "navigate": '    ctx.Navigate({r});',
        "navigate_payload": '    if (ev.Payload is Dictionary<string, object?> payload && payload.TryGetValue({k}, out var route) && route is string target)\n    {{\n        ctx.Navigate(target);\n    }}',
        "comment": '    // {text}', "case": "pascal"},
    "cpp": {
        "file": '#include <fluidian/fluidian.hpp>\n\nusing namespace fluidian;\n\n{screens}int main() {{\n  App app({title});\n  app.view([](Ctx& ctx) {{\n    const std::string& route = ctx.route();\n{routes}    return {home}();\n  }});\n{handlers}  app.run();\n  return 0;\n}}\n',
        "screen": 'static Node {name}() {{\n  return {scene};\n}}\n\n', "pad": "  ", "route": '    if (route == {route}) return {name}();\n',
        "on": '  app.on({a}, [](Ctx& ctx, const Event&{ev}) {{\n{body}\n  }});\n', "action": '  app.action({a}, {d}, {p}, [](Ctx& ctx, const Event&{ev}) {{\n{body}\n  }});\n',
        "toast": '    ctx.toast({m}, {tone});', "navigate": '    ctx.navigate({r});', "navigate_payload": '    ctx.navigate(ev.payload.get({k}).str());',
        "comment": '    // {text}', "case": "camel", "ev": " ev", "noev": ""},
    "ruby": {
        "file": 'require "fluidian"\n\nUI = Fluidian::UI\napp = Fluidian::App.new({title})\n\n{screens}routes = {{\n{routes}}}\n\napp.view {{ |ctx| (routes[ctx.route] || {home}).call }}\n\n{handlers}app.run\n',
        "screen": '{name} = lambda do\n  {scene}\nend\n\n', "pad": "  ", "route": '  {route} => {name},\n',
        "on": 'app.on({a}) do |ctx, event|\n{body}\nend\n\n', "action": 'app.action({a}, {d}, {p}) do |ctx, event|\n{body}\nend\n\n',
        "toast": '  ctx.toast({m}, {tone})', "navigate": '  ctx.navigate({r})', "navigate_payload": '  ctx.navigate(event.payload[{k}])',
        "comment": '  # {text}', "case": "snake"},
    "php": {
        "file": "<?php\nrequire __DIR__ . '/vendor/autoload.php';\n\nuse Fluidian\\App;\nuse Fluidian\\UI;\n\n$app = new App({title});\n\n{screens}$routes = [\n{routes}];\n\n$app->view(fn($ctx) => ($routes[$ctx->route()] ?? '{home}')());\n\n{handlers}$app->run();\n",
        "screen": 'function {name}()\n{{\n    return {scene};\n}}\n\n', "pad": "    ", "route": "    {route} => '{name}',\n",
        "on": '$app->on({a}, function ($ctx, $event) {{\n{body}\n}});\n\n', "action": '$app->action({a}, {d}, {p}, function ($ctx, $event) {{\n{body}\n}});\n\n',
        "toast": '    $ctx->toast({m}, {tone});', "navigate": '    $ctx->navigate({r});', "navigate_payload": '    $ctx->navigate($event->payload[{k}]);',
        "comment": '    // {text}', "case": "snake"},
    "dart": {
        "file": "import 'package:fluidian/fluidian.dart';\n\n{screens}final routes = <String, Node Function()>{{\n{routes}}};\n\nvoid main() {{\n  final app = App({title});\n  app.view((ctx) => (routes[ctx.route] ?? {home})());\n{handlers}  app.run();\n}}\n",
        "screen": 'Node {name}() =>\n    {scene};\n\n', "pad": "    ", "route": '  {route}: {name},\n',
        "on": '  app.on({a}, (ctx, event) {{\n{body}\n  }});\n', "action": '  app.action({a}, {d}, {p}, (ctx, event) {{\n{body}\n  }});\n',
        "toast": '    ctx.toast({m}, {tone});', "navigate": '    ctx.navigate({r});',
        "navigate_payload": '    ctx.navigate((event.payload as Map<String, Object?>)[{k}] as String);',
        "comment": '    // {text}', "case": "camel"},
    "elixir": {
        "file": 'alias Fluidian.{{App, Ctx}}\n\ndefmodule Screens do\n  alias Fluidian.{{Node, UI}}\n\n{screens}end\n\nApp.new({title})\n|> App.view(fn ctx ->\n  case ctx.route do\n{routes}    _ -> Screens.{home}()\n  end\nend)\n{handlers}|> App.run()\n',
        "screen": '  def {name} do\n    {scene}\n  end\n\n', "pad": "    ", "route": '    {route} -> Screens.{name}()\n',
        "on": '|> App.on({a}, fn ctx, {ev} ->\n{body}\nend)\n', "action": '|> App.action({a}, {d}, {p}, fn ctx, {ev} ->\n{body}\nend)\n',
        "toast": '  |> Ctx.toast({m}, {tone})', "navigate": '  |> Ctx.navigate({r})', "navigate_payload": '  |> Ctx.navigate(event.payload[{k}])',
        "comment": '  # {text}', "case": "snake", "ev": "event", "noev": "_event", "lead": "  ctx"},
    "lua": {
        "file": 'local fl = require("fluidian")\nlocal ui = fl.ui\n\nlocal app = fl.App({title})\nlocal screens = {{}}\n\n{screens}local routes = {{\n{routes}}}\n\napp:view(function(ctx)\n  return (routes[ctx.route] or {home})()\nend)\n\n{handlers}app:run()\n',
        "screen": 'function {name}()\n  return {scene}\nend\n\n', "pad": "  ", "route": '  [{route}] = {name},\n',
        "on": 'app:on({a}, function(ctx, event)\n{body}\nend)\n\n', "action": 'app:action({a}, {d}, {p}, function(ctx, event)\n{body}\nend)\n\n',
        "toast": '  ctx:toast({m}, {tone})', "navigate": '  ctx:navigate({r})', "navigate_payload": '  ctx:navigate(event.payload[{k}])',
        "comment": '  -- {text}', "case": "snake", "prefix": "screens."},
}


def _ident(route: str, used: List[str]) -> str:
    base = re.sub(r"[^0-9a-zA-Z]+", "_", route).strip("_").lower() or "home"
    if base[0].isdigit():
        base = "page_" + base
    name, n = base, 2
    while name in used:
        name, n = "%s_%d" % (base, n), n + 1
    used.append(name)
    return name


def _cased(snake: str, case: str) -> str:
    return {"snake": snake, "camel": codegen.camel(snake), "pascal": codegen.pascal(snake)}[case]


def emit(bundle: Dict[str, Any], lang: str, plans: Optional[List[Dict[str, Any]]] = None) -> str:
    """The whole application in ``lang``: one function per route, a router, and a handler per action."""
    t, e = _T[lang], codegen.EMITTERS[lang]
    plans = plan_handlers(bundle) if plans is None else plans
    routes = dict(bundle["routes"])
    if not routes:
        raise ConvertError("nothing to convert: no scene was captured")
    first = "/" if "/" in routes else next(iter(routes))
    used: List[str] = []
    names = {route: t.get("prefix", "") + _cased(_ident(route, used) + "_screen", t["case"]) for route in routes}
    screens = "".join(t["screen"].format(name=names[route], scene=e.node(scene, t["pad"])) for route, scene in routes.items())
    table = "".join(t["route"].format(route=e.s(route), name=names[route]) for route in routes)
    handlers, taken = "", []
    for plan in plans:
        uses_event = any(step["do"] == "navigate_payload" for step in plan["steps"])
        lines = [t.get("lead")] if t.get("lead") else []
        if plan["status"] == "stub":
            label = plan["action"].replace("_", " ").strip().capitalize() or "Action"
            lines.insert(0, t["comment"].format(text="Handler bodies are application code: write this one for your %s backend." % codegen.TITLES[lang]))
            lines.append(t["toast"].format(m=e.s("%s: the handler is not ported yet" % label), tone=e.s("warning")))
        for step in plan["steps"]:
            if step["do"] == "toast":
                lines.append(t["toast"].format(m=e.s(step["text"]), tone=e.s(step["tone"])))
            elif step["do"] == "navigate":
                lines.append(t["navigate"].format(r=e.s(step["route"])))
            else:
                lines.append(t["navigate_payload"].format(k=e.s(step["key"])))
        fn = "on_" + (re.sub(r"\W+", "_", plan["action"]).strip("_") or "action")
        while fn in taken:
            fn += "_"
        taken.append(fn)
        slots = {"a": e.s(plan["action"]), "f": fn, "body": "\n".join(lines), "ev": t.get("ev", "") if uses_event else t.get("noev", "")}
        if plan["declared"]:
            params = plan["declared"].get("params") if isinstance(plan["declared"].get("params"), dict) else {}
            handlers += t["action"].format(d=e.s(str(plan["declared"].get("description") or "")), p=e.lit(params), **slots)
        else:
            handlers += t["on"].format(**slots)
    return t["file"].format(title=e.s(bundle["name"]), screens=screens, routes=table, home=names[first], handlers=handlers)


# --- verify --------------------------------------------------------------------
def _diff(a: Any, b: Any) -> str:
    from .testkit.conformance import _first_diff
    return _first_diff(a, b)


def verify(bundle: Dict[str, Any], project: Dict[str, Any], directory: str, build: bool = True) -> Dict[str, Any]:
    """Build and run a generated project; compare every route's scene, and every probe, with the source."""
    started = time.time()
    absent = missing_tools(project)
    if absent:
        return {"status": "skipped", "detail": "toolchain not installed: " + ", ".join(absent), "seconds": 0.0, "routes": 0, "probes": 0}
    try:
        if build:
            build_project(project, directory)
        session = Session(run_argv(project), directory, sdk_env())
    except ConvertError as exc:
        return {"status": "failed", "detail": str(exc), "seconds": time.time() - started, "routes": 0, "probes": 0}
    checked = replayed = 0
    try:
        ready_actions = [a for a in session.ready.get("actions") or [] if isinstance(a, dict)]
        want_actions = [a for a in bundle["actions"] if isinstance(a, dict)]
        if sorted(json.dumps(a, sort_keys=True) for a in ready_actions) != sorted(json.dumps(a, sort_keys=True) for a in want_actions):
            return {"status": "failed", "detail": "declared actions differ from the source", "seconds": time.time() - started, "routes": 0, "probes": 0}
        for route, want in bundle["routes"].items():
            raw = session.scene(route)
            if raw is None:
                return {"status": "failed", "detail": "%s: no scene returned" % route, "seconds": time.time() - started, "routes": checked, "probes": 0}
            diff = _diff(want, _normalise(raw)[0])
            if diff:
                return {"status": "failed", "detail": "%s differs from the source at %s" % (route, diff), "seconds": time.time() - started,
                        "routes": checked, "probes": 0}
            checked += 1
        for probe in bundle.get("probes") or []:
            if not probe.get("pure"):
                continue
            got = session.fire(probe["route"], probe["action"], probe.get("target"), probe.get("payload"))
            after = _normalise(got["after"])[0] if got["after"] else None
            if got["effects"] != probe["effects"] or _diff(probe["after"], after):
                return {"status": "failed", "detail": "handler `%s` behaves differently on %s" % (probe["action"], probe["route"]),
                        "seconds": time.time() - started, "routes": checked, "probes": replayed}
            replayed += 1
    except ConvertError as exc:
        return {"status": "failed", "detail": str(exc), "seconds": time.time() - started, "routes": checked, "probes": replayed}
    finally:
        session.close()
    detail = "%d route%s identical to the source" % (checked, "" if checked == 1 else "s")
    if replayed:
        detail += ", %d handler call%s replayed" % (replayed, "" if replayed == 1 else "s")
    return {"status": "verified", "detail": detail, "seconds": time.time() - started, "routes": checked, "probes": replayed}


# --- model-backed porting --------------------------------------------------------
def port_with_model(bundle: Dict[str, Any], lang: str, invoke: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> Optional[str]:
    """Ask ``dev.port`` for a translation of the source file. Returns code, or ``None`` when there is nothing usable."""
    path = bundle.get("file")
    source_lang = bundle.get("language")
    if not path or not os.path.isfile(path) or source_lang not in LANGS:
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        source = fh.read()
    result = invoke("dev.port", {"source": source, "from": source_lang, "to": lang})
    if not result.get("ok") or (result.get("provenance") or {}).get("provider") in (None, "", "reflex"):
        return None  # the offline path returns a skeleton, never a translation
    code = str((result.get("data") or {}).get("code") or "").strip()
    fenced = re.match(r"^```[\w+#-]*\n(.*)\n```$", code, re.S)
    return (fenced.group(1) if fenced else code) + "\n" if code else None


# --- the whole pipeline ----------------------------------------------------------
def write_bundle(bundle: Dict[str, Any], path: str) -> None:
    data = {"name": bundle["name"], "source": {"language": bundle.get("language"), "sdk": bundle.get("sdk")}, "actions": bundle["actions"],
            "routes": bundle["routes"], "probes": bundle.get("probes") or []}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write("\n")


def convert(bundle: Dict[str, Any], targets: List[str], out: str, check: bool = True, single: bool = False,
            port: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
            progress: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Write one project per target language under ``out`` and verify each. Returns one report per language."""
    say = progress or (lambda text: None)
    plans = plan_handlers(bundle)
    reports: List[Dict[str, Any]] = []
    extra = {"name": bundle["name"], "convertedFrom": bundle.get("language") or bundle.get("sdk") or "scene", "routes": list(bundle["routes"])}
    for lang in targets:
        directory = out if single else os.path.join(out, lang)
        os.makedirs(directory, exist_ok=True)
        report: Dict[str, Any] = {"language": lang, "directory": directory, "handlers": {"observed": sum(p["status"] == "observed" for p in plans),
                                                                                         "stub": sum(p["status"] == "stub" for p in plans)},
                                  "ported": False}
        project = codegen.write_project(lang, directory, emit(bundle, lang, plans), SDKS, extra)
        report.update(files=project["files"], build=project["build"], run=project["run"], main=project["main"])
        if check:
            say("%s: building and comparing" % codegen.TITLES[lang])
            report["check"] = verify(bundle, project, directory)
        else:
            report["check"] = {"status": "unchecked", "detail": "verification was turned off", "seconds": 0.0, "routes": 0, "probes": 0}
        if port is not None and report["handlers"]["stub"] and report["check"]["status"] in ("verified", "unchecked"):
            report["port"] = _try_port(bundle, lang, directory, project, port, say)
            report["ported"] = report["port"]["status"] == "accepted"
        reports.append(report)
    return reports


def _try_port(bundle: Dict[str, Any], lang: str, directory: str, project: Dict[str, Any],
              port: Callable[[str, Dict[str, Any]], Dict[str, Any]], say: Callable[[str], None]) -> Dict[str, Any]:
    """Replace the deterministic main file with a model translation if, and only if, it verifies."""
    say("%s: porting handlers with dev.port" % codegen.TITLES[lang])
    code = port_with_model(bundle, lang, port)
    if not code:
        return {"status": "unavailable", "detail": "no translation: this needs a source file and a configured model"}
    main = os.path.join(directory, project["main"])
    with open(main, "r", encoding="utf-8") as fh:
        deterministic = fh.read()
    ported = codegen.layout(lang, code, SDKS)["files"][project["main"]]
    with open(main, "w", encoding="utf-8") as fh:
        fh.write(ported)
    result = verify(bundle, project, directory)

    def keep(name: str, text: str) -> None:  # the .txt suffix keeps the file out of the build
        with open(os.path.join(directory, name + ".txt"), "w", encoding="utf-8") as handle:
            handle.write(text)

    if result["status"] == "verified":
        keep("deterministic" + os.path.splitext(main)[1], deterministic)
        return {"status": "accepted", "detail": "translation builds and reproduces the source: " + result["detail"]}
    with open(main, "w", encoding="utf-8") as fh:
        fh.write(deterministic)
    keep("ported.rejected" + os.path.splitext(main)[1], ported)
    if not missing_tools(project):
        build_project(project, directory)
    return {"status": "rejected", "detail": "translation kept beside the project for review; it did not verify: " + result["detail"][:300]}
