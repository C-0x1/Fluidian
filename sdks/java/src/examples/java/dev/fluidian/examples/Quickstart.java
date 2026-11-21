// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   javac -d out $(find src -name '*.java') && fluidian run -- java -cp out dev.fluidian.examples.Quickstart
package dev.fluidian.examples;

import dev.fluidian.AIException;
import dev.fluidian.App;
import dev.fluidian.J;
import dev.fluidian.Node;
import dev.fluidian.UI;

public final class Quickstart {
    public static void main(String[] args) {
        App app = new App("Quickstart");

        app.view(ctx -> {
            Node page = UI.page("Quickstart",
                    UI.text("Count: " + ctx.state.getOrDefault("count", 0L)).id("count"),
                    UI.button("Add one").id("add").on("click", "increment"),
                    UI.textArea("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
                    UI.button("Summarise").id("summarise").on("click", "summarise"));
            if (ctx.state.containsKey("summary")) {
                page.add(UI.callout(String.valueOf(ctx.state.get("summary"))).id("summary"));
            }
            return page;
        });

        app.on("increment", (ctx, ev) -> ctx.state.put("count", (Long) ctx.state.getOrDefault("count", 0L) + 1));
        app.on("set_notes", (ctx, ev) -> ctx.state.put("notes", ev.value));
        app.on("summarise", (ctx, ev) -> {
            try {
                Object notes = ctx.state.getOrDefault("notes", "");
                ctx.state.put("summary", ctx.ai("content.summarize", J.obj("text", notes)).get("title"));
            } catch (AIException error) {
                ctx.toast("Could not summarise: " + error.getMessage(), "warning");
            }
        });
        app.action("reset", "Reset the counter to zero", J.obj(), (ctx, ev) -> ctx.state.put("count", 0L));

        app.run();
    }
}
