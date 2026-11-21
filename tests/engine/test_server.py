"""End-to-end: a real app process, the HTTP surface, server-sent events and the security checks."""
import json
import os
import sys
import time
import unittest

import support
from fluidian.server import Engine

QUICKSTART = os.path.join(support.ROOT, "sdks", "python", "examples", "quickstart.py")


def texts(node):
    out = [str(node["props"].get("content") or node["props"].get("title") or "")]
    for child in node.get("children") or []:
        out.extend(texts(child))
    return out


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["PYTHONPATH"] = os.path.join(support.ROOT, "sdks", "python") + os.pathsep + os.environ.get("PYTHONPATH", "")
        cls.engine = Engine(support.base_config(offline=True), app_argv=[sys.executable, QUICKSTART])
        cls.engine.start_app(30.0)
        cls.engine.serve(block=False)
        cls.base = "http://127.0.0.1:%d" % cls.engine.cfg.port

    @classmethod
    def tearDownClass(cls):
        cls.engine.stop()

    def open(self, route="/"):
        status, _, raw = support.http("POST", self.base + "/_fluidian/session", {"route": route, "locale": "en-US", "viewport": {"w": 1280, "h": 800}})
        self.assertEqual(status, 200)
        return json.loads(raw)

    def scene(self, session, contains=None, timeout=5.0):
        """Read the session's event stream until a scene (optionally containing some text) arrives."""
        deadline = time.time() + timeout
        seen = None
        while time.time() < deadline:
            _, _, raw = support.http("GET", "%s/_fluidian/events?sid=%s&token=%s&once=1" % (self.base, session["sid"], session["token"]))
            for block in raw.decode("utf-8").split("\n\n"):
                if block.startswith("event: scene"):
                    seen = json.loads(block.split("data: ", 1)[1])["root"]
            if seen and (contains is None or contains in texts(seen)):
                return seen
            time.sleep(0.05)
        self.fail("no scene containing %r (last: %s)" % (contains, texts(seen) if seen else None))

    def post(self, session, path, body, **headers):
        merged = {"X-Fluidian-Token": session["token"]}
        merged.update(headers)
        status, _, raw = support.http("POST", self.base + path, dict(body, sid=session["sid"]), merged)
        return status, json.loads(raw or b"{}")

    def test_session_event_round_trip(self):
        session = self.open()
        self.assertEqual(session["app"]["name"], "Quickstart")
        self.assertEqual([a["name"] for a in session["actions"]], ["reset"])
        self.assertFalse(session["live"])
        self.scene(session, "Count: 0")
        for _ in range(2):
            self.assertEqual(self.post(session, "/_fluidian/event", {"name": "increment", "target": "add"})[0], 200)
        self.scene(session, "Count: 2")
        self.post(session, "/_fluidian/event", {"name": "reset"})
        self.scene(session, "Count: 0")

    def test_sessions_are_isolated(self):
        one, two = self.open(), self.open()
        self.post(one, "/_fluidian/event", {"name": "increment"})
        self.scene(one, "Count: 1")
        self.scene(two, "Count: 0")

    def test_app_side_ai_call(self):
        session = self.open()
        self.scene(session, "Count: 0")
        self.post(session, "/_fluidian/event", {"name": "set_notes", "target": "notes", "value": "The importer ships on Friday. QA signs off on Thursday."})
        self.post(session, "/_fluidian/event", {"name": "summarise", "target": "summarise"})
        scene = self.scene(session, "The importer ships on Friday")
        self.assertIn("Callout", json.dumps(scene))

    def test_browser_side_ai_call(self):
        session = self.open()
        status, result = self.post(session, "/_fluidian/ai", {"capability": "input.natural_quantity", "input": {"text": "2.5 tonnes"}})
        self.assertEqual(status, 200)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["unit"], "kg")
        self.assertEqual(result["provenance"]["provider"], "reflex")

    def test_streaming_ai_call(self):
        session = self.open()
        status, _, raw = support.http("POST", self.base + "/_fluidian/ai/stream", {"sid": session["sid"], "capability": "compose.intent", "input": {"intent": "contact form"}},
                                      {"X-Fluidian-Token": session["token"]})
        self.assertEqual(status, 200)
        final = [b for b in raw.decode("utf-8").split("\n\n") if b.startswith("event: result")]
        self.assertEqual(len(final), 1)
        self.assertEqual(json.loads(final[0].split("data: ", 1)[1])["data"]["scene"]["type"], "Page")

    def test_requests_need_the_session_token(self):
        session = self.open()
        self.assertEqual(support.http("POST", self.base + "/_fluidian/event", {"sid": session["sid"], "name": "increment"})[0], 403)
        self.assertEqual(self.post(session, "/_fluidian/event", {"name": "increment"}, **{"X-Fluidian-Token": "wrong"})[0], 403)
        self.assertEqual(support.http("GET", "%s/_fluidian/events?sid=%s&token=nope&once=1" % (self.base, session["sid"]))[0], 403)
        self.assertEqual(self.post({"sid": "missing", "token": "x"}, "/_fluidian/ai", {"capability": "content.title", "input": {"text": "x"}})[0], 403)

    def test_cross_origin_and_foreign_hosts_are_refused(self):
        body = {"route": "/"}
        self.assertEqual(support.http("POST", self.base + "/_fluidian/session", body, {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(support.http("POST", self.base + "/_fluidian/session", body, {"Host": "evil.example"})[0], 403)
        self.assertEqual(support.http("GET", self.base + "/", None, {"Host": "evil.example"})[0], 403)
        self.assertEqual(support.http("POST", self.base + "/_fluidian/session", body, {"Origin": self.base})[0], 200)

    def test_bodies_are_validated(self):
        self.assertEqual(support.http("POST", self.base + "/_fluidian/session", b"not json", {"Content-Type": "application/json"})[0], 400)
        self.assertEqual(support.http("POST", self.base + "/_fluidian/session", b"[1]", {"Content-Type": "application/json"})[0], 400)
        huge = json.dumps({"route": "/", "pad": "x" * (self.engine.cfg.max_body_bytes + 10)}).encode("utf-8")
        # An oversized body is refused before it is read; depending on timing the client sees 413 or a closed connection.
        self.assertIn(support.http("POST", self.base + "/_fluidian/session", huge, {"Content-Type": "application/json"})[0], (413, 0))
        self.assertEqual(support.http("GET", self.base + "/healthz")[0], 200, "the server keeps serving afterwards")
        session = self.open()
        self.assertEqual(self.post(session, "/_fluidian/nothing", {})[0], 404)

    def test_static_surface(self):
        status, headers, raw = support.http("GET", self.base + "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
        self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
        self.assertIn(b"fl-root", raw)
        self.assertEqual(support.http("GET", self.base + "/any/deep/route")[0], 200, "unknown paths serve the app shell")
        for asset, kind in (("app.js", "javascript"), ("fluidian.css", "css"), ("tokens.css", "css"), ("fonts/InterVariable.woff2", "font")):
            status, headers, _ = support.http("GET", self.base + "/_fluidian/runtime/" + asset)
            self.assertEqual(status, 200, asset)
            self.assertIn(kind, headers["Content-Type"], asset)
        self.assertEqual(json.loads(support.http("GET", self.base + "/healthz")[2])["ok"], True)

    def test_static_files_cannot_escape_the_runtime_directory(self):
        for path in ("/_fluidian/runtime/../../engine/fluidian/config.py", "/_fluidian/runtime/%2e%2e/%2e%2e/fluidian", "/_fluidian/runtime/..%2f..%2fLICENSE",
                     "/_fluidian/runtime//etc/passwd"):
            status, _, raw = support.http("GET", self.base + path)
            self.assertNotIn(b"def load_config", raw, path)
            self.assertNotIn(b"root:", raw, path)
            self.assertIn(status, (400, 403, 404), path)

    def test_catalogues(self):
        capabilities = json.loads(support.http("GET", self.base + "/_fluidian/capabilities")[2])
        components = json.loads(support.http("GET", self.base + "/_fluidian/components")[2])
        self.assertEqual(len(capabilities["capabilities"]), 185)
        self.assertEqual(len(components["components"]), 123)

    def test_ai_requests_are_throttled_per_session(self):
        session = self.open()
        codes = [self.post(session, "/_fluidian/ai", {"capability": "content.title", "input": {"text": "Request number %d is here." % i}})[0] for i in range(120)]
        self.assertIn(429, codes)
        self.assertEqual(codes[0], 200)

    def test_closing_a_session_invalidates_it(self):
        session = self.open()
        self.assertEqual(self.post(session, "/_fluidian/close", {})[0], 200)
        self.assertEqual(self.post(session, "/_fluidian/event", {"name": "increment"})[0], 403)


class StaticSceneTest(unittest.TestCase):
    def test_serves_scene_files_without_an_app(self):
        scene = {"type": "Page", "props": {"title": "Static"}, "children": [{"type": "Text", "props": {"content": "No app process"}}, {"type": "Nope", "props": {}}]}
        engine = Engine(support.base_config(offline=True), scenes={"/": scene})
        engine.serve(block=False)
        try:
            base = "http://127.0.0.1:%d" % engine.cfg.port
            session = json.loads(support.http("POST", base + "/_fluidian/session", {"route": "/"})[2])
            raw = support.http("GET", "%s/_fluidian/events?sid=%s&token=%s&once=1" % (base, session["sid"], session["token"]))[2].decode("utf-8")
            data = json.loads(raw.split("data: ", 1)[1].split("\n\n")[0])
            self.assertIn("No app process", texts(data["root"]))
            self.assertEqual(len(data["fixes"]), 1, "developer mode reports scene repairs")
        finally:
            engine.stop()


if __name__ == "__main__":
    unittest.main()
