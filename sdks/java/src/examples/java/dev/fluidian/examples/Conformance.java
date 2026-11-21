// Conformance application: exercises every SDK feature against the shared transcript.
package dev.fluidian.examples;

import dev.fluidian.AIException;
import dev.fluidian.App;
import dev.fluidian.J;
import dev.fluidian.Node;
import dev.fluidian.UI;

public final class Conformance {
    public static void main(String[] args) {
        App app = new App("Conformance");

        app.view(ctx -> {
            Node page = UI.page("Conformance",
                    UI.text("Count: " + ctx.state.getOrDefault("count", 0L)).id("count"),
                    UI.text("Hello, " + ctx.state.getOrDefault("name", "world") + "!").id("greeting"),
                    UI.text("Route: " + ctx.route()).id("route")).id("root");
            if (ctx.state.containsKey("summary")) {
                page.add(UI.text("Summary: " + ctx.state.get("summary")).id("summary"));
            }
            if (ctx.state.containsKey("last")) {
                page.add(UI.text("Last: " + ctx.state.get("last")).id("last"));
            }
            page.add(UI.button("Increment").id("inc").on("click", "increment"));
            page.add(ConformanceScene.build());
            return page;
        });

        app.on("increment", (ctx, ev) -> ctx.state.put("count", (Long) ctx.state.getOrDefault("count", 0L) + 1));
        app.on("set_name", (ctx, ev) -> ctx.state.put("name", ev.value));
        app.on("submit", (ctx, ev) -> ctx.toast("Saved " + ev.form.get("email") + " (" + ev.form.get("plan") + " × " + ev.form.get("seats") + ")", "success"));
        app.on("ask_ai", (ctx, ev) -> ctx.state.put("summary", ctx.ai("content.summarize", J.obj("text", "Fluidian")).get("title")));
        app.on("fail_ai", (ctx, ev) -> {
            try {
                ctx.ai("content.summarize", null);
            } catch (AIException error) {
                ctx.toast("AI unavailable: " + error.getMessage(), "warning");
            }
        });
        app.on("go", (ctx, ev) -> ctx.navigate((String) ev.payloadMap().get("route")));
        app.on("boom", (ctx, ev) -> {
            throw new IllegalStateException("boom");
        });
        app.action("add_item", "Add an item to the list", J.obj("title", "string title"), (ctx, ev) -> ctx.state.put("last", ev.payloadMap().get("title")));

        app.run();
    }
}
