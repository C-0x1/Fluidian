# Fluidian for Elixir

Build AI-native interfaces from Elixir. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Elixir 1.14+ |
| Verified with | Elixir 1.14 on OTP 24 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```elixir
# mix.exs
{:fluidian, path: "/path/to/fluidian/sdks/elixir"}
```

## Quickstart

`examples/quickstart.exs`

```elixir
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
```

Run it from the repository root:

```bash
./fluidian run -- elixir sdks/elixir/examples/quickstart.exs
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Elixir

The API is functional: handlers receive the context and return it. `Ctx.ai/3` returns `{:ok, data}` or `{:error, message}`.

## Move to or from Elixir

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to elixir          # from another language to Elixir
./fluidian convert my-elixir-app/ --to all     # from a Elixir project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk elixir
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Elixir, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
