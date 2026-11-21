<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Testing

Fluidian is tested by one command that needs no network, no API key and no supervision.

```bash
./fluidian test
```

```text
Fluidian 1.2.0  test run

  PASS  Engine, kernel, server and CLI              18.4s  191 tests
  PASS  Browser runtime (Node.js)                    0.5s  31 tests
  PASS  SDK · Python                                 0.3s  conformance, quickstart, scaffold and conversion verified
  PASS  SDK · JavaScript                             0.2s  conformance, quickstart, scaffold and conversion verified
  …
  PASS  SDK · Lua                                    0.1s  conformance, quickstart, scaffold and conversion verified
  PASS  Gallery and showcase in headless Chrome     73.2s  24 tests

17 passed, 0 failed, 0 skipped  in 142.1s
All checks that could run have passed.
```

That is a run with `--browser` on the machine the release was verified on. `bash scripts/test-all.sh` runs the same thing, adds the browser suite when Chrome is installed, and ends with one line: `RESULT: ALL TESTS PASSED` or `RESULT: SOME TESTS FAILED`.

The exit status is 0 only when nothing failed. A suite that cannot run because a tool is missing is reported as `SKIP` with the reason, and never counted as a pass.

## Options

| Command | Runs |
| --- | --- |
| `./fluidian test` | Engine, runtime and every SDK |
| `./fluidian test --quick` | Engine and runtime only |
| `./fluidian test --sdk rust --sdk go` | Only the named SDKs |
| `./fluidian test --no-sdks` | Everything except the SDKs |
| `./fluidian test --browser` | Adds the headless-Chrome suite |
| `./fluidian test --json` | The same results as JSON, for CI |
| `./fluidian test -v` | Full output of every suite |

`make test`, `make test-quick` and `make test-browser` are shortcuts for the same commands.

## The suites

### Engine — `tests/engine/`

Python `unittest`, standard library only.

| File | Covers |
| --- | --- |
| `test_schema.py` | The schema notation, strict compilation, validation, synthesis |
| `test_colors.py` | OKLCH conversion, contrast measurement and repair, ramps, theme tokens |
| `test_components.py` | The registry, normalisation and its repairs, id stability, transport encoding, diffing, hostile input |
| `test_reflex.py` | The offline engine: dates, quantities, format repair, smart paste, anomalies, queries, forecasts, routing, planning, composition, HTML import |
| `test_kernel.py` | Contracts for all 185 capabilities, determinism, consent, policy, redaction, injection shield, grounding, theme contrast, telemetry |
| `test_provider.py` | The model path against a mock of the OpenAI API: strict schemas for every model capability, negotiation, retries, fallback, repair, caching, redaction, budgets |
| `test_server.py` | A real app process end to end: sessions, events, streaming, tokens, origin and host checks, body limits, static files, throttling |
| `test_cli.py` | The command line as a user runs it, including scaffolding in all fourteen languages and static export |
| `test_gallery.py` | Every gallery page renders with zero scene repairs |
| `test_showcase.py` | All 85 showcase screens render with zero scene repairs, each in its own theme; every theme and every marketing, commerce and visual component is exercised |
| `test_convert.py` | Route discovery, capture, handler plans, emission in all fourteen languages, verification, detection of a project that differs, scene files, the gate on model translations, and the command line |
| `test_platforms.py` | The twenty-seven themes and their contrast, token export in nine formats, the iOS, Android and desktop shells, the web app manifest, the service worker, the embed element and the framing policy |
| `test_procs.py` | Stopping child processes when a signal is refused, the server lifeline, start-up on a busy port, launch records, and recognising what an interrupted run left behind |
| `test_brand.py` | Every copy of the logo draws the same mark in the brand colours, the wordmark is outlined, the app icons have the declared sizes, nothing still carries the previous logo, and the showcase uses every preset without leaning on one |
| `test_codegen.py` | Generated SDK sources and published specs are current, and no source file under `sdks/` or `spec/` is hidden by `.gitignore` |

### Runtime — `tests/runtime/`

Node's built-in test runner; needs Node.js 18 or newer and no packages.

- Every component renders on the server and produces tagged, well-formed markup.
- Every component survives missing props and props of the wrong shape.
- Text, attributes, Markdown and URLs are escaped or neutralised; model output is treated like any other untrusted text.
- Every capability's surface exists, and no presenter throws with a result, without one, or with an error.
- Portable logic: the expression language, the function library, bindings, every action, the host API, the store, `State`, `Show` and `Each`, the lint for logic that does not parse, and the sandbox (no access to prototypes or globals, no prototype pollution).

### SDK — the conformance harness

For each language the harness builds four programs and drives them over pipes:

