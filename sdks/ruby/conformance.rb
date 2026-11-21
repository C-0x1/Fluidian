# frozen_string_literal: true
# Conformance application: exercises every SDK feature against the shared transcript.
require "fluidian"
require_relative "conformance_scene"

UI = Fluidian::UI
app = Fluidian::App.new("Conformance")

app.view do |ctx|
  page = UI.page(
    "Conformance",
    UI.text("Count: #{ctx.state.fetch('count', 0)}").id("count"),
    UI.text("Hello, #{ctx.state.fetch('name', 'world')}!").id("greeting"),
    UI.text("Route: #{ctx.route}").id("route")
  ).id("root")
  page.add(UI.text("Summary: #{ctx.state['summary']}").id("summary")) if ctx.state.key?("summary")
  page.add(UI.text("Last: #{ctx.state['last']}").id("last")) if ctx.state.key?("last")
  page.add(UI.button("Increment").id("inc").on("click", "increment"))
  page.add(conformance_scene)
end

app.on("increment") { |ctx, _event| ctx.state["count"] = ctx.state.fetch("count", 0) + 1 }
app.on("set_name") { |ctx, event| ctx.state["name"] = event.value }
app.on("submit") do |ctx, event|
  f = event.form
  ctx.toast("Saved #{f['email']} (#{f['plan']} × #{f['seats']})", "success")
end
app.on("ask_ai") { |ctx, _event| ctx.state["summary"] = ctx.ai("content.summarize", { "text" => "Fluidian" })["title"] }
app.on("fail_ai") do |ctx, _event|
  ctx.ai("content.summarize", {})
rescue Fluidian::AIError => e
  ctx.toast("AI unavailable: #{e.message}", "warning")
end
app.on("go") { |ctx, event| ctx.navigate(event.payload["route"]) }
app.on("boom") { |_ctx, _event| raise "boom" }
app.action("add_item", "Add an item to the list", { "title" => "string title" }) { |ctx, event| ctx.state["last"] = event.payload["title"] }

app.run
