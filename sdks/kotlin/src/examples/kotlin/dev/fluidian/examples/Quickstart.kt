// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   kotlinc src -include-runtime -d quickstart.jar && fluidian run -- java -cp quickstart.jar dev.fluidian.examples.QuickstartKt
package dev.fluidian.examples

import dev.fluidian.AIException
import dev.fluidian.App
import dev.fluidian.UI

fun main() {
    val app = App("Quickstart")

    app.view { ctx ->
        val page = UI.page("Quickstart",
            UI.text("Count: ${ctx.state["count"] ?: 0}").id("count"),
            UI.button("Add one").id("add").on("click", "increment"),
            UI.textArea("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
            UI.button("Summarise").id("summarise").on("click", "summarise")
        )
        val summary = ctx.state["summary"]
        if (summary != null) page.add(UI.callout(summary.toString()).id("summary"))
        page
    }

    app.on("increment") { ctx, _ -> ctx.state["count"] = ((ctx.state["count"] as? Long) ?: 0L) + 1L }
    app.on("set_notes") { ctx, ev -> ctx.state["notes"] = ev.value }
    app.on("summarise") { ctx, _ ->
        try {
            val result = ctx.ai("content.summarize", mapOf("text" to (ctx.state["notes"] ?: "")))
            ctx.state["summary"] = result["title"]
        } catch (error: AIException) {
            ctx.toast("Could not summarise: ${error.message}", "warning")
        }
    }
    app.action("reset", "Reset the counter to zero", emptyMap()) { ctx, _ -> ctx.state["count"] = 0L }

    app.run()
}
