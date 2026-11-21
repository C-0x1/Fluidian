"""Command line interface: ``fluidian <command>``."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from typing import Any, Dict, List, Optional

from . import __version__
from . import components as C
from .config import load_config

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOLD, DIM, GREEN, RED, YELLOW, CYAN, RESET = "\033[1m", "\033[2m", "\033[32m", "\033[31m", "\033[33m", "\033[36m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    BOLD = DIM = GREEN = RED = YELLOW = CYAN = RESET = ""

BANNER = r"""
   ______ __        _      __ _
  / ____// /__  __ (_)____/ /(_)____ _ ____
 / /_   / // / / // // __  // // __ `// __ \
/ __/  / // /_/ // // /_/ // // /_/ // / / /
/_/   /_/ \__,_//_/ \__,_//_/ \__,_//_/ /_/   v%s
""" % __version__


def _lifeline(engine: Any) -> None:
    """Stop the engine when standard input closes.

    Enabled with ``FLUIDIAN_LIFELINE=stdin``. A harness starts the engine with a
    pipe on its standard input and simply holds the other end: when the harness
    finishes, crashes or is killed, the pipe closes and the engine exits by
    itself, so a server never outlives the process that started it.
    """
    try:
        while sys.stdin.buffer.read(4096):
            pass
    except (OSError, ValueError, AttributeError):
        pass
    engine.stopped.set()


def _serve(engine: Any, cfg: Any, label: str, open_browser: bool) -> int:
    try:
        port = engine.serve(block=False)
    except OSError as exc:
        print("%sCould not listen on %s:%s — %s%s" % (RED, cfg.host, cfg.port, exc, RESET))
        print("Pass --port to choose another port.")
        engine.stop()
        return 1
    url = "http://%s:%d/" % ("localhost" if cfg.host in ("127.0.0.1", "0.0.0.0") else cfg.host, port)
    print(BANNER)
    print("  %s%s%s" % (BOLD, label, RESET))
    print("  Open        %s%s%s" % (CYAN, url, RESET))
    print("  Provider    %s" % ("OpenAI (live)  %s" % cfg.base_url if cfg.live else "Reflex (offline) — set OPENAI_API_KEY to enable models"))
    print("  DevTools    Ctrl+.   ·   Intent bar  Ctrl+K   ·   Point-and-ask  Alt+click")
    print("  Stop        Ctrl+C\n")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    if os.environ.get("FLUIDIAN_LIFELINE") == "stdin":
        threading.Thread(target=_lifeline, args=(engine,), name="fluidian-lifeline", daemon=True).start()
    try:
        while not engine.stopped.is_set():
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        engine.stop()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .server import Engine
    if not args.command:
        print("Usage: fluidian run <app file or project folder>\n       fluidian run -- <command that starts your app>\n"
              "   e.g. fluidian run app.py\n        fluidian run converted/go\n        fluidian run -- ./my-server --flag")
        return 2
    command, cwd = list(args.command), os.getcwd()
    if len(command) == 1 and (os.path.isdir(command[0]) or (os.path.isfile(command[0]) and not os.access(command[0], os.X_OK))):
        from . import convert as V
        try:
            source = V.locate(command[0])
            if source["kind"] != "command":
                print("%s%s is a scene file.%s Serve it with: fluidian serve %s" % (RED, command[0], RESET, command[0]))
                return 2
            if source["build"]:
                print("%sBuilding %s …%s" % (DIM, command[0], RESET))
                V.build_project({"build": source["build"]}, source["cwd"])
        except V.ConvertError as exc:
            print("%s%s%s" % (RED, exc, RESET))
            return 1
        command, cwd = V.resolve(list(source["argv"])), source["cwd"]
        if command[:2] and os.path.basename(command[0]) == "cargo" and command[1] == "run":
            command.append("--offline")
        os.environ.update({k: v for k, v in V.sdk_env().items() if k in ("GOFLAGS", "GOTOOLCHAIN", "DOTNET_CLI_TELEMETRY_OPTOUT", "DOTNET_NOLOGO")})
    cfg = load_config(overrides={"port": args.port, "host": args.host, "offline": True if args.offline else None, "dev": False if args.production else None})
    engine = Engine(cfg, app_argv=command, app_cwd=cwd, trace=args.trace)
    try:
        engine.start_app(args.ready_timeout)
    except (RuntimeError, OSError) as exc:
        print("%sCould not start the application:%s %s" % (RED, RESET, exc))
        return 1
    return _serve(engine, cfg, "%s  (%s SDK)" % (engine.app_meta.get("name"), engine.app_meta.get("sdk") or "custom"), args.open)


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import Engine, load_scenes
    cfg = load_config(overrides={"port": args.port, "host": args.host, "offline": True if args.offline else None})
    try:
        scenes = load_scenes(args.scene)
    except (OSError, ValueError) as exc:
        print("%sCould not read %s:%s %s" % (RED, args.scene, RESET, exc))
        return 1
    return _serve(Engine(cfg, scenes=scenes), cfg, "Static scene  %s" % args.scene, args.open)


def cmd_gallery(args: argparse.Namespace) -> int:
    app = os.path.join(ROOT, "examples", "gallery", "app.py")
    os.environ["PYTHONPATH"] = os.path.join(ROOT, "sdks", "python") + os.pathsep + os.environ.get("PYTHONPATH", "")
    args.command, args.trace, args.ready_timeout, args.production = [sys.executable, app], False, 30.0, False
    return cmd_run(args)


def cmd_showcase(args: argparse.Namespace) -> int:
    app = os.path.join(ROOT, "examples", "showcase", "app.py")
    os.environ["PYTHONPATH"] = os.path.join(ROOT, "sdks", "python") + os.pathsep + os.environ.get("PYTHONPATH", "")
    args.command, args.trace, args.ready_timeout, args.production = [sys.executable, app], False, 30.0, False
    return cmd_run(args)


def cmd_test(args: argparse.Namespace) -> int:
    from .testkit.runner import run_suite
    return run_suite(quick=args.quick, sdks=args.sdk, skip_sdks=args.no_sdks, browser=args.browser, as_json=args.json, verbose=args.verbose)


def cmd_doctor(args: argparse.Namespace) -> int:
    from .testkit.conformance import toolchain
    from .codegen import LANGS, TITLES
    cfg = load_config()
    print(BANNER)
    ok = True
    print("%sEnvironment%s" % (BOLD, RESET))
    print("  Python        %s%s%s %s" % (GREEN, "ok", RESET, sys.version.split()[0]))
    if sys.version_info < (3, 8):
        ok = False
        print("  %sPython 3.8 or newer is required.%s" % (RED, RESET))
    node = shutil.which("node") or shutil.which("nodejs")
    print("  Node.js       %s" % ("%sok%s %s" % (GREEN, RESET, subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()) if node
                                  else "%smissing%s (needed for runtime tests and the JavaScript/TypeScript SDKs)" % (YELLOW, RESET)))
    chrome = next((shutil.which(c) for c in ("google-chrome", "chromium", "chromium-browser", "chrome") if shutil.which(c)), None)
    print("  Browser       %s" % ("%sok%s %s" % (GREEN, RESET, chrome) if chrome else "%soptional%s (headless Chrome enables `fluidian test --browser`)" % (DIM, RESET)))
    print("\n%sSDK toolchains%s" % (BOLD, RESET))
    ready = 0
    for lang in LANGS:
        tc = toolchain(lang)
        if tc["missing"]:
            print("  %-12s %smissing%s %s" % (TITLES[lang], YELLOW, RESET, ", ".join(tc["missing"])))
        else:
            ready += 1
            print("  %-12s %sok%s" % (TITLES[lang], GREEN, RESET))
    print("  %d of %d toolchains available%s" % (ready, len(LANGS), "" if ready == len(LANGS) else " — run scripts/install-toolchains.sh to add the rest"))
    print("\n%sProvider%s" % (BOLD, RESET))
    if not cfg.api_key:
        print("  %sNo API key.%s Fluidian runs on the Reflex provider (offline). Export OPENAI_API_KEY to enable models." % (YELLOW, RESET))
    else:
        print("  API key       set (%s)   base URL %s" % (cfg.redacted()["api_key"], cfg.base_url))
        if args.live:
            from .kernel import Kernel
            from .openai_client import ProviderError
            kernel = Kernel(cfg)
            try:
                models = kernel.client.list_models()
                print("  Models        %sok%s %d reachable" % (GREEN, RESET, len(models)))
                kernel.router.available, kernel.router._discovered = set(models), True
                for row in kernel.router.table()["tiers"]:
                    mark = GREEN + "ok" + RESET if row["model"] in models else YELLOW + "not found" + RESET
                    print("    %-11s %-28s %s" % (row["tier"], row["model"] or "—", mark))
                result = kernel.invoke("content.title", {"text": "Quarterly planning notes for the platform team."}, mode="reason")
                if result["ok"] and result["provenance"]["provider"] == "openai":
                    print("  Round trip    %sok%s “%s” via %s in %d ms" % (GREEN, RESET, result["data"]["text"], result["provenance"]["model"], result["provenance"]["latencyMs"]))
                    quirks = kernel.client.quirks.get(result["provenance"]["model"])
                    if quirks:
                        print("  Negotiated    %s" % ", ".join(sorted(quirks)))
                else:
                    ok = False
                    print("  Round trip    %sfailed%s %s" % (RED, RESET, (result.get("error") or {}).get("message") or result["provenance"].get("providerError", "fell back to Reflex")))
            except ProviderError as exc:
                ok = False
                print("  %sProvider check failed:%s %s" % (RED, RESET, exc))
        else:
            print("  Run `fluidian doctor --live` to verify the key and model access (makes two small requests).")
    print()
    return 0 if ok else 1


def cmd_features(args: argparse.Namespace) -> int:
    from .kernel import catalog
    data = catalog()
    caps = [c for c in data["capabilities"] if not args.category or c["category"] == args.category]
    if args.json:
        print(json.dumps({"categories": data["categories"], "capabilities": caps}, indent=1, ensure_ascii=False))
        return 0
    for cat in data["categories"]:
        rows = [c for c in caps if c["category"] == cat["id"]]
        if not rows:
            continue
        print("\n%s%s%s  %s(%d)%s  %s" % (BOLD, cat["title"], RESET, DIM, len(rows), RESET, cat["blurb"]))
        for c in rows:
            print("  %s%-26s%s %-34s %s%s%s" % (CYAN, c["id"], RESET, c["title"], DIM, c["summary"][:74], RESET))
    print("\n%d capabilities. Reference: docs/reference/capabilities.md · try one: fluidian ai content.summarize --input '{\"text\": \"…\"}'\n" % len(caps))
    return 0


def cmd_components(args: argparse.Namespace) -> int:
    if args.json:
        print(json.dumps(C.export_spec(), indent=1, ensure_ascii=False))
        return 0
    last = ""
    for spec in C.COMPONENTS:
        if spec["category"] != last:
            last = spec["category"]
            print("\n%s%s%s" % (BOLD, last.capitalize(), RESET))
        print("  %s%-14s%s %s" % (CYAN, spec["type"], RESET, spec["summary"]))
    print("\n%d components. Reference: docs/reference/components.md\n" % len(C.COMPONENTS))
    return 0


def cmd_ai(args: argparse.Namespace) -> int:
    from .kernel import Kernel
    from .capabilities.registry import REGISTRY
    cfg = load_config(overrides={"offline": True if args.mode == "reflex" else None})
    kernel = Kernel(cfg)
    cap = REGISTRY.get(args.capability)
    if cap is None:
        print("%sUnknown capability %r.%s Run `fluidian features` for the list." % (RED, args.capability, RESET))
        return 2
    try:
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        else:
            payload = json.loads(args.input) if args.input else cap.example
    except (OSError, ValueError) as exc:
        print("%sInput is not valid JSON:%s %s" % (RED, RESET, exc))
        return 2
    if cap.consent:
        kernel.consent.update("cli", cap.consent, True)
    result = kernel.invoke(args.capability, payload, sid="cli", mode=args.mode)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0 if result["ok"] else 1


def cmd_new(args: argparse.Namespace) -> int:
    from . import codegen
    from .reflex import scene as S
    lang = {"js": "javascript", "ts": "typescript", "c#": "csharp", "cs": "csharp", "c++": "cpp", "py": "python", "rb": "ruby", "ex": "elixir"}.get(args.language.lower(), args.language.lower())
    if lang not in codegen.LANGS:
        print("%sUnknown language %r.%s Choose from: %s" % (RED, args.language, RESET, ", ".join(codegen.LANGS)))
        return 2
    target = os.path.abspath(args.directory)
    os.makedirs(target, exist_ok=True)
    name = args.name or os.path.basename(target).replace("-", " ").replace("_", " ").title()
    scene = C.normalize(S.compose_intent(args.describe or "contact form with name, email and message")[0])[0]
    scene["props"]["title"] = name
    if any(not f.startswith(".") for f in os.listdir(target)) and not args.force:
        print("%s%s is not empty.%s Pass --force to write into it anyway." % (RED, target, RESET))
        return 1
    project = codegen.scaffold(lang, target, name, scene, os.path.join(ROOT, "sdks"))
    quote = lambda argv: " ".join(a if a and all(ch.isalnum() or ch in "-_./=:+" for ch in a) else "'%s'" % a for a in argv)
    print("Created %s%s%s  (%s)" % (BOLD, target, RESET, ", ".join(project["files"])))
    print("The project references the SDK in this checkout: %s" % os.path.join(ROOT, "sdks", lang))
    print("\nRun it:\n  cd %s" % target)
    for step in project["build"]:
        print("  " + quote(step))
    print("  %s run -- %s" % (os.path.join(ROOT, "fluidian"), quote(project["run"])))
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """Convert an application to other languages and verify each result against the source."""
    from . import codegen
    from . import convert as V
    quiet = args.json
    say = (lambda text: None) if quiet else (lambda text: print("  %s%s%s" % (DIM, text, RESET)))
    try:
        source = V.locate(args.source, getattr(args, "command", None))
        if not quiet:
            print("%sFluidian convert%s" % (BOLD, RESET))
        bundle = V.capture(source, routes=args.route or [], follow=not args.no_follow, probe=args.probe, progress=say)
        if not bundle["routes"]:
            raise V.ConvertError("The application served no scene, so there is nothing to convert.")
        origin = bundle.get("language") if bundle.get("language") in codegen.LANGS else None
        targets = V.languages(args.to, exclude=origin)
        if not targets:
            raise V.ConvertError("No target language. Use --to go,rust or --to all.")
        out = os.path.abspath(args.out)
        os.makedirs(out, exist_ok=True)
        V.write_bundle(bundle, os.path.join(out, "scenes.json"))
        port = None
        if args.port_handlers:
            from .kernel import Kernel
            kernel = Kernel(load_config())
            if not kernel.cfg.live:
                print("%s--port-handlers needs a model:%s set OPENAI_API_KEY (scripts/set-api-key.sh). Continuing without it." % (YELLOW, RESET))
            else:
                port = lambda capability, payload: kernel.invoke(capability, payload, sid="convert", mode="reason")
        reports = V.convert(bundle, targets, out, check=not args.no_verify, port=port, progress=say)
    except V.ConvertError as exc:
        if quiet:
            print(json.dumps({"ok": False, "error": str(exc)}))
        else:
            print("%s%s%s" % (RED, exc, RESET))
        return 1
    plans = V.plan_handlers(bundle)
    failed = [r for r in reports if r["check"]["status"] == "failed"]
    if quiet:
        print(json.dumps({"ok": not failed, "name": bundle["name"], "from": bundle.get("language"), "routes": list(bundle["routes"]), "out": out,
                          "handlers": [{"action": p["action"], "status": p["status"]} for p in plans], "notes": bundle["notes"],
                          "targets": reports}, indent=1, ensure_ascii=False))
        return 1 if failed else 0
    observed, stubs = sum(p["status"] == "observed" for p in plans), [p["action"] for p in plans if p["status"] == "stub"]
    print("\n  %s%s%s  from %s · %d route%s · %d handler%s%s" % (
        BOLD, bundle["name"], RESET, codegen.TITLES.get(bundle.get("language") or "", bundle.get("language") or "a scene file"), len(bundle["routes"]),
        "" if len(bundle["routes"]) == 1 else "s", len(plans), "" if len(plans) == 1 else "s",
        " (%d reproduced from observed behaviour)" % observed if observed else ""))
    for note in bundle["notes"][:6]:
        print("  %snote: %s%s" % (YELLOW, note, RESET))
    print()
    colour = {"verified": GREEN, "failed": RED, "skipped": YELLOW, "unchecked": DIM}
    for r in reports:
        check = r["check"]
        mark = {"verified": "✓", "failed": "✗", "skipped": "–", "unchecked": "·"}[check["status"]]
        print("  %s%s %-11s%s %-9s %s%s" % (colour[check["status"]], mark, codegen.TITLES[r["language"]], RESET, check["status"],
                                           check["detail"].splitlines()[0][:110], "  %s%.1fs%s" % (DIM, check["seconds"], RESET) if check["seconds"] else ""))
        if check["status"] == "failed" and len(check["detail"].splitlines()) > 1:
            print("      " + "\n      ".join(check["detail"].splitlines()[1:14]))
        if r.get("port"):
            print("      %sdev.port:%s %s — %s" % (CYAN, RESET, r["port"]["status"], r["port"]["detail"][:150]))
    rel = os.path.relpath(out)
    rel = rel if not rel.startswith("..") else out
    print("\n  Projects: %s%s%s/<language>   scenes: %s" % (BOLD, rel, RESET, os.path.join(rel, "scenes.json")))
    good = next((r for r in reports if r["check"]["status"] == "verified"), reports[0])
    print("  Run one:  %s run %s" % (os.path.join(ROOT, "fluidian") if not shutil.which("fluidian") else "fluidian", os.path.join(rel, good["language"])))
    if stubs:
        shown = ", ".join(stubs[:5]) + (" and %d more" % (len(stubs) - 5) if len(stubs) > 5 else "")
        print("\n  %sHandlers to finish:%s %s" % (YELLOW, RESET, shown))
        hints = []
        if not args.probe:
            hints.append("--probe reproduces handlers that only notify or navigate (it calls each one once on the source app)")
        if not args.port_handlers:
            hints.append("--port-handlers translates the rest with the model and keeps a translation only if it verifies")
        for hint in hints:
            print("    %s%s%s" % (DIM, hint, RESET))
    return 1 if failed else 0


def cmd_tokens(args: argparse.Namespace) -> int:
    """Export a theme's design tokens for other toolchains."""
    from . import colors
    from . import platforms as P
    if args.list:
        for name in colors.theme_names():
            spec = colors.THEMES[name]
            print("  %s%-10s%s %s  %s%s%s" % (CYAN, name, RESET, spec.get("brand"), DIM, "dark" if spec.get("dark") else "light", RESET))
        print("\nFormats: %s" % ", ".join(P.TOKEN_FORMATS))
        return 0
    themes = colors.theme_names() if args.theme == "all" else [args.theme]
    formats = P.TOKEN_FORMATS if args.format == "all" else [args.format]
    try:
        if not args.out and len(themes) == 1 and len(formats) == 1:
            sys.stdout.write(P.export_tokens(themes[0], formats[0], args.scheme))
            return 0
        out = os.path.abspath(args.out or "tokens")
        written = 0
        for theme in themes:
            for fmt in formats:
                folder = os.path.join(out, theme) if len(themes) > 1 else out
                os.makedirs(folder, exist_ok=True)
                name = P.TOKEN_FILES[fmt] % theme if "%s" in P.TOKEN_FILES[fmt] else P.TOKEN_FILES[fmt]
                with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
                    fh.write(P.export_tokens(theme, fmt, args.scheme))
                written += 1
    except P.PlatformError as exc:
        print("%s%s%s" % (RED, exc, RESET))
        return 2
    print("Wrote %d token file%s to %s%s%s" % (written, "" if written == 1 else "s", BOLD, out, RESET))
    return 0


