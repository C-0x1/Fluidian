// Conformance application: exercises every SDK feature against the shared transcript.
using Fluidian;

var app = new App("Conformance");

app.View(ctx =>
{
    var page = UI.Page("Conformance",
        UI.Text($"Count: {ctx.State.GetValueOrDefault("count", 0L)}").Id("count"),
        UI.Text($"Hello, {ctx.State.GetValueOrDefault("name", "world")}!").Id("greeting"),
        UI.Text($"Route: {ctx.Route}").Id("route")).Id("root");
    if (ctx.State.ContainsKey("summary")) page.Add(UI.Text($"Summary: {ctx.State["summary"]}").Id("summary"));
    if (ctx.State.ContainsKey("last")) page.Add(UI.Text($"Last: {ctx.State["last"]}").Id("last"));
    page.Add(UI.Button("Increment").Id("inc").On("click", "increment"));
    page.Add(ConformanceScene.Build());
    return page;
});

app.On("increment", (ctx, ev) => ctx.State["count"] = (long)ctx.State.GetValueOrDefault("count", 0L)! + 1);
app.On("set_name", (ctx, ev) => ctx.State["name"] = ev.Value);
app.On("submit", (ctx, ev) => ctx.Toast($"Saved {ev.Form["email"]} ({ev.Form["plan"]} × {ev.Form["seats"]})", "success"));
app.On("ask_ai", (ctx, ev) => ctx.State["summary"] = ctx.Ai("content.summarize", J.Obj("text", "Fluidian"))["title"]);
app.On("fail_ai", (ctx, ev) =>
{
    try { ctx.Ai("content.summarize"); }
    catch (AIException error) { ctx.Toast($"AI unavailable: {error.Message}", "warning"); }
});
app.On("go", (ctx, ev) => ctx.Navigate((string)((Dictionary<string, object?>)ev.Payload!)["route"]!));
app.On("boom", (ctx, ev) => throw new InvalidOperationException("boom"));
app.Action("add_item", "Add an item to the list", J.Obj("title", "string title"),
    (ctx, ev) => ctx.State["last"] = ((Dictionary<string, object?>)ev.Payload!)["title"]);

app.Run();
