# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/). The wire protocol has its own
integer version, independent of the release number.

## [Unreleased]

Repairs to the repository itself: a source file that git was told to ignore, and two things the workflow log complained about.

### Fixed
- **The Dart SDK failed in every clone: `sdks/dart/bin/conformance.dart` could not be found.** The ignore rule
  `bin/`, written for .NET build output, also matched `sdks/dart/bin`, the folder that holds the Dart conformance app.
  A file hidden this way is present where it was written and absent from every clone, which is how the suite could pass
  on one machine and fail in continuous integration. The folder is now exempt from the rule, and the conformance app
  and its generated scene are in the repository.
- The check for stale generated files left out every folder named `bin`, so the Dart conformance scene was the one
  generated file it never looked at. Only the `bin` and `obj` folders of the .NET projects are left out now.
- **A test run left .NET build servers running.** `dotnet build` keeps an MSBuild node and the C# compiler server alive
  for several minutes to make the next build faster, and GitHub Actions reported both as orphan processes when the job
  ended. Builds started by `fluidian test` now ask for neither to be kept. What is built is the same.

### Changed
- The workflow uses `actions/checkout@v7`. Version 4 runs on Node.js 20, which GitHub Actions has deprecated, and every
  job carried a warning about it. The example workflow in the testing guide is updated to match.
- `make clean` also removes `sdks/dart/pubspec.lock`, which `dart run` writes beside the conformance app.
- `.editorconfig` no longer asks for four-space indentation in Dart files, which are written with two.

### Added
- 1 test: nothing under `sdks/` or `spec/` that belongs in the repository may be hidden by an ignore rule. It names the
  file and the rule, and it fails on the rule that caused the failure above.

## [1.2.0] — 2026-11-20

A new identity, seven more themes, and a clean-up check that no longer depends on how a system presents its processes.

### Fixed
- **`test_a_browser_abandoned_by_an_interrupted_run_is_found_and_closed` failed with `0 != 1` on some systems.** The
  clean-up introduced in 1.1.1 recognised an abandoned browser by reading the process table: its command line, and
  whether a Python process was among its ancestors. Neither is dependable. A system may end a browser together with
  the process that started it, an orphan may be adopted by a session manager that is itself written in Python, and a
  packaged browser may run behind wrappers or with a private `/tmp`. The harness now writes a small record for every
  browser it starts and keeps it locked while it runs. A record whose lock is free belongs to a launcher that is gone;
  if the browser it names still answers on its debugging port with the id that was written down, it is closed over that
  port. Nothing is inferred from the process table, and a browser that is in use can never be taken for a leftover.
- The test itself now accepts both outcomes a system can produce, the browser survives its launcher and is cleaned up,
  or the system has already ended it, and a failure prints what the clean-up could see (records, port, process chain).
- A browser that could not be stopped keeps its record, so the next run tries again instead of losing track of it.

### Changed
- **New logo and wordmark in the Deep Blue palette.** The mark is a ribbon: one stroke bends from the top arm of an F
  into its stem, and the crossbar is a wave. It runs from white into sky blue `#7ec8e3` on a tile that falls from pure
  blue `#0000ff` through navy `#000c66` into midnight `#050a30`. The wordmark is set in outlined Inter, so it needs no
  font, and comes in a light and a dark version. The favicon, the installable-app icons, the README banner and the
  collage are redrawn to match. The palette is defined once (`BRAND` in `engine/fluidian/colors.py`).
- **The brand is no longer the colour of everything.** The palette above belongs to the logo, the default theme and the
  default dark scheme only. The showcase now spreads its 85 screens over all twenty-seven presets, with no preset on
  more than six of them, and the gallery pages in the documentation are captured in twenty-three presets besides the default.
- The default theme is the new `deep` preset; `iris` remains as a violet preset of its own.
- The gallery's rail, DevTools and the showcase header draw the new mark. `logo="fluidian"` on `NavBar` or `Footer`
  draws it in your own pages; demo brands still get neutral geometric marks and are never given Fluidian's.
- All 122 documentation screenshots were captured again.

