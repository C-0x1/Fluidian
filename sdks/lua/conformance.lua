-- Conformance application: exercises every SDK feature against the shared transcript.
local fl = require("fluidian")
local ui = fl.ui
local conformance_scene = require("conformance_scene")

local app = fl.App("Conformance")

app:view(function(ctx)
  local page = ui.page("Conformance",
    ui.text("Count: " .. (ctx.state.count or 0)):id("count"),
    ui.text("Hello, " .. (ctx.state.name or "world") .. "!"):id("greeting"),
    ui.text("Route: " .. ctx.route):id("route")):id("root")
  if ctx.state.summary ~= nil then page:add(ui.text("Summary: " .. ctx.state.summary):id("summary")) end
  if ctx.state.last ~= nil then page:add(ui.text("Last: " .. ctx.state.last):id("last")) end
  page:add(ui.button("Increment"):id("inc"):on("click", "increment"))
  page:add(conformance_scene())
  return page
end)

app:on("increment", function(ctx) ctx.state.count = (ctx.state.count or 0) + 1 end)
app:on("set_name", function(ctx, event) ctx.state.name = event.value end)
app:on("submit", function(ctx, event)
  local f = event.form
  ctx:toast("Saved " .. f.email .. " (" .. f.plan .. " × " .. f.seats .. ")", "success")
end)
app:on("ask_ai", function(ctx)
  local result = ctx:ai("content.summarize", { text = "Fluidian" })
  if result then ctx.state.summary = result.title end
end)
app:on("fail_ai", function(ctx)
  local result, err = ctx:ai("content.summarize")
  if not result then ctx:toast("AI unavailable: " .. err, "warning") end
end)
app:on("go", function(ctx, event) ctx:navigate(event.payload.route) end)
app:on("boom", function() error("boom") end)
app:action("add_item", "Add an item to the list", { title = "string title" }, function(ctx, event) ctx.state.last = event.payload.title end)

app:run()
