"""Design-token export, native shells, the installable web app and embedding."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom

import support
from fluidian import colors
from fluidian import platforms as P
from fluidian import server
from fluidian.server import Engine

CLI = os.path.join(support.ROOT, "fluidian")
QUICKSTART = os.path.join(support.ROOT, "sdks", "python", "examples", "quickstart.py")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class ThemeTest(unittest.TestCase):
    def test_twenty_presets_each_readable(self):
        self.assertEqual(len(colors.THEMES), 27)
        self.assertIn(colors.DEFAULT_THEME, colors.THEMES)
        for name, spec in colors.THEMES.items():
            with self.subTest(theme=name):
                t = {row["name"]: row["value"] for row in colors.preset_tokens(spec)}
                self.assertGreaterEqual(colors.contrast(t["--fl-text"], t["--fl-bg"]), 7.0)
                self.assertGreaterEqual(colors.contrast(t["--fl-text-2"], t["--fl-surface"]), 4.5)
                self.assertGreaterEqual(colors.contrast(t["--fl-on-brand"], t["--fl-brand"]), 4.5)
                self.assertGreaterEqual(colors.contrast(t["--fl-brand-text"], t["--fl-surface"]), 4.5)
                self.assertEqual(t["--fl-scheme"], "dark" if spec.get("dark") else "light")

    def test_presets_are_visibly_different(self):
        brands = {colors.THEMES[name]["brand"].lower() for name in colors.THEMES}
        self.assertGreaterEqual(len(brands), 18)
        self.assertGreaterEqual(sum(1 for s in colors.THEMES.values() if s.get("dark")), 4)
        self.assertGreaterEqual(len({str(s.get("display")) for s in colors.THEMES.values()}), 3, "themes vary their display typeface too")

    def test_generated_stylesheets_are_current(self):
        css = read(os.path.join(support.ROOT, "runtime", "themes.css"))
        js = read(os.path.join(support.ROOT, "runtime", "themes.js"))
        for name, spec in colors.THEMES.items():
            self.assertIn('[data-fl-theme="%s"]' % name, css)
            self.assertIn(colors.theme_css('[data-fl-theme="%s"]' % name, spec).strip().splitlines()[1].strip(), css, "run tools/build_tokens.py")
            self.assertIn('"%s"' % name, js)


class TokenExportTest(unittest.TestCase):
    def test_every_theme_exports_in_every_format(self):
        for theme in colors.theme_names():
            for fmt in P.TOKEN_FORMATS:
                with self.subTest(theme=theme, fmt=fmt):
                    text = P.export_tokens(theme, fmt)
                    self.assertGreater(len(text), 400)
                    self.assertNotIn("%(", text)
                    if fmt in ("json", "dtcg"):
                        json.loads(text)
                    if fmt == "android":
                        doc = xml.dom.minidom.parseString(text)
                        self.assertGreaterEqual(len(doc.getElementsByTagName("color")), 20)

    def test_values_agree_across_formats(self):
        _, tokens = P.theme_tokens("ocean")
        brand = tokens["brand"]
        r, g, b = (int(brand[i:i + 2], 16) for i in (1, 3, 5))
        self.assertIn("--fl-brand: %s;" % brand, P.export_tokens("ocean", "css"))
        self.assertIn("$fl-brand: %s;" % brand, P.export_tokens("ocean", "scss"))
        self.assertEqual(json.loads(P.export_tokens("ocean", "json"))["tokens"]["brand"], brand)
        self.assertEqual(json.loads(P.export_tokens("ocean", "dtcg"))["fluidian"]["color"]["brand"], {"$type": "color", "$value": brand})
        self.assertIn('"fl-brand": "%s"' % brand, P.export_tokens("ocean", "tailwind"))
        self.assertIn("static let brand = Color(red: %.3f, green: %.3f, blue: %.3f)" % (r / 255, g / 255, b / 255), P.export_tokens("ocean", "swift"))
        self.assertIn('<color name="fl_brand">#FF%s</color>' % brand[1:].upper(), P.export_tokens("ocean", "android"))
        self.assertIn("val Brand = Color(0xFF%s)" % brand[1:].upper(), P.export_tokens("ocean", "compose"))
        self.assertIn("static const brand = Color(0xFF%s);" % brand[1:].upper(), P.export_tokens("ocean", "flutter"))
        self.assertIn("static let brandSoft", P.export_tokens("ocean", "swift"))

    def test_scheme_can_be_forced_and_bad_input_is_refused(self):
        light, dark = json.loads(P.export_tokens("ocean", "json", "light")), json.loads(P.export_tokens("ocean", "json", "dark"))
        self.assertEqual((light["scheme"], dark["scheme"]), ("light", "dark"))
        self.assertNotEqual(light["tokens"]["bg"], dark["tokens"]["bg"])
        self.assertIn("prefersDark = true", P.export_tokens("midnight", "swift"))
        for theme, fmt in (("nope", "css"), ("ocean", "yaml")):
            with self.assertRaises(P.PlatformError):
                P.export_tokens(theme, fmt)

    @unittest.skipUnless(shutil.which("node") or shutil.which("nodejs"), "Node.js is not installed")
    def test_the_tailwind_preset_loads(self):
        folder = tempfile.mkdtemp(prefix="fluidian-tw-")
        try:
            path = os.path.join(folder, "preset.js")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(P.export_tokens("sunset", "tailwind"))
            script = "const p = require(%s); console.log(JSON.stringify(Object.keys(p.theme.extend)))" % json.dumps(path)
            done = subprocess.run([shutil.which("node") or shutil.which("nodejs"), "-e", script], stdout=subprocess.PIPE, check=True)
            self.assertEqual(json.loads(done.stdout), ["colors", "borderRadius", "fontFamily", "boxShadow"])
        finally:
            shutil.rmtree(folder, ignore_errors=True)


class PackageTest(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp(prefix="fluidian-native-")

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def test_ios_shell(self):
        result = P.package("ios", "Field Notes", "https://notes.example.com", self.out, theme="forest")
        self.assertEqual(result["files"], ["Package.swift", "README.md", os.path.join("Sources", "App.swift")])
        self.assertTrue(result["directory"].endswith(os.path.join("ios", "FieldNotes.swiftpm")))
        manifest, app = read(os.path.join(result["directory"], "Package.swift")), read(os.path.join(result["directory"], "Sources", "App.swift"))
        self.assertIn('bundleIdentifier: "dev.fluidian.fieldnotes"', manifest)
        self.assertIn(".iOSApplication(", manifest)
        self.assertIn('URL(string: "https://notes.example.com?platform=ios")', app)
        self.assertIn("struct FieldNotesApp: App", app)
        self.assertIn("WKWebView", app)
        self.assertEqual(app.count("{"), app.count("}"))
        self.assertEqual(app.count("("), app.count(")"))

    def test_android_shell(self):
        result = P.package("android", "Field Notes", "http://10.0.2.2:8787/?from=shell", self.out, app_id="com.example.notes")
        root = result["directory"]
        for rel in result["files"]:
            if rel.endswith(".xml"):
                xml.dom.minidom.parse(os.path.join(root, rel))
        activity = read(os.path.join(root, "app", "src", "main", "java", "com", "example", "notes", "MainActivity.kt"))
        self.assertTrue(activity.startswith("package com.example.notes\n"))
        self.assertIn('Uri.parse("http://10.0.2.2:8787/?from=shell&platform=android")', activity)
        self.assertEqual(activity.count("{"), activity.count("}"))
        gradle = read(os.path.join(root, "app", "build.gradle.kts"))
        self.assertIn('namespace = "com.example.notes"', gradle)
        self.assertIn('applicationId = "com.example.notes"', gradle)
        self.assertIn('android:usesCleartextTraffic="true"', read(os.path.join(root, "app", "src", "main", "AndroidManifest.xml")))
        self.assertIn("<string name=\"app_name\">Field Notes</string>", read(os.path.join(root, "app", "src", "main", "res", "values", "strings.xml")))
        secure = P.package("android", "Field Notes", "https://notes.example.com", os.path.join(self.out, "secure"))
        self.assertIn('android:usesCleartextTraffic="false"', read(os.path.join(secure["directory"], "app", "src", "main", "AndroidManifest.xml")))

    def test_desktop_shell(self):
        result = P.package("desktop", "Field Notes", "https://notes.example.com", self.out)
        package = json.loads(read(os.path.join(result["directory"], "package.json")))
        self.assertEqual((package["name"], package["main"], package["scripts"]["start"]), ("field-notes", "main.js", "electron ."))
        main = read(os.path.join(result["directory"], "main.js"))
        self.assertIn('const START = "https://notes.example.com?platform=desktop";', main)
        self.assertIn("contextIsolation: true", main)
        node = shutil.which("node") or shutil.which("nodejs")
        if node:
            self.assertEqual(subprocess.run([node, "--check", os.path.join(result["directory"], "main.js")]).returncode, 0)

    def test_names_and_addresses_are_validated(self):
        for kwargs in ({"url": "notes.example.com"}, {"url": "ftp://x"}, {"app_id": "notes"}, {"app_id": "1com.example"}, {"theme": "nope"}):
            args = dict({"url": "https://notes.example.com"}, **kwargs)
            with self.assertRaises(P.PlatformError):
                P.package("ios", "Field Notes", args.pop("url"), self.out, **args)
        with self.assertRaises(P.PlatformError):
            P.package("watch", "Field Notes", "https://notes.example.com", self.out)
        odd = P.package("ios", '9 "Lives" & <Co>', "https://x.example.com", self.out)
        self.assertTrue(os.path.basename(odd["directory"]).startswith("App9LivesCo"))
        self.assertIn('name: "9 \\"Lives\\" & <Co>"', read(os.path.join(odd["directory"], "Package.swift")))

    def test_command_line(self):
        env = dict(os.environ, NO_COLOR="1")
        run = lambda *args: subprocess.run([sys.executable, CLI] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=60)
        listing = run("tokens", "--list").stdout.decode()
        for name in colors.theme_names():
            self.assertIn(name, listing)
        self.assertEqual(json.loads(run("tokens", "--theme", "rose", "--format", "json").stdout)["theme"], "rose")
        done = run("tokens", "--theme", "all", "--format", "all", "-o", os.path.join(self.out, "tokens"))
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        self.assertIn("Wrote 243 token files", done.stdout.decode())
        self.assertEqual(len(os.listdir(os.path.join(self.out, "tokens", "ocean"))), 9)
        self.assertEqual(run("tokens", "--theme", "nope").returncode, 2)
        done = run("package", "all", "--name", "Field Notes", "--url", "https://notes.example.com", "-o", os.path.join(self.out, "native"))
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        self.assertEqual(sorted(os.listdir(os.path.join(self.out, "native"))), ["android", "desktop", "ios"])
        self.assertEqual(run("package", "ios", "--name", "X", "--url", "nope").returncode, 2)


class InstallAndEmbedTest(unittest.TestCase):
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

    def test_the_app_is_installable(self):
        status, headers, raw = support.http("GET", self.base + "/manifest.webmanifest")
        self.assertEqual(status, 200)
        self.assertIn("application/manifest+json", headers["Content-Type"])
        manifest = json.loads(raw)
        self.assertEqual((manifest["name"], manifest["display"], manifest["start_url"], manifest["scope"]), (self.engine.app_meta["name"], "standalone", "/", "/"))
        self.assertRegex(manifest["theme_color"], r"^#[0-9a-f]{6}$")
        self.assertEqual(sorted(i["purpose"] for i in manifest["icons"]), ["any", "any", "maskable"])
        for icon in manifest["icons"]:
            status, headers, raw = support.http("GET", self.base + icon["src"])
            self.assertEqual((status, headers["Content-Type"], raw[:8]), (200, "image/png", b"\x89PNG\r\n\x1a\n"), icon["src"])
        shell = support.http("GET", self.base + "/")[2].decode()
        for needle in ('rel="manifest" href="/manifest.webmanifest"', 'rel="apple-touch-icon"', 'name="theme-color"', "viewport-fit=cover"):
            self.assertIn(needle, shell)
        self.assertEqual(support.http("GET", self.base + "/_fluidian/runtime/pwa/apple-touch-icon.png")[0], 200)

    def test_the_service_worker_is_served_at_the_root_scope(self):
        status, headers, raw = support.http("GET", self.base + "/sw.js")
        self.assertEqual((status, headers.get("Service-Worker-Allowed")), (200, "/"))
        self.assertIn("javascript", headers["Content-Type"])
        text = raw.decode()
        self.assertIn('url.pathname.startsWith("/_fluidian/") && !asset', text, "API calls are never cached")
        self.assertIn("caches.open(CACHE)", text)

    def test_the_embed_element_is_served_for_other_origins(self):
        status, headers, raw = support.http("GET", self.base + "/_fluidian/embed.js")
        self.assertEqual((status, headers.get("Access-Control-Allow-Origin")), (200, "*"))
        self.assertIn(b'customElements.define("fluidian-app"', raw)
        self.assertIn(b"sandbox", raw)

    def test_framing_is_refused_unless_origins_are_listed(self):
        headers = support.http("GET", self.base + "/")[1]
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers.get("Cross-Origin-Opener-Policy"), "same-origin")
        self.assertIn("frame-ancestors 'self' https://www.example.com http://localhost:3000;", server.csp(["https://www.example.com", "http://localhost:3000"]))
        self.assertIn("frame-ancestors 'self' *;", server.csp(["*"]))
        self.assertIn("frame-ancestors 'none';", server.csp(["javascript:alert(1)", "https://a.example.com; script-src *", "'unsafe-inline'"]),
                      "anything that is not a plain origin is dropped")
        self.engine.cfg.embed_origins = ["https://www.example.com"]
        try:
            headers = support.http("GET", self.base + "/")[1]
            self.assertIn("frame-ancestors 'self' https://www.example.com;", headers["Content-Security-Policy"])
            self.assertNotIn("Cross-Origin-Opener-Policy", headers)
        finally:
            self.engine.cfg.embed_origins = []

    def test_embed_origins_come_from_the_environment(self):
        from fluidian.config import load_config
        saved = os.environ.get("FLUIDIAN_EMBED_ORIGINS")
        os.environ["FLUIDIAN_EMBED_ORIGINS"] = "https://www.example.com/, http://localhost:3000"
        try:
            self.assertEqual(load_config(cwd=tempfile.mkdtemp()).embed_origins, ["https://www.example.com", "http://localhost:3000"])
        finally:
            if saved is None:
                del os.environ["FLUIDIAN_EMBED_ORIGINS"]
            else:
                os.environ["FLUIDIAN_EMBED_ORIGINS"] = saved


if __name__ == "__main__":
    unittest.main()