### Added
- **Seven vivid presets**, for twenty-seven in all: `deep` (pure blue on white), `abyss` (blue on midnight), `emerald`
  (green on white), `neon` (magenta and cyan on black), `ruby` (red on white), `lagoon` (teal on deep blue-green) and
  `tangerine` (orange on white). Like the others they are generated in OKLCH and checked for contrast.
- `tools/brand.py` regenerates every brand asset from one definition, and `runtime/brand.js` carries the mark for the runtime.
- `FLUIDIAN_STATE_DIR` chooses where launch records are kept (by default a private folder in the temporary directory).
- 11 tests for launch records, 10 for the brand assets and the spread of themes, 2 more browser tests and 1 runtime test.

## [1.1.1] — 2026-11-20

A fix for the browser test suite, and a harness that cleans up after itself.

### Fixed
- **The browser suite failed in clean-up on systems that refuse to signal the browser.** With a sandboxed browser, such as
  the snap-packaged Chromium on Ubuntu, sending it a signal can fail with `PermissionError: [Errno 13] Permission denied`.
  All tests passed and the run was then reported as failed. The browser is now asked to exit over the DevTools protocol,
  signals are only a fallback, and a refused signal is no longer an error.
- That failure also skipped the rest of the clean-up, leaving the test's gallery and showcase servers and its headless
  browser running. The next browser test or screenshot run now finds and removes them, and says so in the summary.
- A hung suite is reported as a failed suite with its output instead of stopping the test runner with a traceback.

### Changed
- The browser tests choose three free ports at run time instead of the fixed ports 8795 to 8797. `FLUIDIAN_TEST_PORT`
  still pins them.
- Servers started by the tests and the screenshot tool are tied to the process that started them: with
  `FLUIDIAN_LIFELINE=stdin` the engine exits when its standard input closes, so it cannot outlive an interrupted run.
- A server must return its start-up token (`FLUIDIAN_INSTANCE`, echoed by `/healthz`) before it is used, and a busy port
  is reported at once, so a stale server is never mistaken for a fresh one.
- Every place that stops a child process, in the engine, the converter, the conformance harness and the tools, goes
  through one helper that never raises.

### Added
- `engine/fluidian/procs.py` and its tests: 21 engine tests and 3 browser tests covering refused signals, the lifeline,
  busy ports and leftovers.

## [1.1.0] — 2026-11-19

Write once: every language, every platform. A new visual system and 85 complete screens.

### Design
- A new look for every component: refined type, spacing and elevation, with the structure of existing screens unchanged.
- Twenty theme presets (`iris`, `midnight`, `aurora`, `sunset`, `ember`, `ocean`, `forest`, `moss`, `rose`, `grape`, `citrus`, `sand`,
  `graphite`, `paper`, `terminal`, `crimson`, `candy`, `mint`, `gold`, `sky`). A preset sets colour, radius, depth and display
  typeface together. Apply one with the `Theme` component, `?theme=`, or the `theme` attribute of an embed.
- Three more bundled typefaces: Space Grotesk, Instrument Serif and JetBrains Mono (SIL Open Font License).
- 106 more icons, 182 in all. Syntax colouring in `Code`. Smoother charts with gradient areas.

### Components
- 49 new components, 123 in all, in nine families.
- Marketing: `Landing`, `NavBar`, `Band`, `Bento`, `BentoCell`, `Feature`, `LogoCloud`, `Metrics`, `Testimonial`, `PricingCard`,
  `Comparison`, `FAQ`, `CTA`, `Footer`, `PromoTile`.
- Commerce: `ProductCard`, `Cart`, `OrderSummary`, `RatingSummary`, `MediaGallery`, with `Swatches`, `Quantity` and `PinInput` inputs.
- Visualisation: `Sparkline`, `Rings`, `Gauge`, `Heatmap`, `BarList`, `Ticker`, `Funnel`, `Waveform`, `Candles`, `MapView`, `Calendar`,
  `Schedule`, `Roadmap`.
- Product surfaces: `Chat`, `Terminal`, `Player`, `PromptBox`, `AvatarStack`, `ControlTile`.
- `Art`: procedural artwork in 44 kinds, drawn as SVG, so screens need no image files.
- `Screen` and `DeviceFrame` for mobile screens and device previews.

