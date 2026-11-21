"""Every page of the gallery renders through a real engine without a single scene repair."""
import json
import os
import re
import sys
import time
import unittest

import support
from fluidian import components as C
from fluidian.server import Engine

APP = os.path.join(support.ROOT, "examples", "gallery", "app.py")
with open(APP, encoding="utf-8") as fh:
    ROUTES = re.findall(r'^@page\("([^"]+)"', fh.read(), re.MULTILINE)


class GalleryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["PYTHONPATH"] = os.path.join(support.ROOT, "sdks", "python") + os.pathsep + os.environ.get("PYTHONPATH", "")
        cls.engine = Engine(support.base_config(offline=True), app_argv=[sys.executable, APP])
        cls.engine.start_app(30.0)

    @classmethod
    def tearDownClass(cls):
        cls.engine.stop()

    def render(self, route):
        session = self.engine.create_session(route, "en-US", {"w": 1440, "h": 900})
        deadline = time.time() + 20
        while session.scene is None and time.time() < deadline:
            time.sleep(0.02)
        self.assertIsNotNone(session.scene, "no scene for %s" % route)
        return session

    def test_there_are_enough_pages(self):
        self.assertGreaterEqual(len(ROUTES), 26)
        self.assertEqual(len(ROUTES), len(set(ROUTES)))

    def test_every_page_renders_cleanly(self):
        capabilities = set(support.CAPS)
        for route in ROUTES:
            with self.subTest(route=route):
                session = self.render(route)
                self.assertEqual(session.fixes, [], route)
                self.assertEqual(session.scene["type"], "Shell")
                nodes = [n for n, _, _ in C.walk(session.scene)]
                self.assertGreater(len(nodes), 3, route)
                ids = [n["id"] for n in nodes]
                self.assertEqual(len(ids), len(set(ids)), "duplicate ids on %s" % route)
                for node in nodes:
                    for binding in node.get("ai") or []:
                        self.assertIn(binding["capability"], capabilities)
                self.assertNotIn('"error"', json.dumps([n["props"].get("title") for n in nodes]))

    def test_unknown_routes_get_a_not_found_page(self):
        session = self.render("/definitely-not-a-page")
        self.assertIn("EmptyState", {n["type"] for n, _, _ in C.walk(session.scene)})

    def test_the_gallery_uses_a_broad_slice_of_the_framework(self):
        used_components, used_capabilities = set(), set()
        for route in ROUTES:
            for node, _, _ in C.walk(self.render(route).scene):
                used_components.add(node["type"])
                used_capabilities.update(b["capability"] for b in node.get("ai") or [])
        self.assertGreaterEqual(len(used_components), 60, sorted({c["type"] for c in C.COMPONENTS} - used_components))
        self.assertGreaterEqual(len(used_capabilities), 30)


if __name__ == "__main__":
    unittest.main()
