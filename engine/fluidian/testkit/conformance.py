"""SDK conformance suite.

Every SDK ships the same conformance application.  The suite drives each one
through an identical scripted session over the wire protocol and compares the
normalised transcript with the golden transcript.  Passing means the SDK
builds the same scenes, routes events, isolates sessions, handles Unicode,
performs blocking AI calls with interleaved messages, and reports errors
exactly like the reference implementation.
"""
from __future__ import annotations

import glob
import json
import os
import queue
import shutil
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from .. import components as C
from ..procs import stop_process
from ..codegen import LANGS

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
GOLDEN = os.path.join(ROOT, "spec", "conformance", "golden.json")
BUILD = os.path.join(ROOT, ".fluidian", "build")


def _ev(sid: str, name: str, **kw: Any) -> Dict[str, Any]:
    msg = {"t": "event", "sid": sid, "name": name, "target": kw.pop("target", None), "value": None, "form": {}, "payload": None}
    msg.update(kw)
    return msg


def script() -> List[Tuple[Any, int, bool]]:
    """(message, number of replies to wait for, send ASCII-escaped)."""
    summary = {"title": "Summary ✓", "body": "Short.", "bullets": [], "confidence": 0.9, "tone": "ai"}
    return [
        ({"t": "open", "sid": "s1", "route": "/", "locale": "en-US", "viewport": {"w": 1280, "h": 800}}, 1, False),
        (_ev("s1", "increment", target="inc"), 1, False),
        (_ev("s1", "increment", target="inc"), 1, False),
        ({"t": "open", "sid": "s2", "route": "/two", "locale": "fr-FR", "viewport": {"w": 390, "h": 844}}, 1, False),
        (_ev("s1", "set_name", value='Ada "Lovelace" \\ ✓ 日本語 🚀'), 1, False),
        (_ev("s2", "set_name", value="Zoë\t🚀 naïve"), 1, True),
        (_ev("s1", "submit", form={"email": "ada@example.com", "plan": "pro", "seats": 3, "terms": True, "ratio": 0.25,
                                    "tags": ["a", "b"], "note": None}), 2, False),
        (_ev("s1", "ask_ai"), 1, False),
        (_ev("s2", "increment"), 0, False),
        ({"t": "ai.result", "rid": "@rid", "ok": True, "data": summary}, 2, False),
        (_ev("s1", "fail_ai"), 1, False),
        ({"t": "ai.result", "rid": "@rid", "ok": False, "error": "budget exceeded"}, 2, False),
        (_ev("s1", "go", payload={"route": "/details"}), 2, False),
        ({"t": "route", "sid": "s1", "route": "/back"}, 1, False),
        (_ev("s1", "add_item", payload={"title": "Milk"}), 1, False),
        (_ev("s1", "unknown_action"), 1, False),
        (_ev("s1", "boom"), 1, False),
        ({"t": "close", "sid": "s2"}, 0, False),
        (_ev("s2", "increment"), 1, False),
        (_ev("s1", "increment"), 1, False),
        ({"t": "shutdown"}, 0, False),
    ]


