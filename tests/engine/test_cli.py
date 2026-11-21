"""The command-line interface, run exactly as a user would run it."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import support

CLI = os.path.join(support.ROOT, "fluidian")


def run(*args, **kw):
    env = dict(os.environ, FLUIDIAN_OFFLINE="1", NO_COLOR="1")
    env.pop("OPENAI_API_KEY", None)
    return subprocess.run([sys.executable, CLI] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=120, **kw)


class CliTest(unittest.TestCase):
    def test_version(self):
        done = run("version")
        self.assertEqual(done.returncode, 0)
        self.assertIn("1.2.0", done.stdout.decode())

    def test_catalogues_as_json(self):
        features = json.loads(run("features", "--json").stdout)
        self.assertEqual(len(features["capabilities"]), 185)
        self.assertEqual(len(features["categories"]), 15)
        self.assertEqual(len(json.loads(run("components", "--json").stdout)["components"]), 123)
        trust = json.loads(run("features", "--category", "trust", "--json").stdout)["capabilities"]
        self.assertEqual({f["id"].split(".")[0] for f in trust}, {"trust"})

    def test_invoke_a_capability_from_the_terminal(self):
        done = run("ai", "input.natural_quantity", "--input", '{"text": "2.5 tonnes"}')
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        self.assertIn('"kg"', done.stdout.decode())
        self.assertNotEqual(run("ai", "nope.nothing").returncode, 0)

    def test_doctor_passes_offline(self):
        done = run("doctor")
        self.assertEqual(done.returncode, 0, done.stdout.decode()[-600:])
        self.assertIn("Reflex provider", done.stdout.decode())
        self.assertIn("toolchains available", done.stdout.decode())

    def test_scaffolds_run_for_every_language(self):
        from fluidian.codegen import LANGS
        from fluidian import components as C
        from fluidian.testkit import conformance as CF
        base = tempfile.mkdtemp(prefix="fluidian-new-")
        try:
            for lang in LANGS:
                target = os.path.join(base, lang)
                done = run("new", lang, target, "--name", "Demo", "--describe", "contact form with name, email and message")
                self.assertEqual(done.returncode, 0, "%s: %s" % (lang, done.stderr.decode()[-400:]))
                self.assertTrue(os.listdir(target), lang)
                self.assertIn("run --", done.stdout.decode(), "the command prints how to run the project")
            again = run("new", "python", os.path.join(base, "python"))
            self.assertNotEqual(again.returncode, 0, "a non-empty directory is not overwritten without --force")
            # The Python scaffold is executed through the wire protocol.
            app = os.path.join(base, "python", "app.py")
            tc = CF.toolchain("python")
            steps = [({"t": "open", "sid": "n1", "route": "/", "locale": "en-US", "viewport": {"w": 1280, "h": 800}}, 1, False), ({"t": "shutdown"}, 0, False)]
            got = CF.transcript([tc["run"][0], app], tc["env"], base, steps=steps)
            self.assertEqual([m["t"] for m in got], ["ready", "scene", "exit"])
            kinds = {n["type"] for n, _, _ in C.walk(got[1]["root"])}
            self.assertTrue({"Form", "Input"} <= kinds, kinds)
        finally:
            shutil.rmtree(base, ignore_errors=True)

    @unittest.skipUnless(shutil.which("node") or shutil.which("nodejs"), "Node.js is not installed")
    def test_static_export(self):
        folder = tempfile.mkdtemp(prefix="fluidian-export-")
        try:
            scene = os.path.join(folder, "scene.json")
            with open(scene, "w", encoding="utf-8") as fh:
                json.dump({"type": "Page", "props": {"title": "Exported"}, "children": [{"type": "Text", "props": {"content": "<b>escaped</b>"}},
                                                                                         {"type": "Stat", "props": {"label": "Orders", "value": "18,238"}}]}, fh)
            done = run("export", scene, "--out", os.path.join(folder, "out.html"))
            self.assertEqual(done.returncode, 0, done.stderr.decode()[-400:])
            with open(os.path.join(folder, "out.html"), encoding="utf-8") as fh:
                html = fh.read()
            self.assertIn("Exported", html)
            self.assertIn("18,238", html)
            self.assertIn("&lt;b&gt;escaped&lt;/b&gt;", html)
            self.assertNotIn("<b>escaped</b>", html)
            self.assertIn("<style>", html, "the export is a single self-contained file")
        finally:
            shutil.rmtree(folder, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
