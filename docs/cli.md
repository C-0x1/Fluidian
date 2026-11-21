<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Command-line reference

`fluidian` is a launcher script in the repository root. It needs Python 3.9 or newer and nothing else. `./fluidian <command> --help` prints the options of any command.

## Running things

### `fluidian run <app> [options]`
Start an application written with any SDK and serve it. `<app>` is a source file in an interpreted language, a project folder, or any start command after `--`.

```bash
./fluidian run app.py                                  # a file: Python, JavaScript, Ruby, PHP, Lua, Elixir or Dart
./fluidian run converted/go --port 9000 --open         # a project folder: built first, then started
./fluidian run --production --host 0.0.0.0 -- ./my-rust-app
./fluidian run --trace -- php app.php
```

A project folder is one written by `fluidian new` or `fluidian convert` (it contains `fluidian.project.json`), or one that follows the same layout.

| Option | Meaning |
| --- | --- |
| `--port N`, `--host H` | Where to listen (default `127.0.0.1:8787`) |
| `--offline` | Use the Reflex engine even when an API key is set |
| `--open` | Open the browser when ready |
| `--trace` | Print every protocol message in both directions |
| `--production` | Disable developer tools and detailed errors |
| `--ready-timeout S` | Seconds to wait for the app's `ready` message (default 60) |

### `fluidian serve <scene.json>`
Serve a scene file without an application. The file holds one scene, or an object mapping routes to scenes. Attachments work; events have nowhere to go.

### `fluidian gallery`
Start the gallery: one page per AI capability family, plus the component library, portable logic, the platform preview and the artwork and theme catalogue. Accepts `--port`, `--host`, `--offline` and `--open`.

### `fluidian showcase`
Start the showcase: 85 complete screens in six groups (landing pages, storefronts, dashboards, AI products, mobile and cross-platform, application modules). Accepts the same options. Add `?theme=<preset>` or `?platform=ios|android` to any address.

## Checking things

### `fluidian doctor [--live]`
Report Python, Node.js, a browser, each SDK toolchain and the provider mode. With `--live` it also lists the models your key can reach, shows the model chosen per tier, and makes one structured-output request. Exit status is 0 when everything required is present.

### `fluidian test [options]`
Run the automated tests. See [Testing](testing.md).

| Option | Meaning |
| --- | --- |
| `--quick` | Engine and runtime suites only |
| `--sdk LANG` | Only this SDK (repeatable) |
| `--no-sdks` | Skip the SDK suite |
| `--browser` | Add the headless-Chrome suite |
| `--json` | Machine-readable summary |
| `-v`, `--verbose` | Print the full output of every suite |

## Exploring

### `fluidian features [--category ID] [--json]`
List capabilities, optionally one family.

### `fluidian components [--json]`
List components with their props.

### `fluidian ai <capability> [--input JSON | --input-file PATH] [--mode auto|reflex|reason]`
Invoke a capability and print the result with its provenance. Without input, the capability's own example is used.

```bash
./fluidian ai design.theme_prompt --input '{"prompt": "forest trail at dawn"}'
```

## Generating

### `fluidian new <language> <directory> [--name NAME] [--describe TEXT] [--force]`
Scaffold a runnable project: the source file, plus whatever the language needs to build against the SDK in this checkout (`go.mod`, `Cargo.toml`, a `.csproj`, `tsconfig.json`). With `--describe`, the first screen is composed from the description and emitted as code in the chosen language. The command prints the build and run steps; the test suite scaffolds, builds and starts a project in every language.

```bash
./fluidian new go ./crm --name "CRM" --describe "customer list with search and a new-customer form"
```

Languages: `python`, `javascript`, `typescript`, `go`, `rust`, `java`, `kotlin`, `csharp`, `cpp`, `ruby`, `php`, `dart`, `elixir`, `lua`.

### `fluidian export <scene.json> [--out page.html]`
Render a scene to a single static HTML file. Needs Node.js 18 or newer.

## Converting and packaging

### `fluidian convert <source> [--to LANGS] [options]`
Write an application in other SDK languages and verify each result against the source. See [Converting between languages](convert.md).

```bash
./fluidian convert app.py --to go,rust
./fluidian convert app.py --to all --probe
./fluidian convert my-go-app/ --to python
./fluidian convert --to kotlin -- ./server --flag
./fluidian convert scenes.json --to all
```

| Option | Meaning |
| --- | --- |
| `--to LANGS` | Comma-separated target languages, or `all` (default) |
| `-o, --out DIR` | Output folder (default `./converted`), one sub-folder per language |
| `--route PATH` | Also capture this route (repeatable); linked routes are found automatically |
| `--no-follow` | Capture only `/` and the routes given with `--route` |
| `--probe` | Call each handler once on the source and reproduce those that only notify or navigate |
| `--port-handlers` | Translate handler code with the model; a translation is kept only if it verifies |
| `--no-verify` | Write the projects without building and comparing them |
| `--json` | Machine-readable report |

Exit status is 1 when any target fails verification.

### `fluidian tokens [--theme NAME|all] [--format FORMAT|all] [--scheme light|dark] [-o DIR] [--list]`
Export a theme's design tokens. Formats: `css`, `scss`, `json`, `dtcg`, `tailwind`, `swift`, `android`, `compose`, `flutter`. One theme in one format is printed to the terminal; anything more is written to a folder. See [Cross-platform](cross-platform.md#design-tokens).

```bash
./fluidian tokens --list
./fluidian tokens --theme ocean --format swift
./fluidian tokens --theme all --format all -o design-tokens
```

### `fluidian package <ios|android|desktop|all> --name NAME --url URL [--id ID] [--theme NAME] [-o DIR]`
Write native shell projects around a deployed application: SwiftUI with `WKWebView`, Kotlin with `WebView`, and Electron. They are source projects, built with each platform's own tools. See [Cross-platform](cross-platform.md#native-shells).

```bash
./fluidian package all --name "Field Notes" --url https://notes.example.com
```

### `fluidian codegen`
Regenerate the SDK component factories, `spec/components.json`, `spec/capabilities.json` and the golden conformance transcript from the registries.

### `fluidian docs`
Regenerate the capability and component references, the SDK guide, the SDK READMEs and the generated tables in the main README.

### `fluidian version`
Print the version.

## Make targets

`make help` lists shortcuts: `doctor`, `test`, `test-quick`, `test-browser`, `gallery`, `showcase`, `codegen`, `docs`, `screenshots`, `toolchains`, `clean`, `dist`.

## Scripts

| Script | What it does |
| --- | --- |
| `bash scripts/setup-ubuntu.sh` | Installs Python, Node.js and the other language toolchains on Ubuntu, then runs `fluidian doctor` |
| `bash scripts/set-api-key.sh` | Prompts for your OpenAI key without echoing it and stores it for future terminals; `--remove` deletes it |
| `bash scripts/test-all.sh` | Runs every test and ends with one line: `RESULT: ALL TESTS PASSED` or `RESULT: SOME TESTS FAILED` |
| `bash scripts/install-toolchains.sh` | Installs only the language toolchains |