def cmd_package(args: argparse.Namespace) -> int:
    """Write native shell projects around a deployed application."""
    from . import platforms as P
    targets = P.PACKAGE_TARGETS if args.target == "all" else [args.target]
    out = os.path.abspath(args.out)
    try:
        results = [P.package(t, args.name, args.url, out, args.id, args.theme) for t in targets]
    except P.PlatformError as exc:
        print("%s%s%s" % (RED, exc, RESET))
        return 2
    for r in results:
        print("%s%s%s  %s  (%d files)" % (BOLD, {"ios": "iOS", "android": "Android", "desktop": "Desktop"}[r["target"]], RESET, r["directory"], len(r["files"])))
        for i, step in enumerate(r["next"], 1):
            print("  %d. %s" % (i, step))
    print("\n%sThese are source projects; they are built with each platform's own tools.%s" % (DIM, RESET))
    print("%sNothing to package for the web: the engine already serves an installable app (manifest, service worker, icons).%s" % (DIM, RESET))
    return 0


def cmd_codegen(args: argparse.Namespace) -> int:
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import codegen as tool  # type: ignore
    return tool.main()


def cmd_docs(args: argparse.Namespace) -> int:
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import gen_docs as tool  # type: ignore
    return tool.main()


def cmd_export(args: argparse.Namespace) -> int:
    node = shutil.which("node") or shutil.which("nodejs")
    if not node:
        print("%sStatic export needs Node.js 18 or newer.%s" % (RED, RESET))
        return 1
    from .server import load_scenes
    out = args.out or os.path.splitext(args.scene)[0] + ".html"
    try:
        scenes = load_scenes(args.scene)
    except (OSError, ValueError) as exc:
        print("%sCould not read %s:%s %s" % (RED, args.scene, RESET, exc))
        return 1
    scene, fixes = C.normalize(scenes.get("/") or next(iter(scenes.values())))
    for fix in fixes:
        print("%srepaired%s %s" % (DIM, RESET, fix))
    done = subprocess.run([node, os.path.join(ROOT, "tools", "export.mjs"), "-", out], input=json.dumps(scene).encode("utf-8"))
    return done.returncode


