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
