# Conformance application: exercises every SDK feature against the shared transcript.
Code.require_file("lib/fluidian.ex", __DIR__)
Code.require_file("lib/fluidian/ui.ex", __DIR__)
Code.require_file("conformance_scene.exs", __DIR__)

alias Fluidian.{App, Ctx, Node, UI}

App.new("Conformance")
|> App.view(fn ctx ->
  UI.page("Conformance", [
    UI.text("Count: #{Ctx.get(ctx, "count", 0)}") |> Node.id("count"),
    UI.text("Hello, #{Ctx.get(ctx, "name", "world")}!") |> Node.id("greeting"),
    UI.text("Route: #{ctx.route}") |> Node.id("route")
  ])
  |> Node.id("root")
  |> Node.add(if Ctx.has?(ctx, "summary"), do: UI.text("Summary: #{Ctx.get(ctx, "summary")}") |> Node.id("summary"))
  |> Node.add(if Ctx.has?(ctx, "last"), do: UI.text("Last: #{Ctx.get(ctx, "last")}") |> Node.id("last"))
  |> Node.add(UI.button("Increment") |> Node.id("inc") |> Node.on("click", "increment"))
  |> Node.add(ConformanceScene.build())
end)
|> App.on("increment", fn ctx, _event -> Ctx.put(ctx, "count", Ctx.get(ctx, "count", 0) + 1) end)
|> App.on("set_name", fn ctx, event -> Ctx.put(ctx, "name", event.value) end)
|> App.on("submit", fn ctx, event ->
  f = event.form
  Ctx.toast(ctx, "Saved #{f["email"]} (#{f["plan"]} × #{f["seats"]})", "success")
end)
|> App.on("ask_ai", fn ctx, _event ->
  case Ctx.ai(ctx, "content.summarize", %{"text" => "Fluidian"}) do
    {:ok, data} -> Ctx.put(ctx, "summary", data["title"])
    {:error, _} -> ctx
  end
end)
|> App.on("fail_ai", fn ctx, _event ->
  case Ctx.ai(ctx, "content.summarize") do
    {:ok, _} -> ctx
    {:error, message} -> Ctx.toast(ctx, "AI unavailable: #{message}", "warning")
  end
end)
|> App.on("go", fn ctx, event -> Ctx.navigate(ctx, event.payload["route"]) end)
|> App.on("boom", fn _ctx, _event -> raise "boom" end)
|> App.action("add_item", "Add an item to the list", %{"title" => "string title"}, fn ctx, event ->
  Ctx.put(ctx, "last", event.payload["title"])
end)
|> App.run()