def cmd_version(args: argparse.Namespace) -> int:
    print("fluidian %s" % __version__)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fluidian", description="Fluidian — the AI-native interface framework.")
    sub = p.add_subparsers(dest="cmd")

    def net(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--port", type=int, default=None, help="port to listen on (default 8787)")
        sp.add_argument("--host", default=None, help="interface to bind (default 127.0.0.1)")
        sp.add_argument("--offline", action="store_true", help="use the Reflex provider even when an API key is set")
        sp.add_argument("--open", action="store_true", help="open the browser when ready")

    sp = sub.add_parser("run", help="run an application written with any SDK")
    net(sp)
    sp.add_argument("--trace", action="store_true", help="log every protocol message")
    sp.add_argument("--production", action="store_true", help="disable developer tools and detailed errors")
    sp.add_argument("--ready-timeout", type=float, default=60.0, help="seconds to wait for the app to start")
    sp.add_argument("command", nargs=argparse.REMAINDER, help="-- <command>")
    sp.set_defaults(fn=cmd_run)
    sp = sub.add_parser("serve", help="serve a static scene file")
    net(sp)
    sp.add_argument("scene")
    sp.set_defaults(fn=cmd_serve)
    sp = sub.add_parser("gallery", help="launch the gallery: every component and AI capability, live")
    net(sp)
    sp.set_defaults(fn=cmd_gallery)
    sp = sub.add_parser("showcase", help="launch the showcase: 85 complete screens built with the component library")
    net(sp)
    sp.set_defaults(fn=cmd_showcase)
    sp = sub.add_parser("test", help="run every automated test")
    sp.add_argument("--quick", action="store_true", help="engine and runtime tests only")
    sp.add_argument("--sdk", action="append", help="limit SDK conformance to this language (repeatable)")
    sp.add_argument("--no-sdks", action="store_true", help="skip SDK conformance")
    sp.add_argument("--browser", action="store_true", help="also run headless-browser tests")
    sp.add_argument("--json", action="store_true", help="machine-readable summary")
    sp.add_argument("-v", "--verbose", action="store_true")
    sp.set_defaults(fn=cmd_test)
    sp = sub.add_parser("doctor", help="check the environment, toolchains and provider access")
    sp.add_argument("--live", action="store_true", help="verify the API key with real requests")
    sp.set_defaults(fn=cmd_doctor)
    sp = sub.add_parser("features", help="list AI capabilities")
    sp.add_argument("--category")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_features)
    sp = sub.add_parser("components", help="list components")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(fn=cmd_components)
    sp = sub.add_parser("ai", help="invoke a capability from the terminal")
    sp.add_argument("capability")
    sp.add_argument("--input", help="JSON input (defaults to the capability's example)")
    sp.add_argument("--input-file")
    sp.add_argument("--mode", choices=["auto", "reflex", "reason"], default="auto")
    sp.set_defaults(fn=cmd_ai)
    sp = sub.add_parser("new", help="scaffold an application")
    sp.add_argument("language")
    sp.add_argument("directory")
    sp.add_argument("--name")
    sp.add_argument("--describe", help="what the first screen should be")
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(fn=cmd_new)
    sp = sub.add_parser("convert", help="convert an application to any other SDK language and verify the result",
                        description="Runs the source application, records the scene of every route, writes the same application as a runnable "
                                    "project in each target language, then builds and runs every project and compares it with the source.",
                        epilog="examples:\n  fluidian convert app.py --to go,rust\n  fluidian convert app.py --to all --probe\n"
                               "  fluidian convert my-go-app/ --to python\n  fluidian convert --to kotlin -- ./server --flag\n"
                               "  fluidian convert scenes.json --to all",
                        formatter_class=argparse.RawDescriptionHelpFormatter)
    sp.add_argument("source", nargs="?", help="source file, project folder or scene JSON (or give a start command after --)")
    sp.add_argument("--to", default="all", help="target languages, comma separated, or `all` (default)")
    sp.add_argument("-o", "--out", default="converted", help="output folder (default ./converted); one sub-folder per language")
    sp.add_argument("--route", action="append", help="also capture this route (repeatable); linked routes are found automatically")
    sp.add_argument("--no-follow", action="store_true", help="capture only `/` and the routes given with --route")
    sp.add_argument("--probe", action="store_true", help="call each handler once on the source app and reproduce the ones that only notify or navigate")
    sp.add_argument("--port-handlers", action="store_true", help="translate handler code with the model; a translation is kept only if it verifies")
    sp.add_argument("--no-verify", action="store_true", help="write the projects without building and comparing them")
    sp.add_argument("--json", action="store_true", help="machine-readable report")
    sp.set_defaults(fn=cmd_convert, command=None)
    sp = sub.add_parser("tokens", help="export a theme's design tokens (CSS, Tailwind, SwiftUI, Android, Compose, Flutter, …)",
                        epilog="examples:\n  fluidian tokens --list\n  fluidian tokens --theme ocean --format tailwind\n"
                               "  fluidian tokens --theme all --format all -o design-tokens", formatter_class=argparse.RawDescriptionHelpFormatter)
    sp.add_argument("--theme", default="deep", help="theme preset, or `all` (default deep)")
    sp.add_argument("--format", default="css", help="css, scss, json, dtcg, tailwind, swift, android, compose, flutter, or `all`")
    sp.add_argument("--scheme", choices=["light", "dark"], help="force the light or dark variant of the theme")
    sp.add_argument("-o", "--out", help="folder to write files to (default: print one file to the terminal)")
    sp.add_argument("--list", action="store_true", help="list themes and formats")
    sp.set_defaults(fn=cmd_tokens)
    sp = sub.add_parser("package", help="write native shells (iOS, Android, desktop) around a deployed application",
                        epilog="examples:\n  fluidian package all --name \"Field Notes\" --url https://notes.example.com\n"
                               "  fluidian package android --name Demo --url http://10.0.2.2:8787 --id com.example.demo",
                        formatter_class=argparse.RawDescriptionHelpFormatter)
    sp.add_argument("target", choices=["ios", "android", "desktop", "all"])
    sp.add_argument("--name", required=True, help="application name shown to users")
    sp.add_argument("--url", required=True, help="address the application is served at")
    sp.add_argument("--id", help="bundle or application id, for example com.example.app")
    sp.add_argument("--theme", default="deep", help="theme preset used for the window and status bar colours")
    sp.add_argument("-o", "--out", default="native", help="output folder (default ./native)")
    sp.set_defaults(fn=cmd_package)
    sub.add_parser("codegen", help="regenerate SDK component factories and specs").set_defaults(fn=cmd_codegen)
    sub.add_parser("docs", help="regenerate reference documentation").set_defaults(fn=cmd_docs)
    sp = sub.add_parser("export", help="render a scene file to static HTML")
    sp.add_argument("scene")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_export)
    sub.add_parser("version", help="print the version").set_defaults(fn=cmd_version)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    tail = None
    if argv[:1] == ["convert"] and "--" in argv:  # everything after `--` is the command that starts the source app
        cut = argv.index("--")
        argv, tail = argv[:cut], argv[cut + 1:]
    if argv[:1] == ["run"] and "--" not in argv:  # `run app.py --port 9000`: options may follow the file or folder
        rest = argv[1:]
        for i, token in enumerate(rest):
            if not token.startswith("-") and os.path.exists(token) and (i == 0 or rest[i - 1] not in ("--port", "--host", "--ready-timeout")):
                argv = ["run"] + rest[:i] + rest[i + 1:] + ["--", token]
                break
    args = parser.parse_args(argv)
    if tail is not None:
        args.command = tail
    if getattr(args, "cmd", None) == "run" and args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not getattr(args, "fn", None):
        print(BANNER)
        parser.print_help()
        return 0
    try:
        return int(args.fn(args) or 0)
    except KeyboardInterrupt:
        return 130
