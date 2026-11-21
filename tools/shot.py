#!/usr/bin/env python3
"""Capture one page of a running Fluidian app.

    python3 tools/shot.py http://127.0.0.1:8787/landing/lumen out.png [--width 1440] [--height 900] [--scale 1.5] [--full]
"""
import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from fluidian.testkit.cdp import Browser  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--full", action="store_true", help="capture the whole page, not only the viewport")
    ap.add_argument("--wait", type=float, default=0.8)
    args = ap.parse_args()
    with Browser(args.width, args.height, scale=args.scale) as browser:
        browser.navigate(args.url + ("&" if "?" in args.url else "?") + "bare=1")
        browser.wait_for("!!document.querySelector('[data-fl-id]')", timeout=20)
        browser.eval("document.fonts.ready.then(() => 1)")
        time.sleep(args.wait)
        errors = browser.eval("JSON.stringify(window.__fluidian ? window.__fluidian.errors() : [])")
        browser.screenshot(args.out, full_page=args.full)
    print("%s  %d KB  errors=%s" % (args.out, os.path.getsize(args.out) // 1024, errors))


if __name__ == "__main__":
    main()
