<p align="center">
  <img src="docs/assets/banner.svg" alt="Fluidian — the AI-native UI framework" width="100%">
</p>

<p align="center">
  <b>Write the interface once. Run it in 14 languages, on every platform, with AI built into every component.</b><br>
  185 AI capabilities · 123 components · 27 themes · 14 language SDKs · iOS, Android, web and desktop · works offline · Apache-2.0
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#what-you-can-build">Screens</a> ·
  <a href="#ai-native-concretely">AI features</a> ·
  <a href="#write-once-run-in-every-language">Any language</a> ·
  <a href="#write-once-run-on-every-platform">Any platform</a> ·
  <a href="docs/README.md">Documentation</a>
</p>

<p align="center">
  <a href="docs/gallery.md"><img src="docs/assets/hero.png" alt="Eight screens built with Fluidian, each in a different theme: the framework home page in blue, an audio store on black, an observability console in teal, a design-tool landing page in violet, one mobile screen in eight themes, a project dashboard in green, a grocery store in orange and a trading desk in red" width="100%"></a>
</p>

---

## What Fluidian is

Fluidian is a UI framework in which intelligence is a property of the component, not a service you wire up next to it.

You describe a screen as a tree of components in the language you already write. A small engine renders it in the browser, keeps it in sync, and gives every component access to one AI kernel. Attaching a capability takes one call:

```python
ui.table().prop("rows", invoices).ai("data.query")      # filter by typing "overdue over 5000, largest first"
ui.input("when").ai("input.natural_date")               # "next friday 3pm" becomes 2026-11-27T15:00
ui.chart("line").prop("data", revenue).ai("data.anomaly").ai("data.forecast")
ui.generative("Collect feedback after a support call")  # the interface itself is composed from the intent
```

There is no prompt to write, no schema to maintain and no response to parse. Each capability is declared once in the engine with typed inputs and outputs, runs through one audited pipeline, and is available to all fourteen SDKs on the day it is added.

Three properties set it apart:

| | |
| --- | --- |
| **AI-native** | 185 capabilities attach to components the way event handlers do. Each one also has a deterministic offline implementation, so the product works with no key, no network and no bill, and degrades instead of failing when a provider is slow. |
| **Language-neutral** | The same application can be written in C++, C#, Dart, Elixir, Go, Java, JavaScript, Kotlin, Lua, PHP, Python, Ruby, Rust or TypeScript, and `fluidian convert` rewrites an application from any of them into any other and proves the result is identical. |
| **Platform-neutral** | One scene renders on the web, wears iOS or Android controls on a phone, installs as an app from the browser, embeds in any page with one element, and wraps into native shells for iOS, Android and desktop. |

## What it is for

| You are building | What Fluidian gives you |
| --- | --- |
| **Internal tools and dashboards** | Tables that answer plain-language questions, charts with forecasts and anomaly markers, forms that parse what people type. A working screen is a few dozen lines. |
| **AI products** | Chat, agent runs with approvals, playgrounds, evaluation consoles, model catalogues and routing tables are components, with provenance and budgets handled by the kernel. |
| **Customer-facing sites** | Landing pages, pricing, storefronts, carts and checkouts from marketing and commerce components, in twenty-seven themes, with artwork drawn in code. |
| **Mobile and cross-platform apps** | Phone screens with platform-appropriate navigation, the same code on iOS, Android and the web, installable without an app store. |
| **Products on a backend you already have** | Your Rust service, PHP back office or Elixir cluster describes its own interface. No separate front-end codebase, no API layer between them. |
| **Teams that work in several languages** | One component registry and one wire protocol; an interface written by one team converts to another team's language, verified. |

## How it works

```mermaid
flowchart LR
  subgraph APP["Your application · any of 14 languages"]
    direction TB
    V["view(ctx) returns a scene"]
    H["handlers and declared actions"]
  end
  subgraph ENGINE["Fluidian engine · Python standard library only"]
    direction TB
    S["sessions · scene normaliser · router"]
    K["AI kernel · 185 capabilities"]
    R["Reflex · offline, deterministic"]
    O["OpenAI · strict Structured Outputs"]
    S --- K
    K --- R
    K --- O
  end
  subgraph CLIENT["Runtime · ES modules, no build step"]
    direction TB
    C["123 components · 27 themes"]
    L["portable logic · platform skins"]
    P["16 AI presenters · developer tools"]
  end
  APP <-->|"JSON Lines over stdio"| ENGINE
  ENGINE <-->|"HTTP and server-sent events"| CLIENT
```

1. **Your application returns a scene**: a tree of nodes such as `Page`, `Table`, `Chart` or `Hero`, each with props, event bindings and AI attachments. It is an ordinary program in your language that reads and writes JSON Lines.
2. **The engine validates it** against the component registry, repairs what can be repaired, and streams it to the browser.
3. **The runtime renders it** with no bundler and no framework, and patches the page when the next scene arrives.
4. **The kernel answers AI attachments** through one fifteen-stage pipeline, from a model when a key is configured and from the local Reflex engine when it is not.

A complete application:

```python
from fluidian import App, ui

app = App("Counter")

@app.view
def view(ctx):
    return ui.page("Counter",
        ui.text(f"Count: {ctx.state.get('count', 0)}"),
        ui.button("Add one").on("click", "increment"),
        ui.text_area("notes").prop("label", "Notes").ai("input.ghost"))

@app.on("increment")
def increment(ctx, event):
    ctx.state["count"] = ctx.state.get("count", 0) + 1

app.run()
```

```bash
./fluidian run app.py
```

## AI-native, concretely

"AI-native" is a claim worth checking, so here is what it means in this codebase.

**A capability is a typed contract, not a prompt.** Every one of the 185 declares its input and output schema, its instruction, its offline implementation and how the runtime presents the result. The runtime has sixteen presenters: ghost text in a field, a diff before a rewrite is accepted, chips beside a control, an insight panel under a chart, a composed region of real components, and so on. The same capability therefore looks and behaves the same everywhere in a product.

| You write | People get |
| --- | --- |
| `ui.input("when").ai("input.natural_date")` | A field that accepts "tomorrow 9am" or "in 3 days" and stores an ISO timestamp |
| `ui.input("weight").ai("input.natural_quantity", {"expect": "mass"})` | "2.5 tonnes" understood as 2500 kg |
| `ui.input("email").ai("input.format_heal", {"kind": "email"})` | `amara@gmial.com` repaired, not rejected |
| `ui.form("contact", ...).ai("input.smart_paste")` | Paste an email signature and the whole form fills |
| `ui.text_area("reply").ai("input.tone_dial")` | A tone menu with a reviewable diff before anything changes |
| `ui.table().ai("data.query")` | Plain-language filtering and sorting |
| `ui.chart("line").ai("data.forecast").ai("data.anomaly")` | A forecast band and marked outliers, explained in a sentence |
| `ui.thread().ai("collab.thread_summary")` | A summary, with decisions and owners extracted |
| `ui.generative("Onboard a customer in four steps")` | A working wizard composed from registered components |
| `app.action("create_invoice", ...)` | "create an invoice for Globex for $300" works in the Intent Bar and the Copilot |
| `ui.text(notice).ai("access.plain_language")` | Legal text rewritten at a readable level, with a one-click revert |
| `"@ask content.summarize {text: notes} -> summary"` | A button that calls the kernel and stores the answer in page state, with no handler |
| *nothing* | Redaction, injection defence, budgets, caching, provenance and an audit trail on every call |

<p align="center">
  <a href="docs/gallery.md#gallery"><img src="docs/assets/screens/002-dashboard.png" alt="A dashboard with a forecast band, anomaly markers, generated insights and a plain-language table filter" width="92%"></a>