1. the **conformance app**, compared message by message with `spec/conformance/golden.json`;
2. the **quickstart example**, compared with the Python quickstart's transcript;
3. a **scaffolded project** from `fluidian new`, which must build and serve its first scene;
4. a **converted application**: `examples/portable/app.py` written in that language by `fluidian convert`, which must build, serve all six routes identically to the source and reproduce the observed handlers.

A failure names the first differing message and the JSON path inside it. See [the protocol](protocol.md#the-conformance-suite) for what the transcript covers.

Builds started by a test run do not keep .NET's build servers, so no MSBuild node or compiler server is left running when the run ends.

### Browser — `tests/browser/`

Opt-in with `--browser`; needs Chrome or Chromium (set `FLUIDIAN_BROWSER` to choose the binary). A small DevTools-protocol driver, also standard library only, starts the gallery and the showcase and checks that:

- every gallery page and every one of the 85 showcase screens loads with no runtime error, no scene repair and no unparseable logic;
- navigation is client-side, generated regions appear and can be refined, fields parse natural language, and the table filter, Intent Bar and command palette work;
- portable logic changes the page without sending a single event to the application, and `@ask` reaches the kernel;
- theme presets restyle a page, platform skins follow the request, the same scene reflows in a phone, a tablet and a browser frame, and a phone-sized viewport does not overflow;
- the service worker registers and caches the shell, and the manifest names the application;
- the application embeds in a page on another origin with `<fluidian-app>`, sizes itself and reports its route;
- the browser shuts down when the system refuses to signal it; a browser abandoned by an interrupted run is found through its launch record and closed, by a direct call and by the sweep that starts every run; and the browser in use is never taken for an abandoned one.

The suite is built to leave nothing behind and to be unbothered by what is already there:

| | |
| --- | --- |
| **Ports** | Three free ports are chosen when the run starts, so nothing else on the machine can be in the way. Set `FLUIDIAN_TEST_PORT=N` to pin them to `N`, `N+1` and `N+2`. |
| **Servers** | The gallery and the showcase are started with a lifeline (`FLUIDIAN_LIFELINE=stdin`): they exit by themselves when the test process ends, however it ends. Each must return the token it was started with before it is used, so a server from some other run is never mistaken for a fresh one. |
| **Browser** | It is closed over the DevTools protocol first and by signal only as a fallback. A sandboxed build, such as the snap-packaged Chromium on Ubuntu, may refuse signals from the shell that launched it; that is not an error. |
| **Leftovers** | Every browser the harness starts is written down in a small record that the harness keeps locked while it runs. A run begins by reading those records: one whose lock is free belongs to a run that was interrupted, and if its browser still answers on its debugging port it is closed over that port. This does not depend on what the process table shows, which differs between systems (wrappers, a private `/tmp`, how orphans are adopted). Browsers from version 1.1.1 or earlier and test servers from 1.1.0 or earlier are still recognised by their command lines. The summary line says so when something was removed. Browsers and servers you started yourself are never touched. |

## Installing the optional toolchains

```bash
scripts/install-toolchains.sh --check    # what is installed
scripts/install-toolchains.sh            # install everything (Ubuntu or Debian, amd64 or arm64)
scripts/install-toolchains.sh kotlin dart
```

The script is best-effort: a language it cannot install is listed at the end and the others continue.

## Testing by hand

```bash
./fluidian gallery                                   # click through the 33 pages
./fluidian showcase                                  # and the 85 screens
./fluidian ai input.natural_date --input '{"text": "in 3 days"}'
./fluidian run --trace -- python3 sdks/python/examples/quickstart.py
```

## Testing your own app

Because an app is a program that reads and writes JSON lines, you can test it the way the SDKs are tested, in any language and without a browser:

```python
import sys
sys.path.insert(0, "engine")
from fluidian.testkit import conformance as harness

steps = [
    ({"t": "open", "sid": "s1", "route": "/", "locale": "en-US", "viewport": {"w": 1280, "h": 800}}, 1, False),
    ({"t": "event", "sid": "s1", "name": "increment", "target": "add", "value": None, "form": {}, "payload": None}, 1, False),
    ({"t": "shutdown"}, 0, False),
]
messages = harness.transcript(["python3", "app.py"], {"PYTHONPATH": "sdks/python"}, ".", steps=steps)
assert [m["t"] for m in messages] == ["ready", "scene", "scene", "exit"]
```

Each step is `(message, number of replies to wait for, send ASCII-escaped)`. Scenes in the transcript are already normalised, so assertions can use node ids.

For model-backed behaviour, point the engine at the mock provider (`fluidian.testkit.mock_openai.MockOpenAI`) or record real answers once with `FLUIDIAN_REPLAY=record` and replay them in CI.

## Continuous integration

```yaml
# .github/workflows/test.yml
name: test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v7
      - run: scripts/install-toolchains.sh
      - run: ./fluidian test --browser --json
```
