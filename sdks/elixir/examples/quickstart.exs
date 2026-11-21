# Quickstart: a counter, an AI-assisted notes field and an AI summary.
#
#   fluidian run -- elixir sdks/elixir/examples/quickstart.exs
Code.require_file("../lib/fluidian.ex", __DIR__)
Code.require_file("../lib/fluidian/ui.ex", __DIR__)

alias Fluidian.{App, Ctx, Node, UI}

App.new("Quickstart")
|> App.view(fn ctx ->
  UI.page("Quickstart", [
    UI.text("Count: #{Ctx.get(ctx, "count", 0)}") |> Node.id("count"),
    UI.button("Add one") |> Node.id("add") |> Node.on("click", "increment"),
    UI.text_area("notes")
    |> Node.prop("label", "Notes")
    |> Node.id("notes")
    |> Node.ai("input.ghost")
    |> Node.on("change", "set_notes"),
    UI.button("Summarise") |> Node.id("summarise") |> Node.on("click", "summarise")
  ])
  |> Node.add(if Ctx.has?(ctx, "summary"), do: UI.callout(to_string(Ctx.get(ctx, "summary"))) |> Node.id("summary"))
end)
|> App.on("increment", fn ctx, _event -> Ctx.put(ctx, "count", Ctx.get(ctx, "count", 0) + 1) end)
|> App.on("set_notes", fn ctx, event -> Ctx.put(ctx, "notes", event.value) end)
|> App.on("summarise", fn ctx, _event ->
  case Ctx.ai(ctx, "content.summarize", %{"text" => Ctx.get(ctx, "notes", "")}) do
    {:ok, data} -> Ctx.put(ctx, "summary", data["title"])
    {:error, message} -> Ctx.toast(ctx, "Could not summarise: #{message}", "warning")
  end
end)
|> App.action("reset", "Reset the counter to zero", %{}, fn ctx, _event -> Ctx.put(ctx, "count", 0) end)
|> App.run()