</p>

**One kernel, fifteen stages, every call.**

```mermaid
flowchart LR
  A[Policy] --> B[Consent] --> C[Validate input] --> D[Redact] --> E[Shield] --> F[Moderate] --> G[Cache] --> H[Coalesce]
  H --> I[Budget] --> J[Route] --> K{Reason or Reflex} --> L[Validate output] --> M[Ground] --> N[Restore] --> O[Record]
```

Personal data is replaced with placeholders before a request leaves the process and restored afterwards. Untrusted text is fenced and scanned for injected instructions. Outputs are validated against the capability's schema and repaired once if they fail. Interfaces composed by a model are grounded against the component registry: unknown components, props and actions are removed and contrast is fixed before anything renders. Every result carries provenance: provider, model, latency, cache status and a trace id you can open in the developer tools.

**What you will not find elsewhere in one place.**

| Capability | Why it matters |
| --- | --- |
| **Reflex engine** | Every capability runs offline and deterministically. Development, tests, demos and CI need no key; production degrades to Reflex when the provider is down or the budget is spent. |
| **Grounded generative UI** | A model may only compose from registered components, and what it composes is validated, repaired and attributed before it is shown. |
| **Portable logic** | `State`, `Show`, `Each`, `{{ }}` bindings and `@` actions keep client behaviour inside the scene as data, interpreted by a parser with no `eval`. The same behaviour runs in every language and on every platform. |
| **Verified cross-language conversion** | `fluidian convert` rewrites an application into any other SDK language, then builds and runs the result and compares it with the source, scene by scene. |
| **Themes verified by arithmetic** | Twenty-seven presets and any theme you describe are generated in OKLCH and checked against WCAG contrast targets; failing pairs are healed before the tokens are written. |
| **Model ids as configuration** | Tiers have preference lists; the engine asks the account which models it may use and negotiates parameters, so the defaults can age without breaking anything. |
| **Artwork in code** | Product shots, landscapes, portraits, meshes and device frames are drawn by the `Art` component from a handful of props. A complete storefront ships without a single image file. |

The fifteen capability families:

<!-- families:start -->
| Family | Capabilities | What it covers | A few of them |
| --- | --- | --- | --- |
| [Generative Composition](docs/reference/capabilities/compose.md) | 14 | Interfaces assembled at runtime from intent, data, schemas and sketches. | `compose.intent`, `compose.data_view`, `compose.schema_form` |
| [Input Intelligence](docs/reference/capabilities/input.md) | 17 | Fields that complete, parse, heal and coach instead of rejecting. | `input.ghost`, `input.smart_paste`, `input.natural_date` |
| [Conversational Command](docs/reference/capabilities/command.md) | 14 | Language as a first-class way to operate an application. | `command.route`, `command.plan`, `command.copilot` |
| [Adaptive Personalisation](docs/reference/capabilities/adapt.md) | 13 | Interfaces that respond to how each person actually works. | `adapt.expertise`, `adapt.frustration`, `adapt.predict_focus` |
| [Accessibility Intelligence](docs/reference/capabilities/access.md) | 11 | Inclusive defaults generated, audited and repaired automatically. | `access.alt_text`, `access.label_audit`, `access.plain_language` |
| [Design-System Intelligence](docs/reference/capabilities/design.md) | 14 | Themes, palettes, type and motion derived from intent and verified by maths. | `design.theme_prompt`, `design.brand_extract`, `design.palette` |
| [Data & Visualisation Intelligence](docs/reference/capabilities/data.md) | 16 | Data that explains itself: the right chart, grounded insights, plain-language queries. | `data.chart_choose`, `data.insights`, `data.anomaly` |
| [Content & Microcopy](docs/reference/capabilities/content.md) | 13 | Words that fit the space, the reader and the moment. | `content.microcopy`, `content.translate`, `content.summarize` |
| [Workflow & Agentic UI](docs/reference/capabilities/flow.md) | 11 | Goal-driven flows and the controls that keep people in charge of agents. | `flow.goal_wizard`, `flow.step_predict`, `flow.approval` |
| [Trust, Safety & Governance](docs/reference/capabilities/trust.md) | 12 | The guarantees that make generated interfaces safe to ship. | `trust.redact`, `trust.injection_shield`, `trust.moderate` |
| [Intelligence Infrastructure](docs/reference/capabilities/perf.md) | 12 | Caching, routing, streaming and resilience for model-backed UI. | `perf.semantic_cache`, `perf.stream_scene`, `perf.router` |
| [Developer Experience](docs/reference/capabilities/dev.md) | 14 | Review, testing, scaffolding and translation between fourteen languages. | `dev.explain_node`, `dev.ux_review`, `dev.test_synth` |
| [Multimodal](docs/reference/capabilities/modal.md) | 9 | Voice, vision and generated imagery as interface primitives. | `modal.dictate`, `modal.speak`, `modal.vision_form` |
| [Collaboration](docs/reference/capabilities/collab.md) | 7 | Shared work summarised, mediated and kept moving. | `collab.thread_summary`, `collab.merge`, `collab.reply` |
| [Ambient & Emotional UX](docs/reference/capabilities/ambient.md) | 8 | Small moments of timing, tone and care. | `ambient.loading_story`, `ambient.empathy`, `ambient.celebrate` |
| **Total** | **185** | | |
<!-- families:end -->

Every capability is documented with its inputs, outputs, an example and a real result in the [capability reference](docs/reference/capabilities.md).

## Write once, run in every language

Applications are ordinary programs that speak JSON Lines over standard input and output, so every language is a first-class citizen. The SDKs are small, dependency-free and held to one conformance transcript.

