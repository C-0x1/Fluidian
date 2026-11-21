# Fluidian for C#

Build AI-native interfaces from C#. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | C# 10, .NET 6+ |
| Verified with | .NET 8 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```xml
<ItemGroup>
  <ProjectReference Include="/path/to/fluidian/sdks/csharp/Fluidian/Fluidian.csproj" />
</ItemGroup>
```

## Quickstart

`examples/Quickstart/Program.cs`

```csharp
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- dotnet run --project sdks/csharp/examples/Quickstart
using Fluidian;

var app = new App("Quickstart");

app.View(ctx =>
{
    var page = UI.Page("Quickstart",
        UI.Text($"Count: {ctx.State.GetValueOrDefault("count", 0L)}").Id("count"),
        UI.Button("Add one").Id("add").On("click", "increment"),
        UI.TextArea("notes").Prop("label", "Notes").Id("notes").Ai("input.ghost").On("change", "set_notes"),
        UI.Button("Summarise").Id("summarise").On("click", "summarise"));
    if (ctx.State.TryGetValue("summary", out var summary)) page.Add(UI.Callout($"{summary}").Id("summary"));
    return page;
});

app.On("increment", (ctx, ev) => ctx.State["count"] = (long)ctx.State.GetValueOrDefault("count", 0L)! + 1);
app.On("set_notes", (ctx, ev) => ctx.State["notes"] = ev.Value);
app.On("summarise", (ctx, ev) =>
{
    try
    {
        var result = ctx.Ai("content.summarize", J.Obj("text", ctx.State.GetValueOrDefault("notes", "")));
        ctx.State["summary"] = result["title"];
    }
    catch (AIException error)
    {
        ctx.Toast($"Could not summarise: {error.Message}", "warning");
    }
});
app.Action("reset", "Reset the counter to zero", J.Obj(), (ctx, ev) => ctx.State["count"] = 0L);

app.Run();
```

Run it from the repository root:

```bash
./fluidian run -- dotnet run --project sdks/csharp/examples/Quickstart
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for C#

`ctx.State` is a `Dictionary<string, object?>`; JSON integers decode to `long`. `J.Obj(...)` builds JSON literals. `ctx.Ai()` throws `AIException`.

## Move to or from C#

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to csharp          # from another language to C#
./fluidian convert my-csharp-app/ --to all     # from a C# project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk csharp
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into C#, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
