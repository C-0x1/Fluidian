"""The test runner behind ``fluidian test``.

Four suites run in order and are summarised in one table:

1. **engine**   Python unit and end-to-end tests (``tests/engine``), standard library only.
2. **runtime**  browser-runtime tests under Node's built-in test runner (``tests/runtime``).
3. **sdk**      for every language: the conformance transcript and the quickstart example.
4. **browser**  headless-Chrome checks of the gallery (``--browser`` only).

A suite whose toolchain is missing is reported as skipped, never as passed.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from .. import __version__
from ..codegen import LANGS, TITLES
from . import conformance as CF

ROOT = CF.ROOT
GREEN, RED, YELLOW, DIM, BOLD, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    GREEN = RED = YELLOW = DIM = BOLD = RESET = ""
MARK = {"pass": GREEN + "PASS" + RESET, "fail": RED + "FAIL" + RESET, "skip": YELLOW + "SKIP" + RESET}
# `dotnet build` keeps an MSBuild node and the C# compiler server running for several minutes afterwards, so that
# the next build starts faster. A test run should leave nothing behind: with these in the environment of every
# build it starts, both end when the build does. What is built is the same either way.
NO_BUILD_SERVERS = {"MSBUILDDISABLENODEREUSE": "1", "UseSharedCompilation": "false"}


def _run(argv: List[str], env: Optional[Dict[str, str]] = None, timeout: float = 900.0) -> subprocess.CompletedProcess:
    """Run one suite. A suite that hangs is reported as failed with what it printed, not as a crash of the runner."""
    merged = dict(os.environ, **(env or {}))
    try:
        return subprocess.run(argv, cwd=ROOT, env=merged, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        said = exc.stdout if isinstance(exc.stdout, bytes) else b""
        return subprocess.CompletedProcess(argv, 124, said + ("\nStopped after %d seconds without finishing.\n" % timeout).encode("utf-8"))


def engine_suite(verbose: bool) -> Dict[str, Any]:
    started = time.time()
    env = {"PYTHONPATH": os.path.join(ROOT, "engine") + os.pathsep + os.environ.get("PYTHONPATH", ""), "FLUIDIAN_OFFLINE": "1", "PYTHONWARNINGS": "ignore::ResourceWarning"}
    done = _run([sys.executable, "-m", "unittest", "discover", "-s", os.path.join("tests", "engine"), "-t", os.path.join("tests", "engine")] + (["-v"] if verbose else []), env)
    text = done.stdout.decode("utf-8", "replace")
    ran = re.search(r"Ran (\d+) tests? in", text)
    skipped = re.search(r"skipped=(\d+)", text)
    count = int(ran.group(1)) if ran else 0
    status = "pass" if done.returncode == 0 and count else "fail"
    detail = "%d tests" % count + (", %s skipped" % skipped.group(1) if skipped else "")
    return {"suite": "engine", "name": "Engine, kernel, server and CLI", "status": status, "detail": detail, "seconds": time.time() - started,
            "output": text if status == "fail" or verbose else ""}


def runtime_suite(verbose: bool) -> Dict[str, Any]:
    started = time.time()
    node = shutil.which("node") or shutil.which("nodejs")
    name = "Browser runtime (Node.js)"
    if not node:
        return {"suite": "runtime", "name": name, "status": "skip", "detail": "Node.js is not installed", "seconds": 0.0, "output": ""}
    version = _run([node, "--version"]).stdout.decode().strip()
    major = int(re.sub(r"\D.*$", "", version.lstrip("v")) or 0)
    if major < 18:
        return {"suite": "runtime", "name": name, "status": "skip", "detail": "Node.js %s is too old (18 or newer is required)" % version, "seconds": 0.0, "output": ""}
    files = sorted(glob.glob(os.path.join(ROOT, "tests", "runtime", "*.test.mjs")))
    done = _run([node, "--test"] + files)
    text = done.stdout.decode("utf-8", "replace")
    passed = re.search(r"^# pass (\d+)", text, re.MULTILINE)
    failed = re.search(r"^# fail (\d+)", text, re.MULTILINE)
    count = int(passed.group(1)) if passed else 0
    status = "pass" if done.returncode == 0 and count and not (failed and int(failed.group(1))) else "fail"
    return {"suite": "runtime", "name": name, "status": status, "detail": "%d tests" % count, "seconds": time.time() - started,
            "output": text if status == "fail" or verbose else ""}


def sdk_suite(langs: List[str], verbose: bool, progress: bool) -> List[Dict[str, Any]]:
    rows = []
    for lang in langs:
        started = time.time()
        if progress:
            print("%s  … %s%s" % (DIM, TITLES.get(lang, lang), RESET), end="\r", flush=True)
        status, detail, _ = CF.run(lang)
        if status == "pass":
            quick_status, quick_detail, _ = CF.run(lang, target="quickstart")
            if quick_status != "pass":
                status, detail = quick_status, "quickstart example: " + quick_detail
            else:
                new_status, new_detail, _ = CF.run_scaffold(lang)
                if new_status != "pass":
                    status, detail = new_status, "scaffold: " + new_detail
                else:
                    port_status, port_detail, _ = CF.run_convert(lang)
                    if port_status != "pass":
                        status, detail = port_status, port_detail
                    else:
                        detail = "conformance, quickstart, scaffold and conversion verified"
        rows.append({"suite": "sdk", "name": "SDK · %s" % TITLES.get(lang, lang), "status": status, "detail": detail if status != "fail" else detail.splitlines()[0][:110],
                     "seconds": time.time() - started, "output": detail if status == "fail" else ""})
    if progress:
        print(" " * 40, end="\r")
    return rows


def browser_suite(verbose: bool) -> Dict[str, Any]:
    started = time.time()
    from .cdp import find_browser
    name = "Gallery and showcase in headless Chrome"
    if not find_browser():
        return {"suite": "browser", "name": name, "status": "skip", "detail": "no Chrome or Chromium found (set FLUIDIAN_BROWSER)", "seconds": 0.0, "output": ""}
    done = _run([sys.executable, os.path.join("tests", "browser", "test_browser.py")], {"PYTHONPATH": os.path.join(ROOT, "engine")})
    text = done.stdout.decode("utf-8", "replace")
    ran = re.search(r"Ran (\d+) tests? in", text)
    count = int(ran.group(1)) if ran else 0
    status = "pass" if done.returncode == 0 and count else "fail"
    swept = re.search(r"^Removed (\d+) process(?:es)? left behind", text, re.MULTILINE)
    detail = "%d tests" % count + (" · cleared %s leftover process%s from an earlier run" % (swept.group(1), "" if swept.group(1) == "1" else "es") if swept else "")
    return {"suite": "browser", "name": name, "status": status, "detail": detail, "seconds": time.time() - started, "output": text if status == "fail" or verbose else ""}


def run_suite(quick: bool = False, sdks: Optional[List[str]] = None, skip_sdks: bool = False, browser: bool = False,
              as_json: bool = False, verbose: bool = False) -> int:
    """Run the suites and print a summary. Returns a process exit code (0 when nothing failed)."""
    started = time.time()
    unknown = [s for s in (sdks or []) if s not in LANGS]
    if unknown:
        print("Unknown SDK: %s. Choose from: %s" % (", ".join(unknown), ", ".join(LANGS)))
        return 2
    show = not as_json
    if show:
        print("%sFluidian %s%s  test run\n" % (BOLD, __version__, RESET))
    for key, value in NO_BUILD_SERVERS.items():   # every suite and every build below inherits these
        os.environ.setdefault(key, value)
    rows: List[Dict[str, Any]] = []
    if not sdks:
        rows.append(engine_suite(verbose))
        rows.append(runtime_suite(verbose))
    if not quick and not skip_sdks:
        rows.extend(sdk_suite(sdks or LANGS, verbose, show and sys.stdout.isatty()))
    if browser:
        rows.append(browser_suite(verbose))
    failed = [r for r in rows if r["status"] == "fail"]
    skipped = [r for r in rows if r["status"] == "skip"]
    passed = [r for r in rows if r["status"] == "pass"]
    if as_json:
        print(json.dumps({"version": __version__, "ok": not failed, "passed": len(passed), "failed": len(failed), "skipped": len(skipped),
                          "seconds": round(time.time() - started, 2),
                          "results": [{k: (round(v, 2) if k == "seconds" else v) for k, v in r.items()} for r in rows]}, indent=2))
        return 1 if failed else 0
    width = max(len(r["name"]) for r in rows) + 2
    for r in rows:
        print("  %s  %s %s%6.1fs%s  %s" % (MARK[r["status"]], r["name"].ljust(width), DIM, r["seconds"], RESET, r["detail"]))
    for r in failed:
        print("\n%s── %s ──%s\n%s" % (RED, r["name"], RESET, (r["output"] or r["detail"]).strip()[-6000:]))
    for r in rows:
        if verbose and r["status"] != "fail" and r["output"]:
            print("\n%s── %s ──%s\n%s" % (DIM, r["name"], RESET, r["output"].strip()[-6000:]))
    print("\n%s%d passed%s, %s%d failed%s, %d skipped  in %.1fs" % (GREEN, len(passed), RESET, RED if failed else "", len(failed), RESET if failed else "", len(skipped), time.time() - started))
    if skipped:
        print("%sSkipped suites need a toolchain that is not installed. Run scripts/install-toolchains.sh to add them.%s" % (DIM, RESET))
    if not failed:
        print("%sAll checks that could run have passed.%s" % (GREEN, RESET))
    return 1 if failed else 0
