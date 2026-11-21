"""One interface, every platform.

A Fluidian application is a stream of scenes rendered by the runtime, so the
same application already runs in any browser, adapts its controls to iOS,
Android or desktop conventions (``runtime/platform.css``) and can be installed
from the browser as a web app. This module covers the two remaining bridges:

* :func:`export_tokens` writes a theme's design tokens in the formats other
  toolchains read: CSS, SCSS, JSON, the W3C design-tokens format, a Tailwind
  preset, SwiftUI, Android resources, Jetpack Compose and Flutter.
* :func:`package` writes starter shells that wrap a deployed application in a
  native window: an iOS app (SwiftUI and ``WKWebView``), an Android app
  (Kotlin and ``WebView``) and a desktop app (Electron).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml

from . import colors

TOKEN_FORMATS = ["css", "scss", "json", "dtcg", "tailwind", "swift", "android", "compose", "flutter"]
TOKEN_FILES = {"css": "fluidian-%s.css", "scss": "_fluidian-%s.scss", "json": "fluidian-%s.json", "dtcg": "fluidian-%s.tokens.json",
               "tailwind": "fluidian-%s.tailwind.js", "swift": "FluidianTheme.swift", "android": "fluidian_%s.xml", "compose": "FluidianTheme.kt",
               "flutter": "fluidian_theme.dart"}
PACKAGE_TARGETS = ["ios", "android", "desktop"]


class PlatformError(Exception):
    """A request that cannot be carried out as given."""


# --- tokens --------------------------------------------------------------------
def theme_tokens(theme: str, scheme: Optional[str] = None) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """``(spec, tokens)`` for a preset; ``scheme`` forces the light or dark variant."""
    if theme not in colors.THEMES:
        raise PlatformError("Unknown theme %r. Choose from: %s." % (theme, ", ".join(colors.theme_names())))
    spec = dict(colors.THEMES[theme])
    if scheme in ("light", "dark"):
        spec["dark"] = scheme == "dark"
    return spec, {t["name"][len("--fl-"):]: t["value"] for t in colors.preset_tokens(spec)}


def _camel(name: str, upper: bool = False) -> str:
    parts = re.split(r"[-_]", name)
    out = parts[0] + "".join(p.capitalize() for p in parts[1:])
    return out[0].upper() + out[1:] if upper else out


def _rgb(value: str) -> Tuple[int, int, int]:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _families(value: str) -> List[str]:
    return [part.strip().strip('"') for part in value.split(",")]


def export_tokens(theme: str, fmt: str, scheme: Optional[str] = None) -> str:
    """A theme's design tokens as text in ``fmt`` (one of :data:`TOKEN_FORMATS`)."""
    if fmt not in TOKEN_FORMATS:
        raise PlatformError("Unknown format %r. Choose from: %s." % (fmt, ", ".join(TOKEN_FORMATS)))
    spec, tokens = theme_tokens(theme, scheme)
    label = str(spec.get("label") or theme.capitalize())
    mode = tokens.get("scheme", "light")
    hues = {k: v for k, v in tokens.items() if re.match(r"^#[0-9a-fA-F]{6}$", v)}
    radius = int(re.sub(r"\D", "", tokens.get("radius", "12")) or 12)
    shadows = {k: v for k, v in tokens.items() if k.startswith("shadow-") or k == "inset"}
    note = 'Fluidian "%s" theme (%s). Written by `fluidian tokens --theme %s --format %s`.' % (label, mode, theme, fmt)
    if fmt == "css":
        return "/* %s */\n:root {\n%s}\n" % (note, "".join("  --fl-%s: %s;\n" % kv for kv in tokens.items()))
    if fmt == "scss":
        return "// %s\n%s" % (note, "".join("$fl-%s: %s;\n" % kv for kv in tokens.items()))
    if fmt == "json":
        return json.dumps({"theme": theme, "label": label, "scheme": mode, "tokens": tokens}, indent=2, ensure_ascii=False) + "\n"
    if fmt == "dtcg":
        doc = {"$description": note, "fluidian": {
            "color": {k: {"$type": "color", "$value": v} for k, v in hues.items()},
            "radius": {"base": {"$type": "dimension", "$value": "%dpx" % radius}},
            "font": {"body": {"$type": "fontFamily", "$value": _families(tokens["font"])},
                     "display": {"$type": "fontFamily", "$value": _families(tokens["font-display"])},
                     "display-weight": {"$type": "fontWeight", "$value": int(tokens.get("display-weight", "680"))}}}}
        return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if fmt == "tailwind":
        body = {"colors": {"fl-" + k: v for k, v in hues.items()}, "borderRadius": {"fl": "%dpx" % radius, "fl-lg": "%dpx" % round(radius * 1.5)},
                "fontFamily": {"fl": _families(tokens["font"]), "fl-display": _families(tokens["font-display"])},
                "boxShadow": {"fl-" + k.replace("shadow-", ""): v for k, v in shadows.items()}}
        return ("/** %s\n *  Use it as a preset: presets: [require(\"./%s\")]. Classes: bg-fl-brand, text-fl-text-2, rounded-fl, shadow-fl-2. */\n"
                "module.exports = %s;\n" % (note, TOKEN_FILES["tailwind"] % theme, json.dumps({"theme": {"extend": body}}, indent=2, ensure_ascii=False)))
    if fmt == "swift":
        rows = "".join("    public static let %s = Color(red: %.3f, green: %.3f, blue: %.3f)\n" % ((_camel(k),) + tuple(c / 255 for c in _rgb(v)))
                       for k, v in hues.items())
        return ("// %s\nimport SwiftUI\n\npublic enum FluidianTheme {\n%s    public static let radius: CGFloat = %d\n"
                "    public static let prefersDark = %s\n}\n" % (note, rows, radius, "true" if mode == "dark" else "false"))
    if fmt == "android":
        rows = "".join('    <color name="fl_%s">#FF%s</color>\n' % (k.replace("-", "_"), v[1:].upper()) for k, v in hues.items())
        comment = 'Fluidian "%s" theme (%s), exported with the fluidian tokens command.' % (label, mode)  # no double hyphen inside an XML comment
        return '<?xml version="1.0" encoding="utf-8"?>\n<!-- %s -->\n<resources>\n%s    <dimen name="fl_radius">%ddp</dimen>\n</resources>\n' % (xml(comment), rows, radius)
    if fmt == "compose":
        rows = "".join("    val %s = Color(0xFF%s)\n" % (_camel(k, True), v[1:].upper()) for k, v in hues.items())
        return ("// %s\npackage dev.fluidian.theme\n\nimport androidx.compose.ui.graphics.Color\nimport androidx.compose.ui.unit.dp\n\n"
                "object FluidianTheme {\n%s    val Radius = %d.dp\n    const val PrefersDark = %s\n}\n" % (note, rows, radius, "true" if mode == "dark" else "false"))
    rows = "".join("  static const %s = Color(0xFF%s);\n" % (_camel(k), v[1:].upper()) for k, v in hues.items())
    return ("// %s\nimport 'dart:ui';\n\nclass FluidianTheme {\n  const FluidianTheme._();\n\n%s  static const radius = %d.0;\n  static const prefersDark = %s;\n}\n"
            % (note, rows, radius, "true" if mode == "dark" else "false"))


