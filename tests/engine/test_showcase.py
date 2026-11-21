"""The showcase: 85 complete screens, every one rendered through a real engine without a single scene repair."""
import json
import os
import subprocess
import sys
import time
import unittest

import support
from fluidian import colors
from fluidian import components as C
from fluidian.server import Engine

APP = os.path.join(support.ROOT, "examples", "showcase", "app.py")
SDK = os.path.join(support.ROOT, "sdks", "python")
SCREENS = json.loads(subprocess.run([sys.executable, APP, "--list"], stdout=subprocess.PIPE, env=dict(os.environ, PYTHONPATH=SDK), check=True).stdout)
GROUPS = {"Landing pages": 14, "Storefronts": 12, "Dashboards": 16, "AI products": 13, "Mobile and cross-platform": 14, "Application modules": 16}


class ShowcaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["PYTHONPATH"] = SDK + os.pathsep + os.environ.get("PYTHONPATH", "")
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

    def test_the_catalogue_is_complete_and_varied(self):
        self.assertEqual(len(SCREENS), 85)
        self.assertEqual(len({s["route"] for s in SCREENS}), 85)
        self.assertEqual(len({s["slug"] for s in SCREENS}), 85)
        counts = {}
        for screen in SCREENS:
            counts[screen["group"]] = counts.get(screen["group"], 0) + 1
            self.assertIn(screen["theme"], colors.THEMES, screen["route"])
            self.assertTrue(screen["title"] and screen["caption"], screen["route"])
        self.assertEqual(counts, GROUPS)
        self.assertEqual({s["theme"] for s in SCREENS}, set(colors.THEMES), "every theme preset is used by at least one screen")

    def test_every_screen_renders_cleanly_in_its_own_theme(self):
        for screen in SCREENS:
            with self.subTest(route=screen["route"]):
                session = self.render(screen["route"])
                self.assertEqual(session.fixes, [], screen["route"])
                self.assertEqual((session.scene["type"], session.scene["props"]["preset"]), ("Theme", screen["theme"]))
                nodes = [n for n, _, _ in C.walk(session.scene)]
                self.assertGreaterEqual(len(nodes), 8, screen["route"])
                ids = [n["id"] for n in nodes]
                self.assertEqual(len(ids), len(set(ids)), "duplicate ids on %s" % screen["route"])

    def test_the_index_links_to_every_screen(self):
        index = json.dumps(self.render("/").scene)
        for screen in SCREENS:
            self.assertIn('"%s"' % screen["route"], index)

    def test_the_showcase_exercises_the_component_library(self):
        used = set()
        for screen in SCREENS:
            used.update(n["type"] for n, _, _ in C.walk(self.render(screen["route"]).scene))
        registry = {c["type"] for c in C.COMPONENTS}
        self.assertTrue(used <= registry)
        self.assertGreaterEqual(len(used), 95, sorted(registry - used))
        for family in ("marketing", "commerce", "visual"):
            members = {c["type"] for c in C.COMPONENTS if c["category"] == family}
            self.assertTrue(members and members <= used, "%s components not shown: %s" % (family, sorted(members - used)))


if __name__ == "__main__":
    unittest.main()
