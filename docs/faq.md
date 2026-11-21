<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Frequently asked questions

## General

**Do I need an OpenAI key?**
No. Without one, every capability is answered by the Reflex engine, which is deterministic code inside the engine. The gallery, the tests and your development loop all work offline. A key upgrades the answers; it does not unlock features.

**Is the Reflex engine a model?**
No. It is rules, parsers, statistics and templates. It is good at structured tasks — dates, quantities, formats, colour maths, anomalies, routing by keywords — and plainer than a model at open-ended writing and composition. Results are labelled `reflex` so nobody mistakes one for the other.

**What does "server-driven" mean for my users?**
Your code runs on your server, in your language, next to your data. The browser receives a description of the screen and sends back events. There is no client application to build, version or secure separately.

**Which browsers are supported?**
The runtime uses standard ES modules, `fetch` and server-sent events, with no polyfills and no build step. It is developed and tested in Chrome; other current browsers implement the same standards.

**Does it work on phones?**
Yes. Components reflow to the space they are given, the runtime applies iOS or Android control conventions, and the engine serves a manifest and service worker so the app can be installed from the browser. `fluidian package` also writes native shell projects. See [Cross-platform](cross-platform.md).

**Do I need a separate mobile codebase?**
No. The scene your application returns is the same on every platform; only its skin changes. The `Screen` component gives phone screens a title area, bottom tabs and a floating action.

**Can I move an application to another language?**
Yes: `./fluidian convert app.py --to go`. Screens, portable logic and declared actions convert exactly, and the result is built, run and compared with the source before it is reported as verified. Handlers with business logic become marked stubs, or are translated by the model behind the same verification. See [Converting between languages](convert.md).

**Can I put a Fluidian app inside my existing site?**
Yes, with one element: `<fluidian-app src="https://your-app">`. It works in any page or framework, sizes itself to its content, and is refused by default until you list the host in `FLUIDIAN_EMBED_ORIGINS`. See [Embedding](cross-platform.md#embedding).

## AI

**Which models does it use?**
Capabilities ask for a tier — fast, balanced or deep — and the engine maps tiers to the models your account can reach. See [OpenAI integration](openai.md#model-selection). You can pin models per tier.

**Can I use a different provider?**
Any endpoint that implements the OpenAI Chat Completions API with JSON-schema response formats can be used through `OPENAI_BASE_URL`. The client negotiates parameter differences automatically and falls back to JSON mode with local validation when strict schemas are not supported.

**What is sent to the provider?**
The capability's instruction and its input after redaction. Personal data found in the input is replaced by placeholders first. Your API key, session identifiers and unrelated application state are not sent. See [Security](security.md#the-model-path).

**Can a model run my code or change my data?**
Only through actions you registered, with arguments you can validate, and with an approval step for anything the kernel rates as risky. Output that names an unregistered action is discarded.

**What happens when the provider is slow or down?**
Requests are retried with backoff, then the next model in the tier is tried, then the Reflex engine answers. The interface keeps working and the result is marked as degraded.

**How do I control cost?**
Token budgets per session and per process, a result cache with a semantic layer, request coalescing, and `direct` and `hybrid` capabilities that use few or no tokens. `./fluidian ai perf.telemetry` shows usage per capability.

**Are results reproducible?**
Reflex results are deterministic. Model results can be recorded once and replayed with `FLUIDIAN_REPLAY`, which is how to make demos and regression tests stable.

## Building

**How do I add my own component?**
Add an entry to the component registry, a renderer in `runtime/components.js` and styles, then run `./fluidian codegen`. All fourteen SDKs gain a factory. See [CONTRIBUTING.md](../CONTRIBUTING.md#adding-a-component).

**How do I add my own capability?**
One `cap(...)` declaration with a Reflex implementation. See [the kernel guide](ai-kernel.md#adding-a-capability).

**Where does state live?**
In two places. What the server knows lives in the app process, per session, in `ctx.state`; it is not persisted, so store durable data wherever your application already stores data. What the page is doing (a draft, an open panel, a counter) can live in the scene as a `State` node and is handled by the runtime with no round trip. See [Portable logic](portable-logic.md).

**Is portable logic a second programming language to learn?**
It is expressions and eleven verbs: `count += 1`, `toggle open`, `push todos {text: draft}`. It cannot define functions, loop or reach outside page state, which is what keeps it portable and safe. Anything larger belongs in a handler.

**Do the pictures in the showcase need hosting?**
No. Product shots, landscapes, portraits and device frames are drawn by the `Art` and `DeviceFrame` components as SVG from a few props. The showcase contains no image files.

**How do routes work?**
The browser's path is the route. The view reads `ctx.route` and returns the scene for it; `ctx.navigate()` and links change it without a page load.

**Can I use my language's async features?**
Handlers are synchronous and `ctx.ai` blocks, by design: the same code shape works in all fourteen languages. Long-running work belongs in your own job system, with the result written to state by a later event.

**Can the interface be rendered without JavaScript?**
`fluidian export` renders any scene to static HTML with the same renderers. Interactive behaviour needs the runtime.

**My language is not among the fourteen.**
The protocol is small and specified, and the conformance suite tells you when you are done. See [Writing a new SDK](protocol.md#writing-a-new-sdk).

## Operations

**How do people log in?**
Version 1 has no built-in authentication. Put the engine behind your identity layer. See [Security](security.md#what-is-your-responsibility).

**Can I run several instances?**
Yes, with session affinity at the load balancer. See [Deployment](deployment.md#state-and-scaling).

**Is there telemetry sent to the Fluidian project?**
No. The engine makes no network connections other than to the provider you configure.

**What is the licence?**
Apache 2.0. The bundled typefaces (Inter, Space Grotesk, Instrument Serif and JetBrains Mono) are under the SIL Open Font License 1.1.