# --- native shells ---------------------------------------------------------------
def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "app"


def _type_name(name: str) -> str:
    out = "".join(part.capitalize() for part in re.split(r"[^0-9a-zA-Z]+", name) if part) or "App"
    return out if out[0].isalpha() else "App" + out


def _with_platform(url: str, platform: str) -> str:
    return url + ("&" if "?" in url else "?") + "platform=" + platform


def package(target: str, name: str, url: str, out: str, app_id: Optional[str] = None, theme: str = colors.DEFAULT_THEME) -> Dict[str, Any]:
    """Write a starter shell for ``target`` that opens the application served at ``url``.

    Returns ``{"directory": ..., "files": [...], "next": [steps to build it]}``.
    The shells are source projects: building them needs Xcode, Android Studio
    or Node.js with Electron, which is why they are written rather than built.
    """
    if target not in PACKAGE_TARGETS:
        raise PlatformError("Unknown target %r. Choose from: %s." % (target, ", ".join(PACKAGE_TARGETS)))
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise PlatformError("--url must be the http(s) address the application is served at, for example https://app.example.com")
    if not app_id:
        tail = re.sub(r"[^a-z0-9]", "", name.lower())[:40]
        app_id = "dev.fluidian." + (tail if tail[:1].isalpha() else "app" + tail)
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$", app_id):
        raise PlatformError("--id must look like com.example.app")
    _, tokens = theme_tokens(theme)
    info = {"name": name, "type": _type_name(name), "slug": _slug(name), "id": app_id, "url": url, "host": parsed.hostname or "",
            "cleartext": parsed.scheme == "http", "brand": tokens["brand"], "bg": tokens["bg"], "dark": tokens.get("scheme") == "dark"}
    files, directory, steps = {"ios": _ios, "android": _android, "desktop": _desktop}[target](info, out)
    for rel, text in files.items():
        path = os.path.join(directory, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return {"target": target, "directory": directory, "files": sorted(files), "next": steps}


def _readme(info: Dict[str, Any], platform: str, steps: List[str], notes: List[str]) -> str:
    lines = ["# %s for %s" % (info["name"], platform), "",
             "A thin native shell around the Fluidian application served at <%s>." % info["url"],
             "The interface is rendered by the Fluidian runtime inside the system web view, with the %s control skin." % platform, "",
             "## Build", ""] + ["%d. %s" % (i + 1, step) for i, step in enumerate(steps)] + ["", "## Notes", ""] + ["- " + n for n in notes]
    return "\n".join(lines) + "\n"


def _ios(info: Dict[str, Any], out: str) -> Tuple[Dict[str, str], str, List[str]]:
    directory = os.path.join(out, "ios", "%s.swiftpm" % info["type"])
    start = _with_platform(info["url"], "ios")
    r, g, b = (c / 255 for c in _rgb(info["bg"]))
    package_swift = '''// swift-tools-version: 5.9
import PackageDescription
import AppleProductTypes

let package = Package(
    name: %(name)s,
    platforms: [.iOS("16.0")],
    products: [
        .iOSApplication(
            name: %(name)s,
            targets: ["AppModule"],
            bundleIdentifier: %(id)s,
            teamIdentifier: "",
            displayVersion: "1.0",
            bundleVersion: "1",
            appIcon: .placeholder(icon: .sparkle),
            accentColor: .presetColor(.indigo),
            supportedDeviceFamilies: [.pad, .phone],
            supportedInterfaceOrientations: [
                .portrait,
                .landscapeRight,
                .landscapeLeft,
                .portraitUpsideDown(.when(deviceFamilies: [.pad]))
            ]
        )
    ],
    targets: [
        .executableTarget(name: "AppModule", path: "Sources")
    ]
)
''' % {"name": json.dumps(info["name"]), "id": json.dumps(info["id"])}
    app_swift = '''import SwiftUI
import WebKit

/// Where the application is served. The `platform` hint selects the iOS control skin.
let startURL = URL(string: %(url)s)!

@main
struct %(type)sApp: App {
    var body: some Scene {
        WindowGroup {
            WebShell(url: startURL)
                .ignoresSafeArea(.container, edges: .bottom)
                .background(Color(red: %(r).3f, green: %(g).3f, blue: %(b).3f))
        }
    }
}

struct WebShell: UIViewRepresentable {
    let url: URL

    func makeCoordinator() -> Coordinator { Coordinator(home: url) }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        let hint = WKUserScript(source: "window.FluidianHost = { platform: 'ios', shell: 'native' };",
                                injectionTime: .atDocumentStart, forMainFrameOnly: true)
        configuration.userContentController.addUserScript(hint)
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.allowsBackForwardNavigationGestures = true
        view.isOpaque = false
        view.backgroundColor = .clear
        view.load(URLRequest(url: url))
        return view
    }

    func updateUIView(_ view: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate {
        let home: URL

        init(home: URL) { self.home = home }

        /// Links that leave the application open in the browser instead of inside the shell.
        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            if let target = action.request.url, action.navigationType == .linkActivated, target.host != home.host {
                UIApplication.shared.open(target)
                decisionHandler(.cancel)
            } else {
                decisionHandler(.allow)
            }
        }
    }
}
''' % {"url": json.dumps(start), "type": info["type"], "r": r, "g": g, "b": b}
    steps = ["Open `%s.swiftpm` in Xcode 15 or later, or in Swift Playgrounds on an iPad." % info["type"],
             "Choose a simulator or a device and press Run.",
             "To ship it, set your team under Signing and replace the placeholder icon."]
    notes = ["The shell loads `%s`." % start,
             "Use an `https` address for anything beyond local testing: iOS refuses plain `http` unless an App Transport Security exception is added."
             if info["cleartext"] else "The address is `https`, so no App Transport Security exception is needed.",
             "The shell is deliberately small: one `WKWebView`, back and forward swipes, external links handed to Safari.",
             "This project is written by `fluidian package ios`; it is source, and has to be built with Apple's tools on a Mac."]
    return {"Package.swift": package_swift, os.path.join("Sources", "App.swift"): app_swift,
            "README.md": _readme(info, "iOS", steps, notes)}, directory, steps


def _android(info: Dict[str, Any], out: str) -> Tuple[Dict[str, str], str, List[str]]:
    directory = os.path.join(out, "android")
    start = _with_platform(info["url"], "android")
    src = os.path.join("app", "src", "main")
    files = {
        "settings.gradle.kts": '''pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = %s
include(":app")
''' % json.dumps(info["type"]),
        "build.gradle.kts": '''plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
}
''',
        "gradle.properties": "org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8\nandroid.useAndroidX=true\nkotlin.code.style=official\n",
        os.path.join("gradle", "wrapper", "gradle-wrapper.properties"):
            "distributionBase=GRADLE_USER_HOME\ndistributionPath=wrapper/dists\n"
            "distributionUrl=https\\://services.gradle.org/distributions/gradle-8.7-bin.zip\nzipStoreBase=GRADLE_USER_HOME\nzipStorePath=wrapper/dists\n",
        os.path.join("app", "build.gradle.kts"): '''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = %(id)s
    compileSdk = 34

    defaultConfig {
        applicationId = %(id)s
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}
''' % {"id": json.dumps(info["id"])},
        os.path.join(src, "AndroidManifest.xml"): '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme"
        android:usesCleartextTraffic="%s">
        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|screenSize|keyboardHidden"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
''' % ("true" if info["cleartext"] else "false"),
        os.path.join(src, "java", *info["id"].split("."), "MainActivity.kt"): '''package %(id)s

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient

/** A single web view that shows the Fluidian application; the `platform` hint selects the Android control skin. */
class MainActivity : Activity() {
    private lateinit var web: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.webViewClient = object : WebViewClient() {
            // Links that leave the application open in the browser instead of inside the shell.
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                if (request.url.host == START.host) return false
                startActivity(Intent(Intent.ACTION_VIEW, request.url))
                return true
            }
        }
        setContentView(web)
        if (savedInstanceState == null) web.loadUrl(START.toString()) else web.restoreState(savedInstanceState)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        web.saveState(outState)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    private companion object {
        val START: Uri = Uri.parse(%(url)s)
    }
}
''' % {"id": info["id"], "url": json.dumps(start)},
        os.path.join(src, "res", "values", "strings.xml"):
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <string name="app_name">%s</string>\n</resources>\n' % xml(info["name"]),
        os.path.join(src, "res", "values", "colors.xml"):
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="fl_brand">#FF%s</color>\n    <color name="fl_bg">#FF%s</color>\n</resources>\n'
            % (info["brand"][1:].upper(), info["bg"][1:].upper()),
        os.path.join(src, "res", "values", "themes.xml"): '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="android:Theme.Material%s.NoActionBar">
        <item name="android:windowBackground">@color/fl_bg</item>
        <item name="android:statusBarColor">@color/fl_bg</item>
        <item name="android:navigationBarColor">@color/fl_bg</item>
        <item name="android:windowLightStatusBar">%s</item>
    </style>
</resources>
''' % ("" if info["dark"] else ".Light", "false" if info["dark"] else "true"),
        os.path.join(src, "res", "mipmap-anydpi-v26", "ic_launcher.xml"): '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/fl_brand" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
''',
        os.path.join(src, "res", "drawable", "ic_launcher_foreground.xml"): '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M55,32c8,9 14,17 14,25a15,15 0,0 1,-30 0c0,-7 5,-13 9,-18c1,4 3,6 5.500,7c-1.500,-5 -0.500,-10 1.500,-14z" />
</vector>
''',
    }
    steps = ["Open the `android` folder in Android Studio (Koala or later) and let it sync.",
             "Choose an emulator or a device and press Run.",
             "To ship it, set your own `applicationId` and signing configuration, and replace the launcher icon."]
    notes = ["The shell loads `%s`." % start,
             "Plain `http` is allowed because the address is not `https`; switch to `https` before publishing."
             if info["cleartext"] else "Cleartext traffic is disabled because the address is `https`.",
             "From the emulator, a server on your computer is reachable at `http://10.0.2.2:<port>`, not at `127.0.0.1`.",
             "The shell has no dependencies beyond the Android SDK: one `WebView`, the back button, external links handed to the browser.",
             "This project is written by `fluidian package android`; it is source, and has to be built with the Android toolchain."]
    files["README.md"] = _readme(info, "Android", steps, notes)
    return files, directory, steps


