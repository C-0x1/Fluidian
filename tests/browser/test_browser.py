"""Headless-Chrome checks: the gallery boots, every page renders without a runtime error, and interaction works.

Run with ``./fluidian test --browser``.  Needs Chrome or Chromium; set FLUIDIAN_BROWSER to choose the binary.
"""
import functools
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from fluidian import procs  # noqa: E402
from fluidian.procs import free_ports, start_server, stop_server, sweep  # noqa: E402
from fluidian.testkit.cdp import Browser  # noqa: E402

# Three ports nothing else is using, chosen when the run starts; FLUIDIAN_TEST_PORT pins them to N, N+1 and N+2.
if os.environ.get("FLUIDIAN_TEST_PORT"):
    PORT = int(os.environ["FLUIDIAN_TEST_PORT"])
    SHOWCASE_PORT, HOST_PORT = PORT + 1, PORT + 2
else:
    PORT, SHOWCASE_PORT, HOST_PORT = free_ports(3)
BASE = "http://127.0.0.1:%d" % PORT
SHOWCASE = "http://127.0.0.1:%d" % SHOWCASE_PORT
HOST = "http://127.0.0.1:%d" % HOST_PORT
HOST_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Host page</title></head><body>
<h1>A page that is not Fluidian</h1>
<fluidian-app id="app" src="%s" route="/logic" theme="ocean"></fluidian-app>
<script src="%s/_fluidian/embed.js"></script>
<script>window.seen = []; for (const name of ["ready", "resize", "navigate"]) document.addEventListener("fluidian:" + name, (e) => window.seen.push([name, e.detail.route || e.detail.height]));</script>
</body></html>""" % (BASE, BASE)
with open(os.path.join(ROOT, "examples", "gallery", "app.py"), encoding="utf-8") as fh:
    ROUTES = re.findall(r'^@page\("([^"]+)"', fh.read(), re.MULTILINE)
BUSY = "!!document.querySelector('.fl-ai-busy, .fl-generative.is-thinking')"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class BrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sweep()   # an earlier run that was interrupted may have left a browser or servers behind
        env = dict(os.environ, FLUIDIAN_OFFLINE="1", FLUIDIAN_EMBED_ORIGINS=HOST)
        cls.procs = []
        try:
            for app, port in (("gallery", PORT), ("showcase", SHOWCASE_PORT)):
                cls.procs.append(start_server([sys.executable, os.path.join(ROOT, "fluidian"), app, "--port", str(port), "--offline"], port, env))
        except RuntimeError:
            for proc in cls.procs:
                stop_server(proc)
            raise
        cls.proc = cls.procs[0]
        cls.host_dir = tempfile.mkdtemp(prefix="fluidian-host-")
        with open(os.path.join(cls.host_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(HOST_PAGE)
        handler = functools.partial(QuietHandler, directory=cls.host_dir)
        cls.host = http.server.ThreadingHTTPServer(("127.0.0.1", HOST_PORT), handler)
        threading.Thread(target=cls.host.serve_forever, daemon=True).start()
        cls.browser = Browser(1280, 900, scale=1)

    @classmethod
    def tearDownClass(cls):
        # Clean-up never decides the result: each step runs whatever happened to the one before it.
        cls.browser.close()
        try:
            cls.host.shutdown()
            cls.host.server_close()
        except OSError:
            pass
        shutil.rmtree(cls.host_dir, ignore_errors=True)
        for proc in cls.procs:
            stop_server(proc)

    def visit(self, route, query=""):
        self.browser.navigate(BASE + route + ("?" + query if query else ""))
        self.browser.wait_for("!!document.querySelector('.fl-page')", timeout=20)
        deadline, quiet = time.time() + 15, 0
        while time.time() < deadline and quiet < 3:
            quiet = 0 if self.browser.eval(BUSY) else quiet + 1
            time.sleep(0.1)

    def errors(self):
        return json.loads(self.browser.eval("JSON.stringify(window.__fluidian.errors())"))

    def test_every_page_renders_without_runtime_errors(self):
        for route in ROUTES:
            with self.subTest(route=route):
                self.visit(route)
                self.assertEqual(self.errors(), [], route)
                self.assertEqual(json.loads(self.browser.eval("JSON.stringify(window.__fluidian.fixes())")), [], "scene repairs or unparseable logic on %s" % route)
                self.assertTrue(self.browser.eval("document.querySelector('.fl-page').innerText.length > 40"), route)
                self.assertEqual(self.browser.eval("document.querySelectorAll('.fl-generative.is-error').length"), 0, "a generated region failed on %s" % route)

    def test_navigation_is_client_side(self):
        self.visit("/")
        self.browser.eval("window.__marker = 1; [...document.querySelectorAll('.fl-nav-item')].find((a) => a.getAttribute('href') === '/dashboard').click()")
        self.browser.wait_for("location.pathname === '/dashboard' && !!document.querySelector('[data-fl-id=\"revenue-chart\"]')", timeout=10)
        self.assertEqual(self.browser.eval("window.__marker"), 1, "the page must not reload")

    def test_generated_interfaces_appear(self):
        self.visit("/compose")
        self.assertTrue(self.browser.wait_for("document.querySelectorAll('.fl-generative.is-ready').length >= 3", timeout=15))
        self.assertTrue(self.browser.eval("!!document.querySelector('[data-fl-id=\"gen-feedback\"] [data-fl-type=\"Rating\"]')"))

    def test_fields_understand_natural_language(self):
        steps = [{"do": "type", "target": "when", "value": "tomorrow 9am"}, {"do": "type", "target": "weight", "value": "2.5 tonnes"}]
        import base64
        self.visit("/forms", "autopilot=" + base64.urlsafe_b64encode(json.dumps(steps).encode()).decode().rstrip("="))
        self.browser.wait_for("document.body.dataset.autopilot === 'done'", timeout=20)
        self.assertTrue(self.browser.wait_for("document.querySelectorAll('.fl-ai-msg').length >= 2", timeout=10))
        text = self.browser.eval("[...document.querySelectorAll('.fl-ai-msg')].map((e) => e.innerText).join(' | ')")
        self.assertIn("09:00", text)
        self.assertIn("2.5 tonnes", text)

    def test_plain_language_table_filter(self):
        self.visit("/data")
        self.browser.eval("(() => { const el = document.querySelector('[data-fl-id=\"data-table\"] .fl-nlq-input'); el.value = 'overdue over 5000, largest first'; el.form.requestSubmit(); })()")
        self.assertTrue(self.browser.wait_for("document.querySelectorAll('[data-fl-id=\"data-table\"] tbody tr').length === 3", timeout=10))
        self.assertIn("INV-2041", self.browser.eval("document.querySelector('[data-fl-id=\"data-table\"] tbody tr').innerText"))

    def test_intent_bar_runs_a_registered_action(self):
        self.visit("/command")
        self.browser.eval("(() => { const el = document.querySelector('[data-fl-intent]'); el.focus(); el.value = 'create an invoice for Globex for $300'; "
                          "el.dispatchEvent(new Event('input', {bubbles: true})); el.form.requestSubmit(); })()")
        self.assertTrue(self.browser.wait_for("!!document.querySelector('[data-fl-id=\"last-action\"]')", timeout=10))
        self.assertIn("Globex", self.browser.eval("document.querySelector('[data-fl-id=\"last-action\"]').innerText"))

    def test_command_palette_runs_actions_from_any_page(self):
        self.visit("/components")
        self.browser.eval("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'k', ctrlKey: true, bubbles: true}))")
        self.assertTrue(self.browser.wait_for("!!document.querySelector('.fl-palette [data-fl-intent]')", timeout=5))
        self.browser.eval("(() => { const el = document.querySelector('.fl-palette [data-fl-intent]'); el.value = 'open the trust page'; "
                          "el.dispatchEvent(new Event('input', {bubbles: true})); el.form.requestSubmit(); })()")
        self.assertTrue(self.browser.wait_for("location.pathname === '/trust'", timeout=10))
        self.browser.eval("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
        self.assertTrue(self.browser.wait_for("!document.querySelector('.fl-palette')", timeout=5))

    def test_generated_regions_can_be_refined(self):
        self.visit("/compose")
        self.browser.wait_for("!!document.querySelector('[data-fl-id=\"gen-feedback\"] .fl-gen-refine')", timeout=15)
        self.browser.eval("(() => { const el = document.querySelector('[data-fl-id=\"gen-feedback\"] .fl-gen-refine'); el.value = 'add a phone field'; el.form.requestSubmit(); })()")
        self.assertTrue(self.browser.wait_for("[...document.querySelectorAll('[data-fl-id=\"gen-feedback\"] label, [data-fl-id=\"gen-feedback\"] .fl-label')].some((l) => /phone/i.test(l.textContent))", timeout=10))

    def test_theme_prompt_restyles_the_page(self):
        self.visit("/restyle")
        self.assertTrue(self.browser.wait_for("getComputedStyle(document.documentElement).getPropertyValue('--fl-bg').trim().length > 0 && document.documentElement.dataset.scheme === 'dark'", timeout=10))

    def test_dark_scheme_and_mobile_layout(self):
        self.visit("/dashboard", "theme=dark")
        self.assertEqual(self.browser.eval("document.documentElement.dataset.scheme"), "dark")
        self.assertEqual(self.errors(), [])

    # -- portable logic ------------------------------------------------------------
    def test_portable_logic_runs_in_the_runtime_without_server_events(self):
        self.visit("/logic")
        text = lambda node_id: "document.querySelector('[data-fl-id=\"%s\"]').innerText.trim()" % node_id
        click = lambda node_id: self.browser.eval("document.querySelector('[data-fl-id=\"%s\"]').click()" % node_id)
        self.browser.eval("window.__posted = []; const f = window.fetch; window.fetch = (url, init) => { if (String(url).includes('/_fluidian/event')) window.__posted.push(String(url)); return f(url, init); }")
        self.assertEqual(self.browser.eval(text("count-value")), "0")
        for _ in range(5):
            click("count-add")
        self.assertTrue(self.browser.wait_for(text("count-value") + " === '5'", timeout=5))
        self.assertTrue(self.browser.eval("document.body.innerText.includes('That is five or more')"), "a Show node appears when its expression turns true")
        click("count-sub")
        self.assertTrue(self.browser.wait_for("!document.body.innerText.includes('That is five or more')", timeout=5))
        rows = "document.querySelectorAll('[data-fl-type=\"Checkbox\"]').length"
        before = self.browser.eval(rows)
        self.browser.eval("(() => { const el = document.querySelector('[data-fl-id=\"todo-draft\"] input') || document.querySelector('[data-fl-id=\"todo-draft\"]'); "
                          "el.value = 'Call the venue'; el.dispatchEvent(new Event('input', {bubbles: true})); })()")
        self.assertTrue(self.browser.wait_for("window.__fluidian.state().draft === 'Call the venue'", timeout=5), "two-way binding writes to state")
        click("todo-add")
        self.assertTrue(self.browser.wait_for(rows + " === %d" % (before + 1), timeout=5))
        state = json.loads(self.browser.eval("JSON.stringify(window.__fluidian.state())"))
        self.assertEqual((state["todos"][-1], state["draft"], state["count"]), ({"text": "Call the venue", "done": False}, "", 4))
        self.assertIn("1 of %d done" % (before + 1), self.browser.eval(text("todo-count")))
        self.browser.eval("document.querySelectorAll('[data-fl-type=\"Checkbox\"] input')[1].click()")
        self.assertTrue(self.browser.wait_for(text("todo-count") + ".includes('2 of %d done')" % (before + 1), timeout=5))
        self.browser.eval("document.querySelector('[data-fl-id^=\"todo-remove\"]').click()")
        self.assertTrue(self.browser.wait_for(rows + " === %d" % before, timeout=5))
        self.assertEqual(self.browser.eval("window.__posted.length"), 0, "none of this sent an event to the application")
        self.assertEqual(self.errors(), [])

    def test_portable_actions_can_call_the_ai_kernel(self):
        self.visit("/logic")
        self.browser.eval("document.querySelector('[data-fl-id=\"todo-ask\"]').click()")
        self.assertTrue(self.browser.wait_for("!!window.__fluidian.state().summary && !!document.querySelector('[data-fl-id=\"todo-summary\"]')", timeout=15))
        self.assertTrue(self.browser.eval("document.querySelector('[data-fl-id=\"todo-summary\"]').innerText.trim().length > 10"))

    # -- themes and platforms -------------------------------------------------------
    def test_theme_presets_restyle_any_page(self):
        seen = set()
        for theme, scheme in (("ocean", "light"), ("midnight", "dark"), ("sunset", "light"), ("terminal", "dark")):
            self.visit("/dashboard", "theme=" + theme)
            self.assertEqual(self.browser.eval("document.documentElement.dataset.flTheme"), theme)
            self.assertEqual(self.browser.eval("document.documentElement.dataset.scheme"), scheme)
            seen.add(self.browser.eval("getComputedStyle(document.querySelector('.fl-btn.is-primary') || document.body).getPropertyValue('--fl-brand').trim()"))
            self.assertEqual(self.errors(), [])
        self.assertEqual(len(seen), 4, "each preset supplies its own brand colour")

    def test_one_scene_wears_each_platform_skin(self):
        for platform in ("ios", "android", "web"):
            self.visit("/platforms", "platform=" + platform)
            self.assertEqual(self.browser.eval("document.documentElement.dataset.flPlatform"), platform)
        frames = "JSON.stringify([...document.querySelectorAll('.fl-device-screen')].map((el) => [el.dataset.flPlatform, el.dataset.flTheme || '']))"
        self.assertEqual(json.loads(self.browser.eval(frames)), [["ios", ""], ["android", ""], ["ios", "midnight"]], "one scene, previewed in two skins and a second theme")
        titles = json.loads(self.browser.eval("JSON.stringify([...document.querySelectorAll('.fl-device-screen .fl-screen-title')].map((el) => el.innerText.trim()))"))
        self.assertEqual(titles, ["Wallet"] * 3)
        self.browser.navigate(SHOWCASE + "/mobile/platforms?bare=1")
        self.browser.wait_for("document.querySelectorAll('.fl-device-screen').length === 3", timeout=20)
        self.assertEqual(sorted(p for p, _ in json.loads(self.browser.eval(frames))), ["android", "ios", "web"], "phone, tablet and browser frames around the same scene")
        columns = "JSON.stringify([...document.querySelectorAll('.fl-device-screen')].map((el) => new Set([...el.querySelectorAll('.fl-stat')].map((s) => Math.round(s.getBoundingClientRect().left))).size))"
        phone, tablet, web = json.loads(self.browser.eval(columns))
        self.assertTrue(phone < tablet <= web or phone < web, "the scene reflows to the frame it is in: %s" % [phone, tablet, web])
        self.browser.viewport(390, 844)
        try:
            self.visit("/dashboard", "platform=ios")
            self.assertTrue(self.browser.eval("document.documentElement.scrollWidth <= window.innerWidth + 1"), "no horizontal overflow on a phone")
        finally:
            self.browser.viewport(1280, 900)

    def test_artwork_is_drawn_for_every_kind(self):
        self.visit("/art")
        self.assertGreaterEqual(self.browser.eval("document.querySelectorAll('.fl-art svg').length"), 44)
        self.assertEqual(self.browser.eval("[...document.querySelectorAll('.fl-art svg')].filter((svg) => svg.children.length < 2).length"), 0)
        self.assertEqual(self.errors(), [])

    # -- install and embed ----------------------------------------------------------
    def test_the_app_registers_a_service_worker_and_a_manifest(self):
        self.visit("/")
        self.assertTrue(self.browser.wait_for("navigator.serviceWorker.getRegistration().then((r) => !!r && !!(r.active || r.waiting || r.installing))", timeout=15))
        self.assertEqual(self.browser.eval("navigator.serviceWorker.getRegistration().then((r) => new URL(r.scope).pathname)"), "/")
        manifest = json.loads(self.browser.eval("fetch(document.querySelector('link[rel=manifest]').href).then((r) => r.text())"))
        self.assertEqual((manifest["name"], manifest["display"]), ("Fluidian Gallery", "standalone"))
        self.assertTrue(self.browser.wait_for("caches.open('fluidian-shell-v2').then((c) => c.keys()).then((keys) => keys.some((k) => k.url.endsWith('/_fluidian/runtime/app.js')))", timeout=15),
                        "the shell is cached for offline starts")

    def test_the_app_can_be_embedded_in_another_page(self):
        self.browser.navigate(HOST + "/")
        self.assertTrue(self.browser.wait_for("!!window.seen && window.seen.some((e) => e[0] === 'ready')", timeout=25))
        frame = "document.getElementById('app').shadowRoot.querySelector('iframe')"
        self.assertTrue(self.browser.eval(frame + ".src.startsWith('%s/logic?theme=ocean&embed=1')" % BASE))
        self.assertTrue(self.browser.wait_for("parseInt(%s.style.blockSize, 10) > 600" % frame, timeout=10), "the element grows to fit the application")
        seen = json.loads(self.browser.eval("JSON.stringify(window.seen)"))
        self.assertIn(["ready", "/logic"], seen)
        self.assertTrue(any(kind == "resize" and value > 600 for kind, value in seen))
        self.browser.eval("document.getElementById('app').navigate('/art')")
        self.assertTrue(self.browser.wait_for("window.seen.some((e) => e[0] === 'ready' && e[1] === '/art')", timeout=25))

    # -- shutting down ----------------------------------------------------------------
    def test_the_browser_shuts_down_even_when_signals_are_refused(self):
        """A sandboxed browser (the snap-packaged Chromium, for one) may refuse signals from the shell that started it."""
        browser = Browser(800, 600)
        refused = []

        def refuse():
            refused.append(1)
            raise PermissionError(13, "Permission denied")

        browser.proc.terminate = refuse
        browser.proc.kill = refuse
        browser.navigate(BASE + "/")
        profile = browser.profile
        browser.close()
        self.assertIsNotNone(browser.proc.poll(), "the browser exits when asked over the DevTools protocol")
        self.assertEqual(refused, [], "no signal is needed when the browser can be asked to quit")
        self.assertFalse(os.path.exists(profile), "its temporary profile is removed")
        browser.close()   # closing twice is harmless

    def test_a_browser_without_a_page_connection_still_shuts_down(self):
        browser = Browser(800, 600)
        browser.proc.terminate = browser.proc.kill = lambda: (_ for _ in ()).throw(PermissionError(13, "Permission denied"))
        browser.ws.close()
        browser.ws = None
        browser.close()
        self.assertIsNotNone(browser.proc.poll(), "the browser-level endpoint is used when the page connection is gone")

    def abandon_a_browser(self):
        """Start a browser from a process that then dies without closing it. Returns (process id, debugging port)."""
        launcher = ("import os, sys; sys.path.insert(0, %r); from fluidian.testkit.cdp import Browser; "
                    "b = Browser(640, 480); print(b.proc.pid, b.port, flush=True); os._exit(0)" % os.path.join(ROOT, "engine"))
        out = subprocess.run([sys.executable, "-c", launcher], stdout=subprocess.PIPE, check=True, timeout=60).stdout.split()
        pid, port = int(out[0]), int(out[1])
        self.addCleanup(lambda: procs.remove_leftover({"pid": pid, "kind": "browser", "port": port}))
        return pid, port

    def test_a_browser_abandoned_by_an_interrupted_run_is_found_and_closed(self):
        """What the next run does about a browser whose launcher died without closing it, on a system that refuses to signal it."""
        pid, port = self.abandon_a_browser()
        deadline = time.time() + 2.0   # long enough for a system that ends orphans to have done so
        while time.time() < deadline and procs.browser_endpoint(port, timeout=1.0) is not None:
            time.sleep(0.2)
        if procs.browser_endpoint(port, timeout=3.0) is None:
            # Some systems end a browser together with the process that started it. Then nothing was
            # left behind, and the only thing to check is that no stale note about it survives.
            self.assertEqual([e for e in procs.leftovers() if e.get("port") == port], [], procs.describe(pid, port))
            self.assertEqual([n for n in os.listdir(procs.state_dir()) if n.startswith("browser-%d-" % port)], [], procs.describe(pid, port))
            return
        found = [entry for entry in procs.leftovers() if entry.get("port") == port]
        self.assertEqual(len(found), 1, "the abandoned browser is recognised by the record its launcher left\n" + procs.describe(pid, port))
        self.assertEqual(found[0]["kind"], "browser")
        self.assertTrue(found[0].get("record"), "it was found through its launch record, not by guessing from the process table\n" + procs.describe(pid, port))
        real_kill, refused = procs.os.kill, []

        def kill(target, sig):
            refused.append((target, sig))
            raise PermissionError(13, "Permission denied")

        procs.os.kill = kill
        try:
            self.assertTrue(procs.remove_leftover(found[0]), "it is asked to quit over its own port\n" + procs.describe(pid, port))
        finally:
            procs.os.kill = real_kill
        self.assertEqual(refused, [], "so no signal had to be sent")
        self.assertIsNone(procs.browser_endpoint(port), "nothing answers on its port any more")
        self.assertEqual([entry for entry in procs.leftovers() if entry.get("port") == port], [])
        self.assertFalse(os.path.exists(found[0]["record"]), "its record is removed")
        self.assertFalse(os.path.exists(found[0]["profile"]), "and so is its temporary profile")

    def test_a_browser_in_use_is_never_mistaken_for_an_abandoned_one(self):
        ports = {entry.get("port") for entry in procs.leftovers()}
        self.assertNotIn(self.browser.port, ports, "this suite's own browser is running under a live launcher\n" + procs.describe(self.browser.proc.pid, self.browser.port))
        self.assertEqual(self.browser.record.data["endpoint"], procs.browser_endpoint(self.browser.port), "the record holds the browser's own id")

    def test_the_sweep_at_the_start_of_a_run_closes_an_abandoned_browser(self):
        pid, port = self.abandon_a_browser()
        import io
        said = io.StringIO()
        procs.sweep(said)
        self.assertIsNone(procs.browser_endpoint(port), "after the sweep nothing answers on the abandoned browser's port\n" + procs.describe(pid, port))
        self.assertEqual([n for n in os.listdir(procs.state_dir()) if n.startswith("browser-%d-" % port)], [])
        self.assertIsNotNone(procs.browser_endpoint(self.browser.port), "and the browser this suite is using was left alone")

    # -- showcase -------------------------------------------------------------------
    def test_every_showcase_screen_renders_without_runtime_errors(self):
        listing = subprocess.run([sys.executable, os.path.join(ROOT, "examples", "showcase", "app.py"), "--list"], stdout=subprocess.PIPE, check=True,
                                 env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "sdks", "python"))).stdout
        screens = json.loads(listing)
        self.assertEqual(len(screens), 85)
        for screen in screens:
            with self.subTest(route=screen["route"]):
                self.browser.navigate(SHOWCASE + screen["route"] + "?bare=1")
                self.browser.wait_for("!!document.querySelector('[data-fl-type=\"Theme\"]') && !document.querySelector('.fl-boot')", timeout=20)
                self.assertEqual(self.errors(), [], screen["route"])
                self.assertEqual(json.loads(self.browser.eval("JSON.stringify(window.__fluidian.fixes())")), [], screen["route"])
                self.assertEqual(self.browser.eval("document.documentElement.dataset.flTheme"), screen["theme"], screen["route"])
                self.assertTrue(self.browser.eval("document.getElementById('fl-root').innerText.length > 80"), screen["route"])
                self.assertEqual(self.browser.eval("document.querySelectorAll('.fl-unknown, .fl-generative.is-error').length"), 0, screen["route"])

    def test_devtools_panel_opens(self):
        self.visit("/dashboard")
        self.browser.eval("document.dispatchEvent(new KeyboardEvent('keydown', {key: '.', ctrlKey: true, bubbles: true}))")
        self.assertTrue(self.browser.wait_for("!!document.querySelector('.fl-dev')", timeout=5))


if __name__ == "__main__":
    unittest.main()
