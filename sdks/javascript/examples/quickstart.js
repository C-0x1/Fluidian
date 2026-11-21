"use strict";
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- node sdks/javascript/examples/quickstart.js
const { App, AIError, ui } = require("../index.js");

const app = new App("Quickstart");

app.view((ctx) => {
  const page = ui.page(
    "Quickstart",
    ui.text(`Count: ${ctx.state.count || 0}`).id("count"),
    ui.button("Add one").id("add").on("click", "increment"),
    ui.textArea("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
    ui.button("Summarise").id("summarise").on("click", "summarise"),
  );
  if ("summary" in ctx.state) page.add(ui.callout(String(ctx.state.summary)).id("summary"));
  return page;
});

app.on("increment", (ctx) => { ctx.state.count = (ctx.state.count || 0) + 1; });
app.on("set_notes", (ctx, event) => { ctx.state.notes = event.value; });
app.on("summarise", (ctx) => {
  try {
    ctx.state.summary = ctx.ai("content.summarize", { text: ctx.state.notes || "" }).title;
  } catch (err) {
    if (!(err instanceof AIError)) throw err;
    ctx.toast(`Could not summarise: ${err.message}`, "warning");
  }
});
app.action("reset", "Reset the counter to zero", {}, (ctx) => { ctx.state.count = 0; });

app.run();