def _desktop(info: Dict[str, Any], out: str) -> Tuple[Dict[str, str], str, List[str]]:
    directory = os.path.join(out, "desktop")
    start = _with_platform(info["url"], "desktop")
    main_js = '''// %(name)s: a desktop window around the Fluidian application served at START.
const { app, BrowserWindow, shell } = require("electron");

const START = %(url)s;

function createWindow() {
  const win = new BrowserWindow({
    width: 1320,
    height: 880,
    minWidth: 420,
    minHeight: 520,
    title: %(title)s,
    backgroundColor: %(bg)s,
    autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false },
  });
  win.loadURL(START);
  // Links that leave the application open in the system browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (event, url) => {
    if (new URL(url).origin !== new URL(START).origin) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
}

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
''' % {"name": info["name"], "url": json.dumps(start), "title": json.dumps(info["name"]), "bg": json.dumps(info["bg"])}
    package_json = json.dumps({"name": info["slug"], "productName": info["name"], "version": "1.0.0", "private": True, "main": "main.js",
                               "description": "%s, a Fluidian application in a desktop window." % info["name"],
                               "scripts": {"start": "electron ."}, "devDependencies": {"electron": "^31.0.0"}}, indent=2) + "\n"
    steps = ["Run `npm install` in the `desktop` folder (this downloads Electron).", "Run `npm start`.",
             "To make installers, add a packager such as electron-builder."]
    notes = ["The window loads `%s`." % start,
             "No Node.js APIs are exposed to the page: context isolation and the sandbox are on.",
             "Without Electron, any Chromium browser gives a similar window: `chromium --app=%s`." % start,
             "This project is written by `fluidian package desktop`; `npm install` needs network access."]
    return {"main.js": main_js, "package.json": package_json, "README.md": _readme(info, "desktop", steps, notes)}, directory, steps
