# frozen_string_literal: true

# Quickstart: a counter, an AI-assisted notes field and an AI summary.
#
#   fluidian run -- ruby -Isdks/ruby/lib sdks/ruby/examples/quickstart.rb
require "fluidian"

UI = Fluidian::UI
app = Fluidian::App.new("Quickstart")

app.view do |ctx|
  page = UI.page(
    "Quickstart",
    UI.text("Count: #{ctx.state.fetch('count', 0)}").id("count"),
    UI.button("Add one").id("add").on("click", "increment"),
    UI.text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
    UI.button("Summarise").id("summarise").on("click", "summarise")
  )
  page.add(UI.callout(ctx.state["summary"].to_s).id("summary")) if ctx.state.key?("summary")
  page
end

app.on("increment") { |ctx, _event| ctx.state["count"] = ctx.state.fetch("count", 0) + 1 }
app.on("set_notes") { |ctx, event| ctx.state["notes"] = event.value }
app.on("summarise") do |ctx, _event|
  ctx.state["summary"] = ctx.ai("content.summarize", { "text" => ctx.state.fetch("notes", "") })["title"]
rescue Fluidian::AIError => e
  ctx.toast("Could not summarise: #{e.message}", "warning")
end
app.action("reset", "Reset the counter to zero", {}) { |ctx, _event| ctx.state["count"] = 0 }

app.run
