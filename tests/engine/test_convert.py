"""Cross-language conversion: capture a running application, write it in other languages, verify the result."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import support
from fluidian import codegen
from fluidian import components as C
from fluidian import convert as V

APP = os.path.join(support.ROOT, "examples", "portable", "app.py")
CLI = os.path.join(support.ROOT, "fluidian")
NODE = shutil.which("node") or shutil.which("nodejs")
ROUTES = ["/", "/trips", "/about", "/trips/skerry-point", "/trips/larch-hollow", "/trips/kettle-ridge"]


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class ConvertTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = V.capture(V.locate(APP), probe=True)
        cls.tmp = tempfile.mkdtemp(prefix="fluidian-convert-test-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def out(self, name):
        path = os.path.join(self.tmp, name)
        os.makedirs(path, exist_ok=True)
        return path

    # -- discovery ---------------------------------------------------------------
    def test_routes_are_found_in_navigation_links_payloads_and_local_actions(self):
        scene = {"type": "Shell", "props": {"nav": [{"label": "Home", "route": "/"}, {"label": "Orders", "route": "/orders?tab=open#top"}]}, "children": [
            {"type": "Link", "props": {"label": "Docs", "href": "/docs"}},
            {"type": "Link", "props": {"label": "Elsewhere", "href": "https://example.com/x"}},
            {"type": "Link", "props": {"label": "Protocol relative", "href": "//cdn.example.com/x"}},
            {"type": "Button", "props": {"label": "Open"}, "on": {"click": {"action": "go", "payload": {"route": "/orders/7"}}}},
            {"type": "Button", "props": {"label": "Cart"}, "on": {"click": "@count += 1; go '/cart'"}},
            {"type": "Button", "props": {"label": "Dynamic"}, "on": {"click": {"action": "go", "payload": {"route": "/items/{{ item.id }}"}}}},
        ]}
        self.assertEqual(V.find_routes(scene), ["/", "/orders", "/docs", "/orders/7", "/cart"])

    def test_target_languages_accept_names_aliases_and_all(self):
        self.assertEqual(V.languages("go, rs,TS,c#"), ["go", "rust", "typescript", "csharp"])
        self.assertEqual(V.languages("all", exclude="python"), [name for name in codegen.LANGS if name != "python"])
        self.assertEqual(len(V.languages("all")), 14)
        with self.assertRaises(V.ConvertError):
            V.languages("go,cobol")

    def test_sources_are_located_from_files_folders_commands_and_bundles(self):
        self.assertEqual(V.locate(APP)["language"], "python")
        self.assertEqual(V.locate(None, ["./server", "--flag"])["argv"], ["./server", "--flag"])
        project = self.out("located")
        codegen.write_project("go", project, V.emit(self.bundle, "go"), V.SDKS)
        found = V.locate(project)
        self.assertEqual((found["language"], found["argv"]), ("go", ["go", "run", "."]))
        os.remove(os.path.join(project, codegen.MANIFEST))
        self.assertEqual(V.locate(project)["language"], "go", "a project without a manifest is recognised by its layout")
        for bad in (None, os.path.join(self.tmp, "missing"), self.out("empty")):
            with self.assertRaises(V.ConvertError):
                V.locate(bad)

    # -- capture -----------------------------------------------------------------
    def test_capture_records_identity_routes_and_declared_actions(self):
        b = self.bundle
        self.assertEqual((b["name"], b["language"], b["sdk"]), ("Field Notes", "python", "python"))
        self.assertEqual(list(b["routes"]), ROUTES)
        self.assertEqual(b["actions"], [{"name": "export_notes", "description": "Export every note as a file", "params": {"format": "string csv or json"}}])
        self.assertEqual(b["notes"], [])
        kinds = {n["type"] for scene in b["routes"].values() for n, _, _ in C.walk(scene)}
        self.assertTrue({"Theme", "Shell", "State", "Each", "Show", "Art", "Hero", "Breadcrumbs"} <= kinds, kinds)

    def test_capture_can_be_limited_to_named_routes(self):
        bundle = V.capture(V.locate(APP), routes=["/about"], follow=False)
        self.assertEqual(list(bundle["routes"]), ["/", "/about"])
        self.assertEqual(bundle["probes"], [])

    def test_probing_separates_reproducible_handlers_from_stateful_ones(self):
        plans = {p["action"]: p for p in V.plan_handlers(self.bundle)}
        self.assertEqual(list(plans), ["go", "share", "plan_trip", "export_notes"])
        self.assertEqual((plans["go"]["status"], plans["go"]["steps"]), ("observed", [{"do": "navigate_payload", "key": "route"}]))
        self.assertEqual((plans["share"]["status"], plans["share"]["steps"]),
                         ("observed", [{"do": "toast", "text": "Link copied to the clipboard", "tone": "success"}]))
        self.assertEqual(plans["plan_trip"]["status"], "stub", "its message changes between calls, so it is not reproduced from one observation")
        self.assertEqual(plans["export_notes"]["status"], "stub")
        self.assertEqual(plans["export_notes"]["declared"]["description"], "Export every note as a file")
        without = V.plan_handlers(dict(self.bundle, probes=[]))
        self.assertEqual({p["status"] for p in without}, {"stub"}, "nothing is guessed without probing")

    # -- emit --------------------------------------------------------------------
    def test_every_language_gets_one_function_per_route_and_every_handler(self):
        for lang in codegen.LANGS:
            with self.subTest(lang=lang):
                code = V.emit(self.bundle, lang)
                e = codegen.EMITTERS[lang]
                for route in ROUTES:
                    self.assertIn(e.s(route), code)
                for action in ("go", "share", "plan_trip", "export_notes"):
                    self.assertIn(e.s(action), code)
                self.assertIn(e.s("Export every note as a file"), code)
                self.assertIn("@push notes {text: default(draft, ", code, "portable logic travels as data")
                self.assertIn("{{ count(notes, ", code)
                self.assertIn("not ported yet", code)
                self.assertNotIn("{name}", code)
                self.assertNotIn("{scene}", code)

    def test_route_function_names_are_safe_identifiers(self):
        bundle = dict(self.bundle, routes={"/": self.bundle["routes"]["/"], "/404": self.bundle["routes"]["/about"],
                                           "/a-b": self.bundle["routes"]["/about"], "/a_b": self.bundle["routes"]["/about"],
                                           "/class": self.bundle["routes"]["/about"]}, probes=[])
        code = V.emit(bundle, "python")
        for name in ("def home_screen():", "def page_404_screen():", "def a_b_screen():", "def a_b_2_screen():", "def class_screen():"):
            self.assertIn(name, code)
        compile(code, "app.py", "exec")

    # -- verify ------------------------------------------------------------------
    def test_python_conversion_is_verified_and_writes_a_runnable_project(self):
        out = self.out("py")
        report = V.convert(self.bundle, ["python"], out)[0]
        self.assertEqual(report["check"]["status"], "verified", report["check"]["detail"])
        self.assertEqual((report["check"]["routes"], report["check"]["probes"]), (6, 5))
        self.assertEqual(report["handlers"], {"observed": 2, "stub": 2})
        manifest = V.read_manifest(os.path.join(out, "python"))
        self.assertEqual((manifest["language"], manifest["run"], manifest["convertedFrom"], manifest["routes"]), ("python", ["python3", "app.py"], "python", ROUTES))

    @unittest.skipUnless(NODE, "Node.js is not installed")
    def test_round_trip_through_another_language_returns_the_same_application(self):
        out = self.out("trip")
        first = V.convert(self.bundle, ["javascript"], out)[0]
        self.assertEqual(first["check"]["status"], "verified", first["check"]["detail"])
        again = V.capture(V.locate(os.path.join(out, "javascript")), probe=True)
        self.assertEqual(again["language"], "javascript")
        self.assertEqual(again["routes"], self.bundle["routes"])
        self.assertEqual(again["actions"], self.bundle["actions"])
        back = V.convert(again, ["python"], self.out("trip-back"))[0]
        self.assertEqual(back["check"]["status"], "verified", back["check"]["detail"])

    def test_verification_catches_a_project_that_differs(self):
        out = self.out("tampered")
        project = codegen.write_project("python", out, V.emit(self.bundle, "python").replace("Tide tables", "Tide charts"), V.SDKS)
        result = V.verify(self.bundle, project, out)
        self.assertEqual(result["status"], "failed")
        self.assertIn("/ differs from the source", result["detail"])
        broken = self.out("broken")
        project = codegen.write_project("python", broken, "raise SystemExit(3)\n", V.SDKS)
        self.assertEqual(V.verify(self.bundle, project, broken)["status"], "failed")
        wrong = self.out("wrong-handler")
        code = V.emit(self.bundle, "python").replace('"Link copied to the clipboard"', '"Copied"')
        project = codegen.write_project("python", wrong, code, V.SDKS)
        self.assertIn("handler `share` behaves differently", V.verify(self.bundle, project, wrong)["detail"])

    def test_a_missing_toolchain_is_reported_as_skipped(self):
        project = {"build": [["definitely-not-a-compiler", "x"]], "run": ["./app"]}
        self.assertEqual(V.missing_tools(project), ["definitely-not-a-compiler"])
        self.assertEqual(V.verify(self.bundle, project, self.tmp)["status"], "skipped")

    # -- scene files ---------------------------------------------------------------
    def test_scene_files_convert_too(self):
        path = os.path.join(self.tmp, "scenes.json")
        V.write_bundle(self.bundle, path)
        loaded = V.load_bundle(path)
        self.assertEqual(loaded["routes"], self.bundle["routes"])
        self.assertEqual(len(loaded["probes"]), len(self.bundle["probes"]))
        single = os.path.join(self.tmp, "pricing-page.json")
        with open(single, "w", encoding="utf-8") as fh:
            json.dump({"type": "Page", "props": {"title": "Pricing"}, "children": [{"type": "Text", "props": {"content": "Hello"}}]}, fh)
        bundle = V.load_bundle(single)
        self.assertEqual((bundle["name"], list(bundle["routes"])), ("Pricing Page", ["/"]))
        report = V.convert(bundle, ["python"], self.out("from-scene"))[0]
        self.assertEqual(report["check"]["status"], "verified", report["check"]["detail"])
        with open(single, "w", encoding="utf-8") as fh:
            json.dump([1, 2], fh)
        with self.assertRaises(V.ConvertError):
            V.load_bundle(single)

    # -- model-backed porting --------------------------------------------------------
    def test_a_translation_is_kept_only_if_it_verifies(self):
        good = V.emit(self.bundle, "python").replace("the handler is not ported yet", "ported")
        calls = []

        def model(capability, payload):
            calls.append((capability, payload["from"], payload["to"], "Field Notes" in payload["source"]))
            return {"ok": True, "data": {"code": "```python\n%s```" % good}, "provenance": {"provider": "openai"}}

        report = V.convert(self.bundle, ["python"], self.out("ported"), port=model)[0]
        self.assertEqual(calls, [("dev.port", "python", "python", True)])
        self.assertEqual(report["port"]["status"], "accepted", report["port"])
        self.assertTrue(report["ported"])
        main = os.path.join(self.tmp, "ported", "python", "app.py")
        self.assertIn('"Plan trip: ported"', read(main))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "ported", "python", "deterministic.py.txt")))

        bad = lambda capability, payload: {"ok": True, "data": {"code": good.replace("Tide tables", "Tide charts")}, "provenance": {"provider": "openai"}}
        report = V.convert(self.bundle, ["python"], self.out("rejected"), port=bad)[0]
        self.assertEqual(report["port"]["status"], "rejected")
        self.assertFalse(report["ported"])
        main = os.path.join(self.tmp, "rejected", "python", "app.py")
        self.assertIn("Tide tables", read(main), "the verified deterministic project is restored")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "rejected", "python", "ported.rejected.py.txt")))

        offline = lambda capability, payload: {"ok": True, "data": {"code": "print('skeleton')"}, "provenance": {"provider": "reflex"}}
        report = V.convert(self.bundle, ["python"], self.out("offline"), port=offline)[0]
        self.assertEqual(report["port"]["status"], "unavailable", "an offline skeleton is never treated as a translation")

    # -- command line ------------------------------------------------------------------
    def test_command_line_conversion_and_running_the_result(self):
        env = dict(os.environ, FLUIDIAN_OFFLINE="1", NO_COLOR="1")
        env.pop("OPENAI_API_KEY", None)
        out = self.out("cli")
        targets = "python,javascript" if NODE else "python"
        done = subprocess.run([sys.executable, CLI, "convert", APP, "--to", targets, "--probe", "--json", "-o", out], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=env, timeout=180)
        self.assertEqual(done.returncode, 0, done.stdout.decode()[-600:] + done.stderr.decode()[-600:])
        report = json.loads(done.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(report["routes"], ROUTES)
        self.assertEqual([t["check"]["status"] for t in report["targets"]], ["verified"] * len(targets.split(",")))
        self.assertEqual({h["action"]: h["status"] for h in report["handlers"]}, {"go": "observed", "share": "observed", "plan_trip": "stub", "export_notes": "stub"})
        self.assertTrue(os.path.isfile(os.path.join(out, "scenes.json")))
        text = subprocess.run([sys.executable, CLI, "convert", "--to", "python", "-o", self.out("cli2"), "--", sys.executable, APP], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env=dict(env, PYTHONPATH=os.path.join(support.ROOT, "sdks", "python")), timeout=180)
        self.assertEqual(text.returncode, 0, text.stdout.decode()[-600:] + text.stderr.decode()[-600:])
        self.assertIn("6 routes identical to the source", text.stdout.decode())
        self.assertIn("Handlers to finish", text.stdout.decode())
        self.assertIn("--probe", text.stdout.decode())
        missing = subprocess.run([sys.executable, CLI, "convert", os.path.join(self.tmp, "nope.py"), "--to", "go"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("does not exist", missing.stdout.decode())


if __name__ == "__main__":
    unittest.main()
