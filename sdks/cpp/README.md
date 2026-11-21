# Fluidian for C++

Build AI-native interfaces from C++. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | C++17 |
| Verified with | GCC 13 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

Header-only. Add `sdks/cpp/include` to the include path, or use the provided `CMakeLists.txt` (`fluidian::fluidian`).

## Quickstart

`examples/quickstart.cpp`

```cpp
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   g++ -std=c++17 -Iinclude examples/quickstart.cpp -o quickstart && fluidian run -- ./quickstart
#include <fluidian/fluidian.hpp>

using namespace fluidian;

int main() {
  App app("Quickstart");

  app.view([](Ctx& ctx) {
    Node page = ui::page("Quickstart", {
      ui::text("Count: " + std::to_string(ctx.state.get("count").as_int())).id("count"),
      ui::button("Add one").id("add").on("click", "increment"),
      ui::text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
      ui::button("Summarise").id("summarise").on("click", "summarise"),
    });
    if (ctx.state.has("summary")) page.add(ui::callout(ctx.state.get("summary").str()).id("summary"));
    return page;
  });

  app.on("increment", [](Ctx& ctx, const Event&) { ctx.state.set("count", ctx.state.get("count").as_int() + 1); });
  app.on("set_notes", [](Ctx& ctx, const Event& ev) { ctx.state.set("notes", ev.value); });
  app.on("summarise", [](Ctx& ctx, const Event&) {
    try {
      Json result = ctx.ai("content.summarize", Json::object({{"text", ctx.state.get("notes").as_string()}}));
      ctx.state.set("summary", result.get("title"));
    } catch (const AIError& error) {
      ctx.toast(std::string("Could not summarise: ") + error.what(), "warning");
    }
  });
  app.action("reset", "Reset the counter to zero", Json::object(),
             [](Ctx& ctx, const Event&) { ctx.state.set("count", 0); });

  app.run();
  return 0;
}
```

Run it from the repository root:

```bash
g++ -std=c++17 -Isdks/cpp/include sdks/cpp/examples/quickstart.cpp -o quickstart
./fluidian run -- ./quickstart
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for C++

`ctx.state` is a `fluidian::Json` object with `get`, `set` and `has`. `ctx.ai()` throws `AIError`. Exceptions thrown by handlers are reported to the engine.

## Move to or from C++

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to cpp          # from another language to C++
./fluidian convert my-cpp-app/ --to all     # from a C++ project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk cpp
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into C++, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
