# Fluidian for Lua

Build AI-native interfaces from Lua. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Lua 5.3+ |
| Verified with | Lua 5.4 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

Inside a checkout the CLI sets `LUA_PATH` for the app process. Elsewhere, add `sdks/lua/?.lua` to `LUA_PATH` or install the rockspec.

## Quickstart

`examples/quickstart.lua`

```lua
-- Quickstart: a counter, an AI-assisted notes field and an AI summary.
--
--   LUA_PATH="sdks/lua/?.lua;;" fluidian run -- lua5.4 sdks/lua/examples/quickstart.lua
local fl = require("fluidian")
local ui = fl.ui

local app = fl.App("Quickstart")

app:view(function(ctx)
  local page = ui.page("Quickstart",
    ui.text("Count: " .. (ctx.state.count or 0)):id("count"),
    ui.button("Add one"):id("add"):on("click", "increment"),
    ui.text_area("notes"):prop("label", "Notes"):id("notes"):ai("input.ghost"):on("change", "set_notes"),
    ui.button("Summarise"):id("summarise"):on("click", "summarise"))
  if ctx.state.summary ~= nil then page:add(ui.callout(tostring(ctx.state.summary)):id("summary")) end
  return page
end)

app:on("increment", function(ctx) ctx.state.count = (ctx.state.count or 0) + 1 end)
app:on("set_notes", function(ctx, event) ctx.state.notes = event.value end)
app:on("summarise", function(ctx)
  local result, err = ctx:ai("content.summarize", { text = ctx.state.notes or "" })
  if result then
    ctx.state.summary = result.title
  else
    ctx:toast("Could not summarise: " .. err, "warning")
  end
end)
app:action("reset", "Reset the counter to zero", {}, function(ctx) ctx.state.count = 0 end)

app:run()
```

Run it from the repository root:

```bash
./fluidian run -- lua5.4 sdks/lua/examples/quickstart.lua
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Lua

`ctx.state` is a table. `ctx:ai()` returns the result, or `nil` and a message. Errors raised in handlers are reported to the engine.

## Move to or from Lua

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to lua          # from another language to Lua
./fluidian convert my-lua-app/ --to all     # from a Lua project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk lua
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Lua, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
