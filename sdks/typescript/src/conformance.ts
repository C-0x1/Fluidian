// Conformance application: exercises every SDK feature against the shared transcript.
import { AIError, App, ui } from "./index";
import { conformanceScene } from "./conformance_scene";

const app = new App("Conformance");

app.view((ctx) => {
  const page = ui.page(
    "Conformance",
    ui.text(`Count: ${ctx.state.count ?? 0}`).id("count"),
    ui.text(`Hello, ${ctx.state.name ?? "world"}!`).id("greeting"),
    ui.text(`Route: ${ctx.route}`).id("route"),
  ).id("root");
  if ("summary" in ctx.state) page.add(ui.text(`Summary: ${ctx.state.summary}`).id("summary"));
  if ("last" in ctx.state) page.add(ui.text(`Last: ${ctx.state.last}`).id("last"));
  page.add(ui.button("Increment").id("inc").on("click", "increment"));
  page.add(conformanceScene());
  return page;
});

app.on("increment", (ctx) => { ctx.state.count = (ctx.state.count ?? 0) + 1; });
app.on("set_name", (ctx, event) => { ctx.state.name = event.value; });
app.on("submit", (ctx, event) => {
  const f = event.form;
  ctx.toast(`Saved ${f.email} (${f.plan} × ${f.seats})`, "success");
});
app.on("ask_ai", (ctx) => { ctx.state.summary = ctx.ai("content.summarize", { text: "Fluidian" }).title; });
app.on("fail_ai", (ctx) => {
  try {
    ctx.ai("content.summarize", {});
  } catch (err) {
    if (!(err instanceof AIError)) throw err;
    ctx.toast(`AI unavailable: ${err.message}`, "warning");
  }
});
app.on("go", (ctx, event) => ctx.navigate(event.payload.route));
app.on("boom", () => { throw new Error("boom"); });
app.action("add_item", "Add an item to the list", { title: "string title" }, (ctx, event) => { ctx.state.last = event.payload.title; });

app.run();