def canonical(msg: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce a message to what every SDK must agree on."""
    kind = msg.get("t")
    if kind == "ready":
        return {"t": "ready", "protocol": msg.get("protocol"), "name": (msg.get("app") or {}).get("name"),
                "actions": [{"name": a.get("name"), "description": a.get("description"), "params": a.get("params") or {}}
                            for a in msg.get("actions") or []]}
    if kind == "scene":
        return {"t": "scene", "sid": msg.get("sid"), "root": C.normalize(msg.get("root"))[0]}
    if kind == "log":
        return {"t": "log", "level": msg.get("level")}
    if kind == "error":
        return {"t": "error", "sid": msg.get("sid"), "boom": "boom" in str(msg.get("message"))}
    if kind == "ai.invoke":
        return {"t": "ai.invoke", "sid": msg.get("sid"), "capability": msg.get("capability"), "input": msg.get("input") or {}}
    if kind == "toast":
        return {"t": "toast", "sid": msg.get("sid"), "text": msg.get("text"), "tone": msg.get("tone") or "info"}
    if kind == "navigate":
        return {"t": "navigate", "sid": msg.get("sid"), "route": msg.get("route")}
    return msg


def _which(*names: str) -> Optional[str]:
    extra = glob.glob(os.path.expanduser("~/.fluidian/toolchains/*/bin")) + [os.path.expanduser("~/.dotnet"), os.path.expanduser("~/.cargo/bin"),
                                                                              "/usr/local/go/bin", os.path.expanduser("~/go/bin")]
    path = os.pathsep.join([os.environ.get("PATH", "")] + extra)
    for name in names:
        hit = shutil.which(name, path=path)
        if hit:
            return hit
    return None


def toolchain(lang: str, target: str = "conformance") -> Dict[str, Any]:
    """Resolve build and run commands for a language; ``missing`` lists absent tools."""
    sdk = os.path.join(ROOT, "sdks", lang)
    out = os.path.join(BUILD, lang)
    env: Dict[str, str] = {}
    build: List[List[str]] = []
    cwd = ROOT
    need: Dict[str, Optional[str]] = {}
    if lang == "python":
        need = {"python3": _which("python3", "python")}
        run = [need["python3"], os.path.join(sdk, "conformance.py")]
        env["PYTHONPATH"] = sdk
    elif lang == "javascript":
        need = {"node": _which("node", "nodejs")}
        run = [need["node"], os.path.join(sdk, "conformance.js")]
    elif lang == "typescript":
        need = {"node": _which("node", "nodejs"), "tsc": _which("tsc")}
        build = [[need["tsc"], "-p", sdk, "--outDir", out]]
        run = [need["node"], os.path.join(out, "conformance.js")]
    elif lang == "go":
        need = {"go": _which("go")}
        build = [[need["go"], "build", "-o", os.path.join(out, "conformance"), "./cmd/conformance"]]
        cwd = sdk
        env.update(GOTOOLCHAIN="local", GOFLAGS="-mod=mod", GOCACHE=os.path.join(BUILD, "gocache"), GOPROXY="off")
        run = [os.path.join(out, "conformance")]
    elif lang == "rust":
        need = {"cargo": _which("cargo")}
        build = [[need["cargo"], "build", "--quiet", "--offline", "--example", "conformance", "--target-dir", out]]
        cwd = sdk
        run = [os.path.join(out, "debug", "examples", "conformance")]
    elif lang == "java":
        need = {"javac": _which("javac"), "java": _which("java")}
        sources = sorted(glob.glob(os.path.join(sdk, "src", "**", "*.java"), recursive=True))
        build = [[need["javac"], "-encoding", "UTF-8", "-nowarn", "-d", out] + sources]
        run = [need["java"], "-Dfile.encoding=UTF-8", "-cp", out, "dev.fluidian.examples.Conformance"]
    elif lang == "kotlin":
        need = {"kotlinc": _which("kotlinc"), "java": _which("java")}
        sources = sorted(glob.glob(os.path.join(sdk, "src", "**", "*.kt"), recursive=True))
        sources = [s for s in sources if not s.endswith("Quickstart.kt")]
        build = [[need["kotlinc"]] + sources + ["-include-runtime", "-nowarn", "-d", os.path.join(out, "conformance.jar")]]
        run = [need["java"], "-Dfile.encoding=UTF-8", "-cp", os.path.join(out, "conformance.jar"), "dev.fluidian.examples.ConformanceKt"]
    elif lang == "csharp":
        need = {"dotnet": _which("dotnet")}
        build = [[need["dotnet"], "build", os.path.join(sdk, "examples", "Conformance"), "-c", "Release", "-o", out, "--nologo", "-v", "q",
                  "-p:UseAppHost=false"]]
        env.update(DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1")
        run = [need["dotnet"], os.path.join(out, "Conformance.dll")]
    elif lang == "cpp":
        need = {"g++": _which("g++", "clang++", "c++")}
        build = [[need["g++"], "-std=c++17", "-O1", "-I" + os.path.join(sdk, "include"), os.path.join(sdk, "examples", "conformance.cpp"),
                  "-o", os.path.join(out, "conformance")]]
        run = [os.path.join(out, "conformance")]
    elif lang == "ruby":
        need = {"ruby": _which("ruby")}
        run = [need["ruby"], "-I" + os.path.join(sdk, "lib"), "-I" + sdk, os.path.join(sdk, "conformance.rb")]
    elif lang == "php":
        need = {"php": _which("php")}
        run = [need["php"], os.path.join(sdk, "conformance.php")]
    elif lang == "dart":
        need = {"dart": _which("dart")}
        run = [need["dart"], "run", os.path.join(sdk, "bin", "conformance.dart")]
        env["PUB_HOSTED_URL"] = os.environ.get("PUB_HOSTED_URL", "")
    elif lang == "elixir":
        need = {"elixir": _which("elixir")}
        run = [need["elixir"], os.path.join(sdk, "conformance.exs")]
    elif lang == "lua":
        need = {"lua": _which("lua5.4", "lua5.3", "lua", "luajit")}
        run = [need["lua"], os.path.join(sdk, "conformance.lua")]
        env["LUA_PATH"] = os.path.join(sdk, "?.lua") + ";;"
    else:
        raise KeyError(lang)
    missing = [name for name, path in need.items() if not path]
    if target == "quickstart" and not missing:
        build, run = _quickstart(lang, sdk, out, need, build, run)
    return {"lang": lang, "missing": missing, "build": build, "run": run, "env": env, "cwd": cwd, "out": out, "tools": need}


def _quickstart(lang: str, sdk: str, out: str, need: Dict[str, Any], build: List[List[str]], run: List[str]) -> Tuple[List[List[str]], List[str]]:
    """Build and run commands for an SDK's quickstart example."""
    j = os.path.join
    if lang == "python":
        return build, [need["python3"], j(sdk, "examples", "quickstart.py")]
    if lang == "javascript":
        return build, [need["node"], j(sdk, "examples", "quickstart.js")]
    if lang == "typescript":
        return build, [need["node"], j(out, "quickstart.js")]
    if lang == "go":
        return [[need["go"], "build", "-o", j(out, "quickstart"), "./cmd/quickstart"]], [j(out, "quickstart")]
    if lang == "rust":
        return ([[need["cargo"], "build", "--quiet", "--offline", "--example", "quickstart", "--target-dir", out]],
                [j(out, "debug", "examples", "quickstart")])
    if lang == "java":
        return build, run[:-1] + ["dev.fluidian.examples.Quickstart"]
    if lang == "kotlin":
        sources = [s for s in sorted(glob.glob(j(sdk, "src", "**", "*.kt"), recursive=True)) if "Conformance" not in os.path.basename(s)]
        jar = j(out, "quickstart.jar")
        return ([[need["kotlinc"]] + sources + ["-include-runtime", "-nowarn", "-d", jar]],
                [need["java"], "-Dfile.encoding=UTF-8", "-cp", jar, "dev.fluidian.examples.QuickstartKt"])
    if lang == "csharp":
        target = j(out, "quickstart")
        return ([[need["dotnet"], "build", j(sdk, "examples", "Quickstart"), "-c", "Release", "-o", target, "--nologo", "-v", "q",
                  "-p:UseAppHost=false"]], [need["dotnet"], j(target, "Quickstart.dll")])
    if lang == "cpp":
        return ([[need["g++"], "-std=c++17", "-O1", "-I" + j(sdk, "include"), j(sdk, "examples", "quickstart.cpp"), "-o", j(out, "quickstart")]],
                [j(out, "quickstart")])
    if lang == "ruby":
        return build, [need["ruby"], "-I" + j(sdk, "lib"), j(sdk, "examples", "quickstart.rb")]
    if lang == "php":
        return build, [need["php"], j(sdk, "examples", "quickstart.php")]
    if lang == "dart":
        return build, [need["dart"], "run", j(sdk, "example", "quickstart.dart")]
    if lang == "elixir":
        return build, [need["elixir"], j(sdk, "examples", "quickstart.exs")]
    if lang == "lua":
        return build, [need["lua"], j(sdk, "examples", "quickstart.lua")]
    raise KeyError(lang)


NOTES = "Ship the beta on Friday. Émile owns QA — 日本語 ✓"


def quickstart_script() -> List[Tuple[Any, int, bool]]:
    """Scripted session for the quickstart example that every SDK ships."""
    return [
        ({"t": "open", "sid": "q1", "route": "/", "locale": "en-US", "viewport": {"w": 1280, "h": 800}}, 1, False),
        (_ev("q1", "increment", target="add"), 1, False),
        (_ev("q1", "increment", target="add"), 1, False),
        (_ev("q1", "set_notes", target="notes", value=NOTES), 1, False),
        (_ev("q1", "summarise", target="summarise"), 1, False),
        ({"t": "ai.result", "rid": "@rid", "ok": True, "data": {"title": "Beta ships Friday", "body": "Émile owns QA."}}, 1, False),
        (_ev("q1", "summarise", target="summarise"), 1, False),
        ({"t": "ai.result", "rid": "@rid", "ok": False, "error": "offline"}, 2, False),
        (_ev("q1", "reset"), 1, False),
        ({"t": "shutdown"}, 0, False),
    ]


def _check_quickstart(got: List[Dict[str, Any]]) -> None:
    """The reference quickstart must itself behave as documented."""
    def texts(msg: Dict[str, Any]) -> List[str]:
        if msg.get("t") != "scene":
            return []
        found: List[str] = []
        stack = [msg["root"]]
        while stack:
            node = stack.pop()
            props = node.get("props") or {}
            found.append(str(props.get("content") or props.get("title") or ""))
            stack.extend(node.get("children") or [])
        return found
    kinds = [m.get("t") for m in got]
    assert kinds == ["ready", "scene", "scene", "scene", "scene", "ai.invoke", "scene", "ai.invoke", "toast", "scene", "scene", "exit"], kinds
    assert "Count: 0" in texts(got[1]) and "Count: 2" in texts(got[3]) and "Count: 0" in texts(got[10]), "counter"
    assert got[5]["capability"] == "content.summarize" and got[5]["input"] == {"text": NOTES}, got[5]
    assert "Beta ships Friday" in texts(got[6]), "summary callout"
    assert got[8]["text"] == "Could not summarise: offline" and got[8]["tone"] == "warning", got[8]
    assert got[0]["actions"] == [{"name": "reset", "description": "Reset the counter to zero", "params": {}}], got[0]


_REFERENCE: Dict[str, List[Dict[str, Any]]] = {}


def reference(target: str) -> List[Dict[str, Any]]:
    """Reference transcript: the stored golden file, or the Python quickstart run on demand."""
    if target == "conformance":
        return golden()
    if target not in _REFERENCE:
        tc = toolchain("python", target)
        got = transcript(tc["run"], tc["env"], tc["cwd"], steps=quickstart_script())
        _check_quickstart(got)
        _REFERENCE[target] = got
    return _REFERENCE[target]


class _Proc:
    def __init__(self, argv: List[str], env: Dict[str, str], cwd: str):
        full = dict(os.environ, **{k: v for k, v in env.items() if v})
        self.proc = subprocess.Popen(argv, cwd=cwd, env=full, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.lines: "queue.Queue[Optional[str]]" = queue.Queue()
        self.stderr: List[str] = []
        threading.Thread(target=self._pump, daemon=True).start()
        threading.Thread(target=self._pump_err, daemon=True).start()

    def _pump(self) -> None:
        assert self.proc.stdout is not None
        try:
            for raw in iter(self.proc.stdout.readline, b""):
                self.lines.put(raw.decode("utf-8", "replace"))
        except (OSError, ValueError):
            pass  # the pipe was closed while the process was being torn down
        self.lines.put(None)

    def _pump_err(self) -> None:
        assert self.proc.stderr is not None
        try:
            for raw in iter(self.proc.stderr.readline, b""):
                self.stderr.append(raw.decode("utf-8", "replace").rstrip())
        except (OSError, ValueError):
            pass

    def send(self, msg: Dict[str, Any], ascii_only: bool) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(msg, ensure_ascii=ascii_only, separators=(",", ":")) + "\n").encode("utf-8"))
        self.proc.stdin.flush()

    def read(self, timeout: float) -> Dict[str, Any]:
        deadline = time.time() + timeout
        while True:
            try:
                line = self.lines.get(timeout=max(0.05, deadline - time.time()))
            except queue.Empty:
                raise TimeoutError("no message within %.0fs; stderr: %s" % (timeout, " | ".join(self.stderr[-5:])))
            if line is None:
                raise EOFError("application exited (code %s); stderr: %s" % (self.proc.poll(), " | ".join(self.stderr[-8:])))
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                raise ValueError("stdout line is not JSON: %r" % line[:200])
            if isinstance(msg, dict) and "t" in msg:
                return msg


