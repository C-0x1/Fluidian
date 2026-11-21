// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- cargo run --quiet --example quickstart
use fluidian::{jobj, ui, App};

fn main() {
    let mut app = App::new("Quickstart");

    app.view(|ctx| {
        let mut page = ui::page("Quickstart", vec![
            ui::text(&format!("Count: {}", ctx.state.int("count"))).id("count"),
            ui::button("Add one").id("add").on("click", "increment"),
            ui::text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
            ui::button("Summarise").id("summarise").on("click", "summarise"),
        ]);
        if ctx.state.has("summary") {
            page = page.push(ui::callout(&ctx.state.text("summary", ""), vec![]).id("summary"));
        }
        page
    });

    app.on("increment", |ctx, _| {
        let next = ctx.state.int("count") + 1;
        ctx.state.set("count", next);
        Ok(())
    });
    app.on("set_notes", |ctx, ev| {
        ctx.state.set("notes", &ev.value);
        Ok(())
    });
    app.on("summarise", |ctx, _| {
        let notes = ctx.state.text("notes", "");
        match ctx.ai("content.summarize", jobj! {"text" => notes}) {
            Ok(result) => ctx.state.set("summary", result.get("title")),
            Err(error) => ctx.toast(&format!("Could not summarise: {}", error), "warning"),
        }
        Ok(())
    });
    app.action("reset", "Reset the counter to zero", jobj! {}, |ctx, _| {
        ctx.state.set("count", 0);
        Ok(())
    });

    app.run();
}