<!-- languages:start -->
| Language | Language level | Verified with | Start an app |
| --- | --- | --- | --- |
| [Python](sdks/python/README.md) | Python 3.9+ | CPython 3.13 | `fluidian run -- python3 examples/quickstart.py` |
| [JavaScript](sdks/javascript/README.md) | Node.js 14+ (CommonJS) | Node.js 22 | `fluidian run -- node examples/quickstart.js` |
| [TypeScript](sdks/typescript/README.md) | TypeScript 4.5+, target ES2019 | TypeScript 7.0 on Node.js 22 | `fluidian run -- node dist/quickstart.js` |
| [Go](sdks/go/README.md) | Go 1.18+ | Go 1.24 | `fluidian run -- go run ./cmd/quickstart` |
| [Rust](sdks/rust/README.md) | Rust 2021 edition | Rust 1.97 | `fluidian run -- cargo run --quiet --example quickstart` |
| [Java](sdks/java/README.md) | Java 11+ | OpenJDK 21 | `fluidian run -- java -cp out dev.fluidian.examples.Quickstart` |
| [Kotlin](sdks/kotlin/README.md) | Kotlin 1.3+ on JVM 11+ | kotlinc 1.3 on OpenJDK 21 | `fluidian run -- java -cp quickstart.jar dev.fluidian.examples.QuickstartKt` |
| [C#](sdks/csharp/README.md) | C# 10, .NET 6+ | .NET 8 | `fluidian run -- dotnet run --project examples/Quickstart` |
| [C++](sdks/cpp/README.md) | C++17 | GCC 13 | `fluidian run -- ./quickstart` |
| [Ruby](sdks/ruby/README.md) | Ruby 3.0+ | Ruby 3.3 | `fluidian run -- ruby -Ilib examples/quickstart.rb` |
| [PHP](sdks/php/README.md) | PHP 8.1+ | PHP 8.3 | `fluidian run -- php examples/quickstart.php` |
| [Dart](sdks/dart/README.md) | Dart 3 | Dart 3.14 | `fluidian run -- dart run example/quickstart.dart` |
| [Elixir](sdks/elixir/README.md) | Elixir 1.14+ | Elixir 1.14 on OTP 24 | `fluidian run -- elixir examples/quickstart.exs` |
| [Lua](sdks/lua/README.md) | Lua 5.3+ | Lua 5.4 | `fluidian run -- lua5.4 examples/quickstart.lua` |
<!-- languages:end -->

Moving between them is one command:

```console
$ ./fluidian convert examples/portable/app.py --to all --probe

  Field Notes  from Python · 6 routes · 4 handlers (2 reproduced from observed behaviour)

  ✓ JavaScript  verified  6 routes identical to the source, 5 handler calls replayed
  ✓ TypeScript  verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Go          verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Rust        verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Java        verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Kotlin      verified  6 routes identical to the source, 5 handler calls replayed
  ✓ C#          verified  6 routes identical to the source, 5 handler calls replayed
  ✓ C++         verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Ruby        verified  6 routes identical to the source, 5 handler calls replayed
  ✓ PHP         verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Dart        verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Elixir      verified  6 routes identical to the source, 5 handler calls replayed
  ✓ Lua         verified  6 routes identical to the source, 5 handler calls replayed

  Projects: converted/<language>   scenes: converted/scenes.json
  Run one:  fluidian run converted/go
```

The converter does not translate source text. It runs your application, records the scene of every route, writes those scenes as idiomatic builder code for the target SDK, then builds and runs the generated project and compares what it serves with the original. Any language can be the source and any language the target, including a chain: Python to Go to Rust and back to Python returns the identical application.

What converts, and how completely:

| Part of your application | What happens |
| --- | --- |
| Screens, layout, props, themes, AI attachments | Converted exactly and verified node for node |
| Portable logic: state, bindings, conditional and repeated content, `@` actions | Converted exactly; it is data in the scene |
| Declared actions: name, description, parameters | Converted exactly and verified |
| Handlers that notify or navigate | With `--probe`: observed on the source, reproduced, then replayed against the result |
| Handlers with business logic | A clearly marked stub; with `--port-handlers` the model translates them and the translation is kept only if it verifies |

The whole 85-screen showcase in this repository converts to all thirteen other languages with every one of its 86 routes verified identical. The guide is [docs/convert.md](docs/convert.md).

## Write once, run on every platform

| Target | How | What you do |
| --- | --- | --- |
| **Web** | The runtime is plain ES modules served by the engine | Nothing |
| **iOS and Android controls** | The runtime detects the platform and applies its skin: large titles and tab bars on iOS, Material bars, indicators and a floating action button on Android | Nothing; force one with `?platform=ios` |
| **Phone, tablet, desktop layouts** | Components respond to the space they are given through container queries, not to the window | Nothing |
| **Installed app** | The engine serves a web app manifest, icons and a service worker that keeps the shell available offline | "Add to Home Screen" or "Install" in the browser |
| **Inside another site** | `<fluidian-app src="https://your-app">` works in plain HTML, React, Vue, Svelte, Angular and server templates, and sizes itself to its content | Add one script tag and list the host in `FLUIDIAN_EMBED_ORIGINS` |
| **Native shells** | `fluidian package ios`, `android` or `desktop` writes a SwiftUI, Kotlin or Electron project around your deployed app | Open it in Xcode or Android Studio, or run `npm start` |
| **Your design tools** | `fluidian tokens` exports any theme as CSS, SCSS, JSON, W3C design tokens, a Tailwind preset, SwiftUI, Android resources, Jetpack Compose or Flutter | Pick a format |
| **Static hosting** | `fluidian export` renders a scene to a self-contained HTML file | Upload it |

<p align="center">
  <a href="docs/gallery.md#mobile-and-cross-platform"><img src="docs/assets/screens/100-mobile-platforms.png" alt="The same dashboard scene in a phone, a tablet and a browser" width="92%"></a>
</p>

The guide is [docs/cross-platform.md](docs/cross-platform.md).

## What you can build

Every image below is the running framework, captured by [`tools/screenshots.py`](tools/screenshots.py). Open them yourself with `./fluidian showcase` and `./fluidian gallery`. Brands and people shown are fictional.

<!-- gallery:start -->
<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/035-landing-lumen.png"><img src="docs/assets/screens/035-landing-lumen.png" alt="An AI product launch: glow backdrop, prompt composer and a bento of capabilities"></a><br><sub><b>Lumen · AI workspace</b> · aurora theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/061-dash-finance.png"><img src="docs/assets/screens/061-dash-finance.png" alt="A wealth dashboard in the Midnight theme: allocation rings, a performance curve and holdings with trends"></a><br><sub><b>Northbank · wealth dashboard</b> · midnight theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/049-store-olea.png"><img src="docs/assets/screens/049-store-olea.png" alt="An editorial storefront: serif display type, a split hero and a product grid with procedural product shots"></a><br><sub><b>Maison Olea · skincare storefront</b> · sand theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/077-ai-chat.png"><img src="docs/assets/screens/077-ai-chat.png" alt="An assistant conversation with tool calls, citations and follow-ups, beside the sources it read"></a><br><sub><b>Assistant chat</b> · aurora theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/096-mobile-weather.png"><img src="docs/assets/screens/096-mobile-weather.png" alt="A weather app whose icons and skies are all generated artwork"></a><br><sub><b>Weather · iOS and Android</b> · abyss theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/079-ai-playground.png"><img src="docs/assets/screens/079-ai-playground.png" alt="A prompt playground: system and user messages, parameters, a streamed answer and token accounting"></a><br><sub><b>Prompt playground</b> · neon theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/063-dash-trading.png"><img src="docs/assets/screens/063-dash-trading.png" alt="A trading terminal in the Crimson theme: candlesticks with volume, an order book and open positions"></a><br><sub><b>Vector · trading terminal</b> · crimson theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/040-landing-northbank.png"><img src="docs/assets/screens/040-landing-northbank.png" alt="A financial services page: calm blues, account cards, a rate comparison and an FAQ"></a><br><sub><b>Northbank · investing</b> · ocean theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/110-module-kanban.png"><img src="docs/assets/screens/110-module-kanban.png" alt="A kanban board in the Forest theme with tags, assignees and a suggested next priority"></a><br><sub><b>Kanban board</b> · forest theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/090-mobile-banking.png"><img src="docs/assets/screens/090-mobile-banking.png" alt="One banking scene rendered with the iOS skin, the Android skin and a dark theme: no platform-specific code"></a><br><sub><b>Banking app · iOS and Android</b> · deep theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/054-store-order.png"><img src="docs/assets/screens/054-store-order.png" alt="Order confirmation with live tracking: a route on the generated city map and a delivery timeline"></a><br><sub><b>Order tracking</b> · mint theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/064-dash-health.png"><img src="docs/assets/screens/064-dash-health.png" alt="Health and training in the Ember theme: activity rings, heart-rate zones, sleep stages and a readiness gauge"></a><br><sub><b>Pulse · health dashboard</b> · ember theme</sub></td></tr>
</table>

The full set, by kind (click to open):

<details>
<summary><b>Landing pages</b> — 14 screens. Launch pages for thirteen fictional products and for Fluidian itself, across thirteen themes, each with its own typographic voice.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/035-landing-lumen.png"><img src="docs/assets/screens/035-landing-lumen.png" alt="An AI product launch: glow backdrop, prompt composer and a bento of capabilities"></a><br><sub><b>Lumen · AI workspace</b> · aurora theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/036-landing-stackline.png"><img src="docs/assets/screens/036-landing-stackline.png" alt="A developer platform in monochrome: grid backdrop, a product window and a code-first feature band"></a><br><sub><b>Stackline · developer cloud</b> · graphite theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/037-landing-relay.png"><img src="docs/assets/screens/037-landing-relay.png" alt="An API gateway for models: headline stats, a ranked model list and a usage console in a browser frame"></a><br><sub><b>Relay · model router</b> · abyss theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/038-landing-halo.png"><img src="docs/assets/screens/038-landing-halo.png" alt="A hardware launch in full-bleed promo tiles, with every product drawn procedurally"></a><br><sub><b>Halo · wearables</b> · ruby theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/039-landing-pulse.png"><img src="docs/assets/screens/039-landing-pulse.png" alt="A mobile app launch page: split hero with a live phone preview, feature tiles and testimonials"></a><br><sub><b>Pulse · fitness app</b> · ember theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/040-landing-northbank.png"><img src="docs/assets/screens/040-landing-northbank.png" alt="A financial services page: calm blues, account cards, a rate comparison and an FAQ"></a><br><sub><b>Northbank · investing</b> · ocean theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/041-landing-canvasly.png"><img src="docs/assets/screens/041-landing-canvasly.png" alt="A playful design-tool launch: pastel palette, input modes and a wall of short testimonials"></a><br><sub><b>Canvasly · design tool</b> · candy theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/042-landing-brightbuild.png"><img src="docs/assets/screens/042-landing-brightbuild.png" alt="An AI app builder: warm gradient mesh, a prompt-first hero and a gallery of starting points"></a><br><sub><b>Brightbuild · app builder</b> · sunset theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/043-landing-hearth.png"><img src="docs/assets/screens/043-landing-hearth.png" alt="An open-source project page in the Terminal theme: monospace type, an install block and numbered features"></a><br><sub><b>Hearth · open-source agent</b> · terminal theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/044-landing-mnemo.png"><img src="docs/assets/screens/044-landing-mnemo.png" alt="An infrastructure product: tabbed code in the hero, a three-step explainer and a benchmark chart"></a><br><sub><b>Mnemo · memory for AI</b> · grape theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/045-landing-orbit.png"><img src="docs/assets/screens/045-landing-orbit.png" alt="A SaaS landing page with the product on show: a dashboard in a browser frame, feature tiles and plans"></a><br><sub><b>Orbit · product analytics</b> · iris theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/046-landing-atelier.png"><img src="docs/assets/screens/046-landing-atelier.png" alt="A studio portfolio in the Gold theme: serif display type on near-black, with generative cover art"></a><br><sub><b>Atelier Nord · studio</b> · gold theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/047-landing-voyage.png"><img src="docs/assets/screens/047-landing-voyage.png" alt="A travel booking page: a generated landscape hero with a search card and destination tiles"></a><br><sub><b>Voyage · travel</b> · sky theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/048-landing-fluidian.png"><img src="docs/assets/screens/048-landing-fluidian.png" alt="Fluidian's own home page, built with Fluidian: code beside its result, the numbers and the ideas behind it"></a><br><sub><b>Fluidian · framework home page</b> · deep theme</sub></td></tr>
</table>

</details>

<details>
<summary><b>Storefronts</b> — 12 screens. Catalogues, product pages, carts, checkouts and a seller's back office. Every product image is drawn by the `Art` component.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/049-store-olea.png"><img src="docs/assets/screens/049-store-olea.png" alt="An editorial storefront: serif display type, a split hero and a product grid with procedural product shots"></a><br><sub><b>Maison Olea · skincare storefront</b> · sand theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/050-store-kordo.png"><img src="docs/assets/screens/050-store-kordo.png" alt="A dark category page: filters, sort controls and a product grid with colour swatches"></a><br><sub><b>Kordo · category listing</b> · neon theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/051-store-product.png"><img src="docs/assets/screens/051-store-product.png" alt="A product detail page with a media gallery, variant pickers and a review summary written by the AI kernel"></a><br><sub><b>Kordo · product page</b> · emerald theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/052-store-cart.png"><img src="docs/assets/screens/052-store-cart.png" alt="A cart in the Rose theme: line items with steppers, an order summary and recommendations"></a><br><sub><b>Maison Olea · cart</b> · rose theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/053-store-checkout.png"><img src="docs/assets/screens/053-store-checkout.png" alt="A checkout with smart paste: one pasted address fills the form, and totals stay in view"></a><br><sub><b>Maison Olea · checkout</b> · ocean theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/054-store-order.png"><img src="docs/assets/screens/054-store-order.png" alt="Order confirmation with live tracking: a route on the generated city map and a delivery timeline"></a><br><sub><b>Order tracking</b> · mint theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/055-store-fern.png"><img src="docs/assets/screens/055-store-fern.png" alt="A plant shop in the Moss theme: lime on deep green, with every plant drawn from a seed"></a><br><sub><b>Fern & Co · plant shop</b> · moss theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/056-store-glyph.png"><img src="docs/assets/screens/056-store-glyph.png" alt="A marketplace for fonts and templates: type specimens and interface thumbnails generated on the fly"></a><br><sub><b>Glyph Market · digital goods</b> · candy theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/057-store-tempo.png"><img src="docs/assets/screens/057-store-tempo.png" alt="A luxury product page: gold on black, serif headlines and a generated watch as the centrepiece"></a><br><sub><b>Tempo · watches</b> · gold theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/058-store-crate.png"><img src="docs/assets/screens/058-store-crate.png" alt="Grocery delivery in the Tangerine theme: produce drawn as artwork, quick-add buttons and a live basket"></a><br><sub><b>Crate · grocery delivery</b> · tangerine theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/059-store-admin.png"><img src="docs/assets/screens/059-store-admin.png" alt="The merchant side: revenue, orders and stock alerts, with an AI briefing on what needs attention"></a><br><sub><b>Merchant admin</b> · deep theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/060-store-lookbook.png"><img src="docs/assets/screens/060-store-lookbook.png" alt="An editorial homeware lookbook in the Forest theme: overlay tiles, serif type and warm product shots"></a><br><sub><b>Casa Verano · lookbook</b> · forest theme</sub></td></tr>
</table>

</details>

<details>
<summary><b>Dashboards</b> — 16 screens. Sixteen operational screens, from a trading desk to a clinic schedule.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/061-dash-finance.png"><img src="docs/assets/screens/061-dash-finance.png" alt="A wealth dashboard in the Midnight theme: allocation rings, a performance curve and holdings with trends"></a><br><sub><b>Northbank · wealth dashboard</b> · midnight theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/062-dash-saas.png"><img src="docs/assets/screens/062-dash-saas.png" alt="Product analytics: activation, a conversion funnel, a retention heatmap and the pages people use most"></a><br><sub><b>Orbit · product analytics</b> · deep theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/063-dash-trading.png"><img src="docs/assets/screens/063-dash-trading.png" alt="A trading terminal in the Crimson theme: candlesticks with volume, an order book and open positions"></a><br><sub><b>Vector · trading terminal</b> · crimson theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/064-dash-health.png"><img src="docs/assets/screens/064-dash-health.png" alt="Health and training in the Ember theme: activity rings, heart-rate zones, sleep stages and a readiness gauge"></a><br><sub><b>Pulse · health dashboard</b> · ember theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/065-dash-home.png"><img src="docs/assets/screens/065-dash-home.png" alt="A smart-home panel in the Grape theme: device tiles, a thermostat gauge, energy use and scenes"></a><br><sub><b>Hearthstone · smart home</b> · grape theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/066-dash-devops.png"><img src="docs/assets/screens/066-dash-devops.png" alt="An observability console in the Lagoon theme, teal on deep blue-green: latency and error rates, service health, an incident timeline and live logs"></a><br><sub><b>Stackline · observability</b> · lagoon theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/067-dash-llm.png"><img src="docs/assets/screens/067-dash-llm.png" alt="An LLM gateway console: token spend by model, cache savings, budgets per team and the latest requests"></a><br><sub><b>Relay · LLM gateway console</b> · abyss theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/068-dash-crm.png"><img src="docs/assets/screens/068-dash-crm.png" alt="A sales workspace: a pipeline board with deal values, a forecast with a confidence band and a leaderboard"></a><br><sub><b>Northpass · sales pipeline</b> · ocean theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/069-dash-projects.png"><img src="docs/assets/screens/069-dash-projects.png" alt="A project tracker in black and white: a roadmap, a burndown, workload by person and what is due this week"></a><br><sub><b>Cadence · project tracker</b> · emerald theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/070-dash-music.png"><img src="docs/assets/screens/070-dash-music.png" alt="A music app: generated album covers, a now-playing bar with a waveform and personal listening stats"></a><br><sub><b>Tide · music streaming</b> · neon theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/071-dash-learning.png"><img src="docs/assets/screens/071-dash-learning.png" alt="A learning platform in the Candy theme: course progress, a study streak, the week's schedule and a leaderboard"></a><br><sub><b>Kindle Academy · learning</b> · candy theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/072-dash-logistics.png"><img src="docs/assets/screens/072-dash-logistics.png" alt="Fleet operations: live routes on the generated map, on-time performance and shipments that need attention"></a><br><sub><b>Halden · fleet and logistics</b> · tangerine theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/073-dash-clinic.png"><img src="docs/assets/screens/073-dash-clinic.png" alt="A clinic day view in the Mint theme: appointments across rooms, a waiting list and capacity at a glance"></a><br><sub><b>Oakline · clinic operations</b> · mint theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/074-dash-energy.png"><img src="docs/assets/screens/074-dash-energy.png" alt="A home energy dashboard in the Citrus theme: production against use, battery state and panel output"></a><br><sub><b>Solstice · solar and energy</b> · citrus theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/075-dash-social.png"><img src="docs/assets/screens/075-dash-social.png" alt="Creator analytics in the Rose theme: audience growth, the best time to post and top content with generated thumbnails"></a><br><sub><b>Bloom · creator analytics</b> · rose theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/076-dash-support.png"><img src="docs/assets/screens/076-dash-support.png" alt="A support desk in the Sky theme: queue health, a live conversation and a reply drafted by the assistant"></a><br><sub><b>Harbor · support desk</b> · sky theme</sub></td></tr>
</table>

</details>

<details>
<summary><b>AI products</b> — 13 screens. Chat, agents, playgrounds, model catalogues, evaluation consoles and routing tables: the screens AI companies ship.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/077-ai-chat.png"><img src="docs/assets/screens/077-ai-chat.png" alt="An assistant conversation with tool calls, citations and follow-ups, beside the sources it read"></a><br><sub><b>Assistant chat</b> · aurora theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/078-ai-agent-run.png"><img src="docs/assets/screens/078-ai-agent-run.png" alt="An agent run laid bare: every step, tool call and cost, with an approval waiting for a human"></a><br><sub><b>Agent run inspector</b> · abyss theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/079-ai-playground.png"><img src="docs/assets/screens/079-ai-playground.png" alt="A prompt playground: system and user messages, parameters, a streamed answer and token accounting"></a><br><sub><b>Prompt playground</b> · neon theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/080-ai-models.png"><img src="docs/assets/screens/080-ai-models.png" alt="Choosing a model with evidence: quality, speed and price side by side, and the same prompt answered three ways"></a><br><sub><b>Model comparison</b> · ruby theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/081-ai-compose.png"><img src="docs/assets/screens/081-ai-compose.png" alt="Generative UI, live: a sentence becomes a working interface, composed by the kernel and editable afterwards"></a><br><sub><b>Generative interface</b> · iris theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/082-ai-search.png"><img src="docs/assets/screens/082-ai-search.png" alt="A search experience that answers: a cited summary, the passages behind it and related questions"></a><br><sub><b>Answer engine</b> · deep theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/083-ai-doc-qa.png"><img src="docs/assets/screens/083-ai-doc-qa.png" alt="Ask a contract: the document on the left, answers on the right with the clause each one came from"></a><br><sub><b>Document question answering</b> · ocean theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/084-ai-analyst.png"><img src="docs/assets/screens/084-ai-analyst.png" alt="Ask your data: a plain-language question becomes a query, a chart and a written finding you can check"></a><br><sub><b>Data analyst</b> · mint theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/085-ai-review.png"><img src="docs/assets/screens/085-ai-review.png" alt="Human review of AI changes: each rewrite shown as a diff with its reason, risk and an accept or reject"></a><br><sub><b>Reviewing AI edits</b> · rose theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/086-ai-memory.png"><img src="docs/assets/screens/086-ai-memory.png" alt="What the assistant remembers and why: facts with their source, confidence and a way to forget"></a><br><sub><b>Memory inspector</b> · grape theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/087-ai-voice.png"><img src="docs/assets/screens/087-ai-voice.png" alt="A recording becomes a summary, decisions and assigned actions, with the transcript one click away"></a><br><sub><b>Voice notes to actions</b> · ember theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/088-ai-router.png"><img src="docs/assets/screens/088-ai-router.png" alt="Model governance in the Terminal theme: routing rules, a fallback chain, guardrails and data residency"></a><br><sub><b>Routing and guardrails</b> · terminal theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/089-ai-evals.png"><img src="docs/assets/screens/089-ai-evals.png" alt="Keeping quality honest: pass rates per suite, a regression flagged against the last release and failing examples"></a><br><sub><b>Evaluation dashboard</b> · lagoon theme</sub></td></tr>
</table>

</details>

<details>
<summary><b>Mobile and cross-platform</b> — 14 screens. Phone screens with the iOS and Android skins, and the same scene shown on a phone, a tablet and the web.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/090-mobile-banking.png"><img src="docs/assets/screens/090-mobile-banking.png" alt="One banking scene rendered with the iOS skin, the Android skin and a dark theme: no platform-specific code"></a><br><sub><b>Banking app · iOS and Android</b> · deep theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/091-mobile-fitness.png"><img src="docs/assets/screens/091-mobile-fitness.png" alt="A fitness tracker in the Ember theme on both platforms, with rings, stats and a weekly chart"></a><br><sub><b>Fitness tracker · iOS and Android</b> · ember theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/092-mobile-food.png"><img src="docs/assets/screens/092-mobile-food.png" alt="A food delivery app in the Sunset theme: generated dishes, quick filters and a floating basket"></a><br><sub><b>Food delivery · iOS and Android</b> · sunset theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/093-mobile-travel.png"><img src="docs/assets/screens/093-mobile-travel.png" alt="A trip screen with a generated landscape, a boarding pass and the day's plan"></a><br><sub><b>Travel companion · iOS and Android</b> · sky theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/094-mobile-music.png"><img src="docs/assets/screens/094-mobile-music.png" alt="A music player with generated cover art, transport controls and a waveform"></a><br><sub><b>Music player · iOS and Android</b> · grape theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/095-mobile-chat.png"><img src="docs/assets/screens/095-mobile-chat.png" alt="A messaging app: the inbox on iOS and a conversation on Android, with an AI-suggested reply inline"></a><br><sub><b>Messaging · list and conversation</b> · mint theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/096-mobile-weather.png"><img src="docs/assets/screens/096-mobile-weather.png" alt="A weather app whose icons and skies are all generated artwork"></a><br><sub><b>Weather · iOS and Android</b> · abyss theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/097-mobile-habits.png"><img src="docs/assets/screens/097-mobile-habits.png" alt="A habit tracker with a streak heatmap, a checklist and a nudge from the AI kernel"></a><br><sub><b>Habit tracker · iOS and Android</b> · citrus theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/098-mobile-home.png"><img src="docs/assets/screens/098-mobile-home.png" alt="Smart-home controls: toggle tiles, a thermostat gauge and scene shortcuts on both platforms"></a><br><sub><b>Smart home · iOS and Android</b> · lagoon theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/099-mobile-shop.png"><img src="docs/assets/screens/099-mobile-shop.png" alt="The Maison Olea storefront on phones: the same product cards as the website, reflowed"></a><br><sub><b>Storefront · iOS and Android</b> · ruby theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/100-mobile-platforms.png"><img src="docs/assets/screens/100-mobile-platforms.png" alt="The same dashboard scene in a phone, a tablet and a browser: layout adapts to the frame, not just the window"></a><br><sub><b>One scene on phone, tablet and web</b> · emerald theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/101-mobile-themes.png"><img src="docs/assets/screens/101-mobile-themes.png" alt="One wallet screen in eight of the twenty-seven built-in themes, alternating the iOS and Android skins"></a><br><sub><b>One screen, eight themes</b> · paper theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/102-mobile-onboarding.png"><img src="docs/assets/screens/102-mobile-onboarding.png" alt="A three-step onboarding flow with generated illustrations"></a><br><sub><b>Onboarding flow</b> · tangerine theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/103-mobile-auth.png"><img src="docs/assets/screens/103-mobile-auth.png" alt="Authentication screens: sign-in, a one-time code and passkey confirmation"></a><br><sub><b>Sign-in, verification and passkeys</b> · ocean theme</sub></td></tr>
</table>

</details>

<details>
<summary><b>Application modules</b> — 16 screens. The parts every product needs: sign-in, onboarding, settings, inbox, calendar, files, billing and more.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/104-module-auth.png"><img src="docs/assets/screens/104-module-auth.png" alt="A split sign-in screen: generated artwork and a testimonial on one side, the form on the other"></a><br><sub><b>Sign-in</b> · aurora theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/105-module-onboarding.png"><img src="docs/assets/screens/105-module-onboarding.png" alt="A setup wizard with progress, plan choices and suggestions written by the AI kernel"></a><br><sub><b>Setup wizard</b> · sunset theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/106-module-settings.png"><img src="docs/assets/screens/106-module-settings.png" alt="Account settings: profile, preferences, security, a plan card and a danger zone"></a><br><sub><b>Settings</b> · deep theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/107-module-inbox.png"><img src="docs/assets/screens/107-module-inbox.png" alt="A three-pane mail client with an AI summary and a drafted reply above the thread"></a><br><sub><b>Mail client</b> · iris theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/108-module-calendar.png"><img src="docs/assets/screens/108-module-calendar.png" alt="A month calendar with an agenda and scheduling suggestions from the AI kernel"></a><br><sub><b>Calendar</b> · sky theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/109-module-files.png"><img src="docs/assets/screens/109-module-files.png" alt="A file manager with generated thumbnails, a details panel and search by meaning rather than filename"></a><br><sub><b>File manager</b> · grape theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/110-module-kanban.png"><img src="docs/assets/screens/110-module-kanban.png" alt="A kanban board in the Forest theme with tags, assignees and a suggested next priority"></a><br><sub><b>Kanban board</b> · forest theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/111-module-table.png"><img src="docs/assets/screens/111-module-table.png" alt="A dense data grid with plain-language filtering, bulk actions, status badges and pagination"></a><br><sub><b>Data grid</b> · emerald theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/112-module-notifications.png"><img src="docs/assets/screens/112-module-notifications.png" alt="A notification centre: grouped activity, an AI digest of what matters and per-channel preferences"></a><br><sub><b>Notification centre</b> · candy theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/113-module-team.png"><img src="docs/assets/screens/113-module-team.png" alt="A team directory: member cards with presence, roles, workload and pending invitations"></a><br><sub><b>Team directory</b> · mint theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/114-module-billing.png"><img src="docs/assets/screens/114-module-billing.png" alt="Billing: the current plan, metered usage against limits, a payment method and invoice history"></a><br><sub><b>Billing and usage</b> · ocean theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/115-module-pricing.png"><img src="docs/assets/screens/115-module-pricing.png" alt="A complete pricing page: plan cards, a feature comparison and frequently asked questions"></a><br><sub><b>Pricing page</b> · citrus theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/116-module-changelog.png"><img src="docs/assets/screens/116-module-changelog.png" alt="A changelog with release entries, tagged improvements and a subscription card"></a><br><sub><b>Changelog</b> · midnight theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/117-module-command.png"><img src="docs/assets/screens/117-module-command.png" alt="The command palette: language routed to actions, with the matched arguments shown before anything runs"></a><br><sub><b>Command palette</b> · moss theme</sub></td><td width="33%" valign="top"><a href="docs/assets/screens/118-module-docs.png"><img src="docs/assets/screens/118-module-docs.png" alt="A documentation layout: section navigation, an article with highlighted code and an on-this-page rail"></a><br><sub><b>Documentation site</b> · abyss theme</sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/119-module-themes.png"><img src="docs/assets/screens/119-module-themes.png" alt="All twenty-seven built-in themes on one page, each applied to the same card with a single Theme node"></a><br><sub><b>Theme wall</b> · paper theme</sub></td></tr>
</table>

</details>

<details>
<summary><b>Gallery</b> — 37 screens. The live gallery application: one page per AI capability family, running against the offline engine.</summary>
<br>

<table>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/001-overview.png"><img src="docs/assets/screens/001-overview.png" alt="Gallery overview"></a><br><sub><b>Gallery overview</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/002-dashboard.png"><img src="docs/assets/screens/002-dashboard.png" alt="Dashboard with forecast, anomaly detection and generated insights"></a><br><sub><b>Dashboard with forecast, anomaly detection and generated insights</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/003-dashboard-dark.png"><img src="docs/assets/screens/003-dashboard-dark.png" alt="The same dashboard in the dark scheme"></a><br><sub><b>The same dashboard in the dark scheme</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/004-generative-ui.png"><img src="docs/assets/screens/004-generative-ui.png" alt="Interfaces composed from intent, schema and data"></a><br><sub><b>Interfaces composed from intent, schema and data</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/005-sketch-import.png"><img src="docs/assets/screens/005-sketch-import.png" alt="Text wireframes and legacy HTML translated into components"></a><br><sub><b>Text wireframes and legacy HTML translated into components</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/006-smart-forms.png"><img src="docs/assets/screens/006-smart-forms.png" alt="Natural dates and quantities, format healing and semantic validation"></a><br><sub><b>Natural dates and quantities, format healing and semantic validation</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/007-smart-paste.png"><img src="docs/assets/screens/007-smart-paste.png" alt="A pasted signature fills the whole form"></a><br><sub><b>A pasted signature fills the whole form</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/008-writing-tools.png"><img src="docs/assets/screens/008-writing-tools.png" alt="Tone changes are previewed as a diff before they are accepted"></a><br><sub><b>Tone changes are previewed as a diff before they are accepted</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/009-intent-bar.png"><img src="docs/assets/screens/009-intent-bar.png" alt="The Intent Bar routes language to registered actions"></a><br><sub><b>The Intent Bar routes language to registered actions</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/010-copilot.png"><img src="docs/assets/screens/010-copilot.png" alt="A copilot grounded in the current screen"></a><br><sub><b>A copilot grounded in the current screen</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/011-ask-your-data.png"><img src="docs/assets/screens/011-ask-your-data.png" alt="Plain-language filtering, column typing and chart selection"></a><br><sub><b>Plain-language filtering, column typing and chart selection</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/012-charts.png"><img src="docs/assets/screens/012-charts.png" alt="Charts with forecasts, anomaly markers and written descriptions"></a><br><sub><b>Charts with forecasts, anomaly markers and written descriptions</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/013-data-story.png"><img src="docs/assets/screens/013-data-story.png" alt="A narrative report generated from rows"></a><br><sub><b>A narrative report generated from rows</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/014-theme-studio.png"><img src="docs/assets/screens/014-theme-studio.png" alt="Themes generated as OKLCH design tokens with contrast repair"></a><br><sub><b>Themes generated as OKLCH design tokens with contrast repair</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/015-restyle-night.png"><img src="docs/assets/screens/015-restyle-night.png" alt="One sentence restyles the product: “Calm fintech at night”"></a><br><sub><b>One sentence restyles the product: “Calm fintech at night”</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/016-restyle-citrus.png"><img src="docs/assets/screens/016-restyle-citrus.png" alt="The same screen as “Sunny citrus market”"></a><br><sub><b>The same screen as “Sunny citrus market”</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/017-accessibility.png"><img src="docs/assets/screens/017-accessibility.png" alt="An accessibility audit with fixes"></a><br><sub><b>An accessibility audit with fixes</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/018-adaptive.png"><img src="docs/assets/screens/018-adaptive.png" alt="Context, pace and locale adapt the interface"></a><br><sub><b>Context, pace and locale adapt the interface</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/019-content.png"><img src="docs/assets/screens/019-content.png" alt="FAQs, change summaries and tours derived from existing content"></a><br><sub><b>FAQs, change summaries and tours derived from existing content</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/020-collaboration.png"><img src="docs/assets/screens/020-collaboration.png" alt="Thread summaries, decisions and reply drafts"></a><br><sub><b>Thread summaries, decisions and reply drafts</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/021-workflows.png"><img src="docs/assets/screens/021-workflows.png" alt="Agent runs with approvals and an audit trail"></a><br><sub><b>Agent runs with approvals and an audit trail</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/022-trust.png"><img src="docs/assets/screens/022-trust.png" alt="Redaction, injection defence, provenance and budgets"></a><br><sub><b>Redaction, injection defence, provenance and budgets</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/023-kernel.png"><img src="docs/assets/screens/023-kernel.png" alt="The fifteen-step AI kernel pipeline with live telemetry"></a><br><sub><b>The fifteen-step AI kernel pipeline with live telemetry</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/024-developer-tools.png"><img src="docs/assets/screens/024-developer-tools.png" alt="Scaffolding, UX review and test synthesis"></a><br><sub><b>Scaffolding, UX review and test synthesis</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/025-multimodal.png"><img src="docs/assets/screens/025-multimodal.png" alt="Voice, vision, illustration and sonification"></a><br><sub><b>Voice, vision, illustration and sonification</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/026-languages.png"><img src="docs/assets/screens/026-languages.png" alt="The same app in fourteen languages"></a><br><sub><b>The same app in fourteen languages</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/027-components.png"><img src="docs/assets/screens/027-components.png" alt="The component library"></a><br><sub><b>The component library</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/028-inputs.png"><img src="docs/assets/screens/028-inputs.png" alt="Input controls"></a><br><sub><b>Input controls</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/029-board.png"><img src="docs/assets/screens/029-board.png" alt="A board with suggested priorities"></a><br><sub><b>A board with suggested priorities</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/030-guided-tour.png"><img src="docs/assets/screens/030-guided-tour.png" alt="A guided tour spotlighting live nodes"></a><br><sub><b>A guided tour spotlighting live nodes</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/031-states.png"><img src="docs/assets/screens/031-states.png" alt="Generated empty states, skeletons and progress narration"></a><br><sub><b>Generated empty states, skeletons and progress narration</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/032-capability-explorer.png"><img src="docs/assets/screens/032-capability-explorer.png" alt="All 185 capabilities in a filterable table"></a><br><sub><b>All 185 capabilities in a filterable table</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/033-devtools.png"><img src="docs/assets/screens/033-devtools.png" alt="The built-in trace panel"></a><br><sub><b>The built-in trace panel</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/034-mobile.png"><img src="docs/assets/screens/034-mobile.png" alt="Responsive layout on a phone"></a><br><sub><b>Responsive layout on a phone</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/120-portable-logic.png"><img src="docs/assets/screens/120-portable-logic.png" alt="Portable logic: state, bindings and actions that run in the runtime and convert between all SDK languages"></a><br><sub><b>Portable logic: state, bindings and actions that run in the runtime and convert between all SDK languages</b></sub></td><td width="33%" valign="top"><a href="docs/assets/screens/121-platform-preview.png"><img src="docs/assets/screens/121-platform-preview.png" alt="One scene previewed with the iOS, Android and web skins"></a><br><sub><b>One scene previewed with the iOS, Android and web skins</b></sub></td></tr>
<tr><td width="33%" valign="top"><a href="docs/assets/screens/122-art-and-themes.png"><img src="docs/assets/screens/122-art-and-themes.png" alt="Procedural artwork and the twenty-seven theme presets"></a><br><sub><b>Procedural artwork and the twenty-seven theme presets</b></sub></td></tr>
</table>

</details>

122 screens in all, each captured from the running framework. Full-size versions with routes and notes are in [docs/gallery.md](docs/gallery.md).
<!-- gallery:end -->

## Components and themes

<!-- components:start -->
| Family | Components | What is in it |
| --- | --- | --- |
| [Layout](docs/reference/components.md#layout) | 19 | Pages, app shells, grids, splits, cards, tabs, dialogs, drawers, heroes and themed regions. `Page`, `Shell`, `Stack`, `Row`, `Grid` |
| [Content](docs/reference/components.md#content) | 29 | Text, badges, stats, callouts, timelines, lists, trees, threads, boards, chat, terminals and media players. `Heading`, `Text`, `Markdown`, `Badge`, `Tag` |
| [Input](docs/reference/components.md#input) | 19 | Buttons, text and choice controls, sliders, ratings, file drops, forms, PIN entry, swatches and control tiles. `Button`, `Input`, `TextArea`, `Select`, `Checkbox` |
| [Data](docs/reference/components.md#data) | 7 | Tables, charts, candlesticks, funnels, calendars, schedules and roadmaps. `Table`, `Chart`, `Candles`, `Funnel`, `Calendar` |
| [AI-native](docs/reference/components.md#ai-native) | 15 | The Intent Bar, the Copilot, generative regions, insight panels, approvals, agent timelines and prompt boxes. `IntentBar`, `Copilot`, `Suggestions`, `Insight`, `Provenance` |
| [Marketing and landing pages](docs/reference/components.md#marketing-and-landing-pages) | 15 | Navigation bars, bands, bento grids, feature blocks, pricing, testimonials, comparisons, FAQs and footers. `Landing`, `NavBar`, `Band`, `Bento`, `BentoCell` |
| [Commerce](docs/reference/components.md#commerce) | 5 | Product cards, carts, order summaries, rating summaries and media galleries. `ProductCard`, `Cart`, `OrderSummary`, `RatingSummary`, `MediaGallery` |
| [Visualisation, artwork and devices](docs/reference/components.md#visualisation-artwork-and-devices) | 11 | Procedural artwork, device frames, mobile screens, rings, gauges, sparklines, heatmaps, maps and waveforms. `Art`, `DeviceFrame`, `Screen`, `Rings`, `Gauge` |
| [Portable logic](docs/reference/components.md#portable-logic) | 3 | Behaviour that lives in the scene and runs in the runtime. `State`, `Show`, `Each` |
| **Total** | **123** | |
<!-- components:end -->

Twenty-seven theme presets ship with the runtime: `deep`, `abyss`, `iris`, `midnight`, `aurora`, `sunset`, `ember`, `ocean`, `forest`, `moss`, `rose`, `grape`, `citrus`, `sand`, `graphite`, `paper`, `terminal`, `crimson`, `candy`, `mint`, `gold`, `sky`, `emerald`, `neon`, `ruby`, `lagoon` and `tangerine`. A theme changes colour, radius, depth and the display typeface together; wrap any subtree in `ui.theme(...).prop("preset", "ocean")`, add `?theme=ocean` to a URL, or describe a new one in a sentence with `design.theme_prompt`. The reference is [docs/reference/components.md](docs/reference/components.md) and the guide is [docs/theming.md](docs/theming.md).

## Quickstart

Fluidian needs **Python 3.9 or newer** and nothing else. On Ubuntu, from the unzipped folder:

```bash
bash scripts/setup-ubuntu.sh        # 1. installs Python, Node.js and the other 12 language toolchains, then checks them
bash scripts/set-api-key.sh         # 2. optional: stores your OpenAI key; skip it to stay on the offline engine
bash scripts/test-all.sh            # 3. runs every automated test and prints one clear result
```

Then look around:

```bash
./fluidian showcase --open          # 85 complete screens: landing pages, storefronts, dashboards, AI products, mobile
./fluidian gallery --open           # every AI capability family, live
./fluidian run examples/portable/app.py
./fluidian new rust my-app --describe "contact form with name, email and message"
```

With a key configured, `./fluidian doctor --live` verifies it, lists the models your account can reach and makes one real call. The step-by-step guide, including a fresh Ubuntu virtual machine on a Mac, is [docs/getting-started.md](docs/getting-started.md).

## Testing

One command runs everything and needs no network, no API key and no human:

```bash
./fluidian test              # all suites; SDKs without a toolchain are reported as skipped
./fluidian test --quick      # engine and runtime only, a few seconds
./fluidian test --sdk go     # one SDK
./fluidian test --browser    # adds headless-Chrome checks of the gallery and the showcase
./fluidian test --json       # machine-readable summary for CI
```

| Area | What it proves |
| --- | --- |
| Engine | Schemas, colour maths and all twenty-seven themes, scene normalisation, the Reflex engine, the kernel's contracts for all 185 capabilities, the HTTP surface and its security checks, the CLI, every gallery page and all 85 showcase screens |
| Provider | The model path against a local stand-in for the OpenAI API: strict-schema validity for every model capability, parameter negotiation, retries, fallback, self-repair, redaction and caching |
| Conversion and platforms | Capture, emission in all fourteen languages, verification, rejection of a tampered project, the model-porting gate, token export in nine formats, native shells, the manifest, the service worker and the embed policy |
| Runtime | Server-side rendering of every component, output escaping, malformed-prop fuzzing, every capability presenter, and the portable-logic interpreter including its sandbox |
| SDK | For each of the 14 languages: a 24-message conformance transcript, the quickstart example, a scaffolded project that must build and run, and a converted six-route application that must reproduce its source |
| Browser | Every gallery page and every showcase screen in headless Chrome with zero runtime errors, plus interaction, theming, platform, install and embed checks |

Details are in [docs/testing.md](docs/testing.md).

## Configuration

Fluidian reads environment variables and an optional `fluidian.config.json`. The ones you are most likely to need:

| Variable | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Enables model-backed answers | unset: offline Reflex engine |
| `OPENAI_BASE_URL` | An OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `FLUIDIAN_MODEL_FAST`, `_BALANCED`, `_DEEP` | Pin the model for a tier | discovered from the account |
| `FLUIDIAN_OFFLINE` | Force the Reflex engine even with a key | `false` |
| `FLUIDIAN_PORT`, `FLUIDIAN_HOST` | Where the engine listens | `8787`, `127.0.0.1` |
| `FLUIDIAN_SESSION_TOKEN_BUDGET` | Token ceiling per session | `400000` |
| `FLUIDIAN_SHIELD` | Injection shield: `off`, `flag` or `block` | `flag` |
| `FLUIDIAN_EMBED_ORIGINS` | Sites allowed to embed the app with `<fluidian-app>` | none |

The full list is in [docs/configuration.md](docs/configuration.md).

## Documentation

| | |
| --- | --- |
| [Getting started](docs/getting-started.md) | Install, add a key, run the showcase and the gallery, write and run an app |
| [Why Fluidian](docs/why.md) | The problems it removes, what is new in it, and when not to use it |
| [Concepts](docs/concepts.md) | Scenes, nodes, events, state, routes, actions and AI attachments |
| [Portable logic](docs/portable-logic.md) | State, bindings, `Show`, `Each` and `@` actions |
| [Converting between languages](docs/convert.md) | Capture, emit, verify; probing and model-assisted porting |
| [Cross-platform](docs/cross-platform.md) | Platform skins, installable apps, embedding, native shells and token export |
| [Theming and artwork](docs/theming.md) | The twenty-seven presets, generated themes, typography and the `Art` component |
| [Screens](docs/gallery.md) | All 122 screens with routes and notes |
| [Architecture](docs/architecture.md) | Processes, data flow and the registries |
| [AI kernel](docs/ai-kernel.md) | The pipeline, Reflex, routing, caching, budgets and provenance |
| [OpenAI integration](docs/openai.md) | Structured Outputs, model selection, negotiation and failure handling |
| [Wire protocol](docs/protocol.md) | The complete specification, for SDK authors |
| [SDK guide](docs/sdks.md) | All fourteen languages side by side |
| [Capability reference](docs/reference/capabilities.md) | Every capability with inputs, outputs and a real result |
| [Component reference](docs/reference/components.md) | Every component with props and events |
| [Developer tools](docs/devtools.md) | The trace panel, scene review and the AI ledger |
| [Testing](docs/testing.md) | The suites, the conformance harness and writing tests |
| [Security](docs/security.md) | Threat model, defaults and the production checklist |
| [Deployment](docs/deployment.md) | Running behind a proxy, systemd, containers |
| [Configuration](docs/configuration.md) · [CLI](docs/cli.md) · [FAQ](docs/faq.md) · [Roadmap](docs/roadmap.md) | Reference and answers |

## Project status

Version 1.2.0. The wire protocol is at version 1 and is covered by the conformance suite. The release was verified on Ubuntu 24.04 (x86-64) with the toolchain versions listed in the SDK guide; run `./fluidian doctor` and `./fluidian test` to verify your own environment, and `./fluidian doctor --live` to verify your OpenAI account. What changed since 1.0.0 is in the [changelog](CHANGELOG.md).

## Contributing

Bug reports, capabilities, components, themes and new SDKs are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md); security reports go through [SECURITY.md](SECURITY.md).

## License

Fluidian is released under the [Apache License 2.0](LICENSE). The bundled typefaces (Inter, Space Grotesk, Instrument Serif and JetBrains Mono) are licensed under the SIL Open Font License 1.1; see [NOTICE](NOTICE).

<p align="center">
  <img src="docs/assets/logo.svg" width="36" alt="">
  <br>
  <sub>Fluidian — interfaces that think.</sub>
</p>
