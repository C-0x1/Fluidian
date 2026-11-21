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
