<p align="right"><a href="../README.md"><img src="assets/wordmark.svg" height="28" alt="Fluidian"></a></p>

# Roadmap

This page lists what is planned and what is deliberately out of scope. It describes direction, not dates.

## Where 1.1 stands

- Wire protocol version 1, with a conformance suite that all fourteen SDKs pass.
- 185 capabilities, each with a model path and an offline path.
- 123 components in nine families, twenty-seven themes, one registry, generated factories for every language.
- Portable logic: state, bindings and actions that live in the scene.
- Verified conversion between all fourteen languages.
- Platform skins for iOS and Android, an installable web app, an embed element, native shell projects and design-token export in nine formats.
- Verified on Ubuntu 24.04 (x86-64) with the toolchains listed in the [SDK guide](sdks.md).

## Next

**Identity pass-through.** Deliver verified identity headers from a trusted proxy to the app in the `open` message, so handlers can authorise without their own session layer.

**Packages on the public registries.** The SDKs are installed from the repository today. Publishing to PyPI, npm, crates.io, Maven Central, NuGet, RubyGems, Packagist, pub.dev, Hex and LuaRocks is planned once the 1.x API has settled.

**A Swift SDK.** Planned as the fifteenth language. Like every SDK, it ships when it passes the conformance suite on its own toolchain.

**Session stores.** Optional external storage for session state, to remove the need for session affinity and to survive restarts.

**WebSocket transport.** As an alternative to server-sent events where proxies make long-lived streams awkward.

**The Responses API.** An additional provider client alongside Chat Completions, selected per model.

**Reflex beyond English.** The offline engine's text rules are English-first. Dates, numbers and formats are next for localisation.

**Component extensions.** A supported way to ship third-party components — registry entry, renderer and styles — as one package.

**Built native shells.** `fluidian package` writes iOS, Android and desktop projects in source form. Building and signing them in a hosted pipeline, and running them in the test suite, comes next.

**Portable handlers.** A larger portable-logic vocabulary (validation rules, derived state, timers) so that more applications convert between languages with nothing left to port.

**Verified ARM64 and macOS runs.** The code has no architecture-specific parts; the conformance suite will be run and published for both.

## Later

- Collaborative sessions: several people on one scene, with presence.
- A visual scene editor built with Fluidian itself.
- Evaluation harness for capabilities: scored test sets per capability, run against any model.
- Native renderers that consume the same scenes outside the browser.

## Out of scope

- **A client-side application framework.** Business logic stays on the server. Portable logic covers interaction that only changes what is shown; it will not grow into a general-purpose language.
- **A model gateway.** The kernel routes among models of the provider you configure; it is not a multi-tenant proxy.
- **Hidden AI.** Generated content will always be marked and attributable.

## Influencing the roadmap

Open an issue describing the problem you are trying to solve. Proposals that come with a capability declaration, a component entry or a failing conformance case are the easiest to act on.
