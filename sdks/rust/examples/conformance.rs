// Conformance application: exercises every SDK feature against the shared transcript.
use fluidian::{jobj, ui, App};

#[path = "conformance_scene.rs"]
mod conformance_scene;

fn main() {
    let mut app = App::new("Conformance");

    app.view(|ctx| {
        let mut page = ui::page("Conformance", vec![
            ui::text(&format!("Count: {}", ctx.state.int("count"))).id("count"),
            ui::text(&format!("Hello, {}!", ctx.state.text("name", "world"))).id("greeting"),
            ui::text(&format!("Route: {}", ctx.route())).id("route"),
        ])
        .id("root");
        if ctx.state.has("summary") {
            page = page.push(ui::text(&format!("Summary: {}", ctx.state.get("summary"))).id("summary"));
        }
        if ctx.state.has("last") {
            page = page.push(ui::text(&format!("Last: {}", ctx.state.get("last"))).id("last"));
        }
        page.push(ui::button("Increment").id("inc").on("click", "increment"))
            .push(conformance_scene::conformance_scene())
    });

    app.on("increment", |ctx, _| {
        let next = ctx.state.int("count") + 1;
        ctx.state.set("count", next);
        Ok(())
    });
    app.on("set_name", |ctx, ev| {
        ctx.state.set("name", &ev.value);
        Ok(())
    });
    app.on("submit", |ctx, ev| {
        let text = format!("Saved {} ({} × {})", ev.form.get("email"), ev.form.get("plan"), ev.form.get("seats"));
        ctx.toast(&text, "success");
        Ok(())
    });
    app.on("ask_ai", |ctx, _| {
        let result = ctx.ai("content.summarize", jobj! {"text" => "Fluidian"})?;
        ctx.state.set("summary", result.get("title"));
        Ok(())
    });
    app.on("fail_ai", |ctx, _| {
        if let Err(error) = ctx.ai("content.summarize", jobj! {}) {
            ctx.toast(&format!("AI unavailable: {}", error), "warning");
        }
        Ok(())
    });
    app.on("go", |ctx, ev| {
        let route = ev.payload.get("route").to_string();
        ctx.navigate(&route);
        Ok(())
    });
    app.on("boom", |_, _| Err("boom".into()));
    app.action("add_item", "Add an item to the list", jobj! {"title" => "string title"}, |ctx, ev| {
        ctx.state.set("last", ev.payload.get("title"));
        Ok(())
    });

    app.run();
}