def transcript(argv: List[str], env: Dict[str, str], cwd: str, startup: float = 120.0,
               steps: Optional[List[Tuple[Any, int, bool]]] = None) -> List[Dict[str, Any]]:
    """Run the scripted session against an application and return canonical replies."""
    proc = _Proc(argv, env, cwd)
    out: List[Dict[str, Any]] = []
    try:
        out.append(canonical(proc.read(startup)))
        rid = None
        for msg, replies, ascii_only in (steps if steps is not None else script()):
            if msg.get("rid") == "@rid":
                msg = dict(msg, rid=rid)
            proc.send(msg, ascii_only)
            for _ in range(replies):
                reply = proc.read(20.0)
                if reply.get("t") == "ai.invoke":
                    rid = reply.get("rid")
                out.append(canonical(reply))
        try:
            code = proc.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            code = None
        out.append({"t": "exit", "code": code})
    finally:
        stop_process(proc.proc, timeout=5.0)
        for stream in (proc.proc.stdin, proc.proc.stdout, proc.proc.stderr):
            try:
                if stream:
                    stream.close()
            except OSError:
                pass
    return out


def _first_diff(a: Any, b: Any, path: str = "$") -> str:
    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool)):
        return "%s: expected %s, got %s" % (path, json.dumps(a, ensure_ascii=False)[:90], json.dumps(b, ensure_ascii=False)[:90])
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in b:
                return "%s.%s: missing" % (path, k)
            if k not in a:
                return "%s.%s: unexpected %s" % (path, k, json.dumps(b[k], ensure_ascii=False)[:80])
            d = _first_diff(a[k], b[k], "%s.%s" % (path, k))
            if d:
                return d
        return ""
    if isinstance(a, list):
        if len(a) != len(b):
            return "%s: expected %d items, got %d" % (path, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            d = _first_diff(x, y, "%s[%d]" % (path, i))
            if d:
                return d
        return ""
    return "" if a == b else "%s: expected %s, got %s" % (path, json.dumps(a, ensure_ascii=False)[:90], json.dumps(b, ensure_ascii=False)[:90])


def golden() -> List[Dict[str, Any]]:
    with open(GOLDEN, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_golden() -> int:
    tc = toolchain("python")
    result = transcript(tc["run"], tc["env"], tc["cwd"])
    os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
    with open(GOLDEN, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fh.write("\n")
    return len(result)


def run(lang: str, verbose: bool = False, target: str = "conformance") -> Tuple[str, str, float]:
    """Build and verify one SDK. Returns (status, detail, seconds); status is pass, fail or skip."""
    started = time.time()
    tc = toolchain(lang, target)
    if tc["missing"]:
        return "skip", "toolchain not installed: " + ", ".join(tc["missing"]), 0.0
    os.makedirs(tc["out"], exist_ok=True)
    env = dict(os.environ, **{k: v for k, v in tc["env"].items() if v})
    for cmd in tc["build"]:
        done = subprocess.run(cmd, cwd=tc["cwd"], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if done.returncode != 0:
            return "fail", "build failed: %s\n%s" % (" ".join(cmd[:4]), done.stdout.decode("utf-8", "replace")[-1800:]), time.time() - started
    try:
        want = reference(target)
        got = transcript(tc["run"], tc["env"], tc["cwd"], steps=None if target == "conformance" else quickstart_script())
    except (TimeoutError, EOFError, ValueError, OSError, AssertionError) as exc:
        return "fail", str(exc)[:1500], time.time() - started
    if len(got) != len(want):
        return "fail", "transcript length %d, expected %d" % (len(got), len(want)), time.time() - started
    for index, (a, b) in enumerate(zip(want, got)):
        diff = _first_diff(a, b)
        if diff:
            return "fail", "message %d (%s): %s" % (index, a.get("t"), diff), time.time() - started
    return "pass", "%d messages identical to the reference transcript" % len(got), time.time() - started


def run_scaffold(lang: str) -> Tuple[str, str, float]:
    """Scaffold a project with ``fluidian new``'s generator, build it and check that it serves a scene."""
    import tempfile
    from .. import codegen
    from ..reflex import scene as S
    started = time.time()
    tc = toolchain(lang)
    if tc["missing"]:
        return "skip", "toolchain not installed: " + ", ".join(tc["missing"]), 0.0
    folder = tempfile.mkdtemp(prefix="fluidian-scaffold-")
    try:
        scene = C.normalize(S.compose_intent("contact form with name, email and message")[0])[0]
        project = codegen.scaffold(lang, folder, "Demo", scene, os.path.join(ROOT, "sdks"))
        tools = dict(tc["tools"], **{"lua5.4": tc["tools"].get("lua"), "python3": tc["tools"].get("python3")})
        resolve = lambda argv: [tools.get(argv[0]) or _which(argv[0]) or argv[0]] + argv[1:]
        env = dict(os.environ, **{k: v for k, v in tc["env"].items() if v and k not in ("GOFLAGS",)})
        if lang == "go":
            env["GOFLAGS"] = "-mod=mod"
        for cmd in project["build"]:
            done = subprocess.run(resolve(cmd) + (["--offline"] if cmd[:2] == ["cargo", "build"] else []), cwd=folder, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if done.returncode != 0:
                return "fail", "scaffold build failed: %s\n%s" % (" ".join(cmd[:3]), done.stdout.decode("utf-8", "replace")[-1500:]), time.time() - started
        steps = [({"t": "open", "sid": "n1", "route": "/", "locale": "en-US", "viewport": {"w": 1280, "h": 800}}, 1, False), ({"t": "shutdown"}, 0, False)]
        run_cmd = resolve(project["run"]) + (["--offline"] if project["run"][:2] == ["cargo", "run"] else [])
        try:
            got = transcript(run_cmd, {k: v for k, v in env.items() if k in tc["env"] or k == "GOFLAGS"}, folder, steps=steps)
        except (TimeoutError, EOFError, ValueError, OSError) as exc:
            return "fail", "scaffold did not run: " + str(exc)[:1200], time.time() - started
        kinds = {n["type"] for n, _, _ in C.walk(got[1]["root"])} if len(got) > 1 and got[1].get("t") == "scene" else set()
        if [m.get("t") for m in got] != ["ready", "scene", "exit"] or not {"Form", "Input", "Button"} <= kinds:
            return "fail", "scaffold produced an unexpected transcript: %s" % [m.get("t") for m in got], time.time() - started
        return "pass", "scaffold builds and serves its first scene", time.time() - started
    finally:
        shutil.rmtree(folder, ignore_errors=True)


_PORTABLE: Dict[str, Any] = {}


def run_convert(lang: str) -> Tuple[str, str, float]:
    """Convert the portable example to ``lang`` and check that the result reproduces every scene and observed handler."""
    import tempfile
    from .. import convert as V
    started = time.time()
    if toolchain(lang)["missing"]:
        return "skip", "toolchain not installed", 0.0
    folder = tempfile.mkdtemp(prefix="fluidian-convert-")
    try:
        if "bundle" not in _PORTABLE:
            _PORTABLE["bundle"] = V.capture(V.locate(os.path.join(ROOT, "examples", "portable", "app.py")), probe=True)
        bundle = _PORTABLE["bundle"]
        report = V.convert(bundle, [lang], folder, single=True)[0]
        check = report["check"]
        if check["status"] != "verified":
            return "fail", "conversion: " + check["detail"], time.time() - started
        if check["routes"] != len(bundle["routes"]) or not check["probes"]:
            return "fail", "conversion checked %d routes and %d handler calls" % (check["routes"], check["probes"]), time.time() - started
        return "pass", check["detail"], time.time() - started
    except V.ConvertError as exc:
        return "fail", "conversion: %s" % exc, time.time() - started
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def run_all(langs: Optional[List[str]] = None, target: str = "conformance") -> Dict[str, Tuple[str, str, float]]:
    return {lang: run(lang, target=target) for lang in (langs or LANGS)}