### Portable logic
- `State`, `Show` and `Each` components, `{{ }}` bindings in any string prop, a `bind` prop for two-way binding, and actions
  that start with `@` and run in the runtime: assignment, arithmetic, `toggle`, `push`, `remove`, `clear`, `go`, `toast`, `emit`
  and `ask` (which calls the AI kernel and stores the answer in page state).
- A parser and interpreter with no `eval`; it cannot reach prototypes or globals.
- In development mode, logic that does not parse is listed beside scene repairs.

### Every language
- `fluidian convert`: write an application in any other SDK language and verify the result. It captures the scene of every
  route from the running application, emits one function per route in the target language, builds and runs the generated
  project, and compares every scene with the source. Sources can be files, project folders, commands or scene files.
- `--probe` reproduces handlers that only notify or navigate, and replays them against the result. `--port-handlers`
  translates handler code with `dev.port` and keeps a translation only if the project still verifies.
- `fluidian run` accepts a source file or a project folder as well as a command. Projects written by `new` and `convert`
  carry a `fluidian.project.json` manifest.
- The SDK test phase now also converts a six-route application into each language and checks it.

### Every platform
- Platform skins: the runtime applies iOS or Android control conventions from the user agent, `?platform=`, or a native shell.
- Components respond to their container rather than the window, so one scene fits a phone, a tablet and a wide screen.
- Installable web app: the engine serves a manifest, icons and a service worker that keeps the shell available offline.
- `<fluidian-app>`: embed an application in any page. Framing stays refused unless `FLUIDIAN_EMBED_ORIGINS` lists the host.
- `fluidian package ios|android|desktop`: native shell projects in source form (SwiftUI, Kotlin, Electron).
- `fluidian tokens`: export any theme as CSS, SCSS, JSON, W3C design tokens, a Tailwind preset, SwiftUI, Android resources,
  Jetpack Compose or Flutter.

### Examples and documentation
- `fluidian showcase`: 85 complete screens in six groups: landing pages, storefronts, dashboards, AI products, mobile and
  cross-platform, and application modules.
- The gallery gained pages for portable logic, the platform preview, and artwork and themes.
- `examples/portable`: a small application that converts to every language.
- 122 screenshots, all captured from the running framework, with a page that lists each one with its route and theme.
- New guides: Why Fluidian, Portable logic, Converting between languages, Cross-platform. Theming rewritten.
- `scripts/setup-ubuntu.sh`, `scripts/set-api-key.sh` and `scripts/test-all.sh` for a three-command start.

### Fixed
- The Rust handler emitted by `fluidian new` did not return a result and failed to compile when a scene bound an action.
- A `?theme=` request was discarded when the scene had no `Theme` root.
- Stat tiles placed directly in a row collapsed to their padding.
- An application started by the engine could import the engine package instead of the Python SDK when both were on the path.

## [1.0.0] — 2026-11-19

First public release.

### Engine
- Server-driven UI engine with a JSON Lines wire protocol (version 1), session
  isolation, server-sent events and a no-build browser runtime.
- AI kernel with a fifteen-stage pipeline: policy, consent, input validation,
  redaction, injection shield, moderation, cache, coalescing, budget, routing,
  model or Reflex execution, output validation with self-repair, grounding,
  restoration and provenance.
- 185 capabilities in 15 families: 122 model capabilities, 19 hybrid and 44
  direct. Every capability also runs offline through the Reflex engine.
- OpenAI integration through strict Structured Outputs, with model discovery,
  tier fallback chains and adaptive parameter negotiation.
- 74 components with one registry that drives validation, code generation,
  documentation and the conformance suite.

### SDKs
- Fourteen languages: C++, C#, Dart, Elixir, Go, Java, JavaScript, Kotlin,
  Lua, PHP, Python, Ruby, Rust and TypeScript. None has a runtime dependency.
- Component factories generated from the registry for every language.

### Tooling
- `fluidian` command line: run, serve, gallery, test, doctor, features,
  components, ai, new, codegen, docs, export.
- Test suite: engine and end-to-end tests, runtime tests, a conformance
  transcript shared by all SDKs, and optional headless-browser checks.
- Gallery application with 30 pages and in-browser developer tools.
