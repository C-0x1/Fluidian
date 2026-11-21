"""Capture the documentation screenshots.

    python3 tools/screenshots.py                  # every shot
    python3 tools/screenshots.py dashboard dark   # shots whose name contains a word
    python3 tools/screenshots.py --list           # print the shot list and exit

The script starts the gallery and the showcase in offline mode on private ports,
drives a headless Chrome through the DevTools protocol, and writes PNG files to
``docs/assets/screens`` together with ``index.json``, which the documentation
generator reads.  Set ``FLUIDIAN_BROWSER`` to choose the browser binary and
``FLUIDIAN_SHOT_SCALE`` (default 1.5) for the device pixel ratio.  When
``pngquant`` is installed the files are palette-optimised, which cuts their size
by about two thirds.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from fluidian.procs import start_server, stop_server, sweep  # noqa: E402
from fluidian.testkit.cdp import Browser  # noqa: E402

OUT = os.path.join(ROOT, "docs", "assets", "screens")
PORT = int(os.environ.get("FLUIDIAN_SHOT_PORT", "8793"))
APPS = {"gallery": PORT, "showcase": PORT + 1}
VIEWPORTS = {"desktop": (1440, 900), "tall": (1440, 1180), "mobile": (390, 844)}
SCALE = float(os.environ.get("FLUIDIAN_SHOT_SCALE", "1.5"))


def typed(target, value, blur=True, pause=350):
    return {"do": "type", "target": target, "value": value, "blur": blur, "pause": pause}


def click(selector):
    return "document.querySelector(%s).click()" % json.dumps(selector)


def field(node_id, css=""):
    return '[data-fl-id="%s"] %s' % (node_id, css)


# name, route, caption, options. The gallery is one application, so its pages are captured in a spread of presets
# (``?theme=``) to show that a theme is a choice per screen and not something the framework imposes.
SHOTS = [
    ("001-overview", "/", "Gallery overview", {}),
    ("002-dashboard", "/dashboard", "Dashboard with forecast, anomaly detection and generated insights", {"view": "tall"}),
    ("003-dashboard-dark", "/dashboard", "The same dashboard in the dark scheme", {"query": "theme=dark", "view": "tall"}),
    ("004-generative-ui", "/compose", "Interfaces composed from intent, schema and data", {"query": "theme=iris", "view": "tall"}),
    ("005-sketch-import", "/import", "Text wireframes and legacy HTML translated into components", {"query": "theme=emerald", "view": "tall"}),
    ("006-smart-forms", "/forms", "Natural dates and quantities, format healing and semantic validation", {"auto": [
        typed("when", "next friday 3pm"), typed("weight", "2.5 tonnes"), typed("phone", "415 555 0134"), typed("email", "amara@gmial.com"),
        typed("role", "amara@calder.example"), typed("notes", "Gate code 4411. Card 4242 4242 4242 4242 if there is a fee.")]}),
    ("007-smart-paste", "/paste", "A pasted signature fills the whole form", {"query": "theme=tangerine", "js": [
        "(() => { const el = document.querySelector('.fl-smartpaste-input'); const data = new DataTransfer(); data.setData('text/plain', %s); "
        "el.dispatchEvent(new ClipboardEvent('paste', {clipboardData: data, bubbles: true, cancelable: true})); })()"
        % json.dumps("Dr. Amara Nwosu\nHead of Procurement, Calder Robotics\namara.nwosu@calder-robotics.example\n+44 20 7946 0321\n14 Wharf Lane, Bristol BS1 4RW, United Kingdom")]}),
    ("008-writing-tools", "/writing", "Tone changes are previewed as a diff before they are accepted", {"query": "theme=rose", "view": "tall", "js": [
        click(field("reply", ".fl-iconbtn.is-ai")), "WAIT", "[...document.querySelectorAll('.fl-ai-menu .fl-chip')].find((b) => /friendly/i.test(b.textContent)).click()"]}),
    ("009-intent-bar", "/command", "The Intent Bar routes language to registered actions", {"query": "theme=neon", "js": [
        "(() => { const el = document.querySelector('[data-fl-intent]'); el.focus(); el.value = 'create an invoice for Globex for $300'; el.dispatchEvent(new Event('input', {bubbles: true})); el.form.requestSubmit(); })()"]}),
    ("010-copilot", "/copilot", "A copilot grounded in the current screen", {"query": "theme=grape"}),
    ("011-ask-your-data", "/data", "Plain-language filtering, column typing and chart selection", {"query": "theme=ocean", "view": "tall", "js": [
        "(() => { const el = document.querySelector('[data-fl-id=\"data-table\"] .fl-nlq-input'); el.value = 'overdue over 5000, largest first'; el.form.requestSubmit(); })()"]}),
    ("012-charts", "/charts", "Charts with forecasts, anomaly markers and written descriptions", {"query": "theme=lagoon", "view": "tall"}),
    ("013-data-story", "/story", "A narrative report generated from rows", {"query": "theme=sunset", "view": "tall"}),
    ("014-theme-studio", "/theme", "Themes generated as OKLCH design tokens with contrast repair", {"view": "tall"}),
    ("015-restyle-night", "/restyle", "One sentence restyles the product: “Calm fintech at night”", {}),
    ("016-restyle-citrus", "/restyle", "The same screen as “Sunny citrus market”", {"js": [
        "[...document.querySelectorAll('[data-fl-id=\"theme-choice\"] button, [data-fl-id=\"theme-choice\"] label')].find((b) => /citrus/i.test(b.textContent)).click()"]}),
    ("017-accessibility", "/access", "An accessibility audit with fixes", {"query": "theme=mint", "view": "tall"}),
    ("018-adaptive", "/adaptive", "Context, pace and locale adapt the interface", {"query": "theme=candy"}),
    ("019-content", "/content", "FAQs, change summaries and tours derived from existing content", {"query": "theme=ruby", "view": "tall"}),
    ("020-collaboration", "/collab", "Thread summaries, decisions and reply drafts", {"query": "theme=sky", "view": "tall", "auto": [typed("heated", "This is the THIRD time the build is late. Totally unacceptable!!")]}),
    ("021-workflows", "/flow", "Agent runs with approvals and an audit trail", {"query": "theme=midnight", "settle": False}),
    ("022-trust", "/trust", "Redaction, injection defence, provenance and budgets", {"query": "theme=forest", "view": "tall"}),
    ("023-kernel", "/kernel", "The fifteen-step AI kernel pipeline with live telemetry", {"query": "theme=aurora", "view": "tall"}),
    ("024-developer-tools", "/dev", "Scaffolding, UX review and test synthesis", {"query": "theme=terminal", "view": "tall"}),
    ("025-multimodal", "/multimodal", "Voice, vision, illustration and sonification", {"query": "theme=ember", "view": "tall"}),
    ("026-languages", "/languages", "The same app in fourteen languages", {"query": "theme=citrus"}),
    ("027-components", "/components", "The component library", {"view": "tall", "settle": False}),
    ("028-inputs", "/inputs", "Input controls", {"query": "theme=moss"}),
    ("029-board", "/board", "A board with suggested priorities", {"query": "theme=crimson"}),
    ("030-guided-tour", "/tour", "A guided tour spotlighting live nodes", {}),
    ("031-states", "/states", "Generated empty states, skeletons and progress narration", {"query": "theme=paper", "settle": False}),
    ("032-capability-explorer", "/capabilities", "All 185 capabilities in a filterable table", {"query": "theme=graphite", "view": "tall"}),
    ("033-devtools", "/dashboard", "The built-in trace panel", {"js": [
        "document.dispatchEvent(new KeyboardEvent('keydown', {key: '.', ctrlKey: true, bubbles: true}))"]}),
    ("034-mobile", "/dashboard", "Responsive layout on a phone", {"view": "mobile"}),
]
# Pages added to the gallery after the showcase; numbered after it so earlier numbers never move.
GALLERY_EXTRA = [
    ("portable-logic", "/logic", "Portable logic: state, bindings and actions that run in the runtime and convert between all SDK languages", {"query": "theme=emerald", "view": "tall", "js": [
        "(() => { const b = document.querySelector('[data-fl-id=\"todo-add\"]'); if (b) b.click(); })()", "WAIT"]}),
    ("platform-preview", "/platforms", "One scene previewed with the iOS, Android and web skins", {"view": "tall"}),
    ("art-and-themes", "/art", "Procedural artwork and the twenty-seven theme presets", {"view": "tall"}),
]

BUSY = "!!document.querySelector('.fl-spinner, .fl-ai-busy, .fl-generative.is-thinking, .fl-smartform > .fl-skeleton')"


def showcase_screens():
    """The showcase registers its own screens; ask it for the list."""
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "sdks", "python"))
    out = subprocess.run([sys.executable, os.path.join(ROOT, "examples", "showcase", "app.py"), "--list"], capture_output=True, text=True, env=env, check=True).stdout
    return json.loads(out)


def all_shots():
    """Every shot as a dict: name, app, route, caption, group and capture options."""
    shots = [{"name": name, "app": "gallery", "route": route, "caption": caption, "group": "Gallery", "options": options} for name, route, caption, options in SHOTS]
    number = len(shots)
    for screen in showcase_screens():
        number += 1
        shots.append({"name": "%03d-%s" % (number, screen["slug"]), "app": "showcase", "route": screen["route"], "caption": screen["caption"], "group": screen["group"], "title": screen["title"],
                      "theme": screen["theme"], "options": {"size": (screen["width"], screen["height"])}})
    for slug, route, caption, options in GALLERY_EXTRA:
        number += 1
        shots.append({"name": "%03d-%s" % (number, slug), "app": "gallery", "route": route, "caption": caption, "group": "Gallery", "options": options})
    return shots


def start(app):
    """Start the gallery or the showcase on its port; it exits by itself if this tool is interrupted."""
    env = dict(os.environ, FLUIDIAN_OFFLINE="1", PYTHONUNBUFFERED="1")
    return start_server([sys.executable, os.path.join(ROOT, "fluidian"), app, "--port", str(APPS[app]), "--offline"], APPS[app], env)


def settle(browser, timeout=20.0):
    """Wait until no AI work is in flight for a short, continuous period."""
    quiet, deadline = 0, time.time() + timeout
    while time.time() < deadline and quiet < 4:
        quiet = 0 if browser.eval(BUSY) else quiet + 1
        time.sleep(0.15)


def capture(browser, shot, size):
    options, name = shot["options"], shot["name"]
    query = [options["query"]] if options.get("query") else []
    query.append("bare=1")
    if options.get("auto"):
        query.append("autopilot=" + base64.urlsafe_b64encode(json.dumps(options["auto"]).encode("utf-8")).decode("ascii").rstrip("="))
    browser.viewport(size[0], size[1], scale=2.0 if options.get("view") == "mobile" else SCALE)
    browser.navigate("http://127.0.0.1:%d%s?%s" % (APPS[shot["app"]], shot["route"], "&".join(query)))
    browser.wait_for("!!document.querySelector('.fl-shell, .fl-page, .fl-landing')", timeout=20)
    browser.eval("document.fonts.ready.then(() => 1)")
    time.sleep(0.5)
    if options.get("auto"):
        browser.wait_for("document.body.dataset.autopilot === 'done' || (document.body.dataset.autopilot || '').startsWith('missing')", timeout=30)
        state = browser.eval("document.body.dataset.autopilot")
        if state != "done":
            raise RuntimeError("%s: autopilot stopped at %s" % (name, state))
    for step in options.get("js") or []:
        if step == "WAIT":
            time.sleep(0.5)
            continue
        browser.eval(step)
        time.sleep(0.4)
    if options.get("settle", True):
        settle(browser)
    if shot["app"] == "showcase":
        # Application screens are captured whole; long marketing pages are cropped at the requested height.
        page = int(browser.eval("document.documentElement.scrollHeight") or 0)
        if size[1] < page <= size[1] * 1.3:
            browser.viewport(size[0], page, scale=SCALE)
            time.sleep(0.3)
    time.sleep(0.6)
    browser.eval("document.activeElement && document.activeElement.blur && 0")
    errors = browser.eval("JSON.stringify(window.__fluidian ? window.__fluidian.errors().map((e) => e.message) : [])")
    if errors and errors != "[]":
        raise RuntimeError("%s: runtime errors %s" % (name, errors))
    path = os.path.join(OUT, name + ".png")
    browser.screenshot(path)
    return path


def optimise(paths):
    tool = shutil.which("pngquant")
    if not tool or os.environ.get("FLUIDIAN_SHOT_RAW"):
        return False
    for start_ in range(0, len(paths), 16):
        subprocess.run([tool, "--quality=70-95", "--speed", "3", "--force", "--skip-if-larger", "--ext", ".png"] + paths[start_:start_ + 16], check=False)
    return True


def main(argv):
    shots = all_shots()
    if "--list" in argv:
        for shot in shots:
            print("%-34s %-9s %s" % (shot["name"], shot["app"], shot["route"]))
        return 0
    wanted = [a.lower() for a in argv if not a.startswith("-")]
    chosen = [s for s in shots if not wanted or any(w in s["name"] for w in wanted)]
    os.makedirs(OUT, exist_ok=True)
    sweep()   # a run that was interrupted may have left a browser or servers behind
    procs, done, failed = [], [], []
    try:
        for app in sorted({s["app"] for s in chosen}):
            procs.append(start(app))
        with Browser(1440, 900, scale=SCALE) as browser:
            for shot in chosen:
                options = shot["options"]
                size = options.get("size") or VIEWPORTS[options.get("view", "desktop")]
                started = time.time()
                try:
                    path = capture(browser, shot, size)
                except (RuntimeError, TimeoutError) as exc:
                    failed.append(shot["name"])
                    print("%-34s FAILED  %s" % (shot["name"], exc))
                    continue
                done.append(path)
                print("%-34s %5.1fs  %4d KB" % (shot["name"], time.time() - started, os.path.getsize(path) // 1024))
    finally:
        for proc in procs:
            stop_server(proc)
    if optimise(done):
        print("optimised %d files: %.1f MB in total" % (len(done), sum(os.path.getsize(p) for p in done) / 1048576.0))
    if not wanted:
        keep = {s["name"] + ".png" for s in shots}
        for stale in sorted(f for f in os.listdir(OUT) if f.endswith(".png") and f not in keep):
            os.remove(os.path.join(OUT, stale))
            print("removed stale shot", stale)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        json.dump([{"file": s["name"] + ".png", "app": s["app"], "route": s["route"], "group": s["group"], "title": s.get("title", ""), "theme": s.get("theme", ""), "caption": s["caption"]} for s in shots], fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
