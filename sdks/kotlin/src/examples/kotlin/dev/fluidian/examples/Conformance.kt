// Conformance application: exercises every SDK feature against the shared transcript.
package dev.fluidian.examples

import dev.fluidian.AIException
import dev.fluidian.App
import dev.fluidian.UI

fun main() {
    val app = App("Conformance")

    app.view { ctx ->
        val page = UI.page("Conformance",
            UI.text("Count: ${ctx.state["count"] ?: 0}").id("count"),
            UI.text("Hello, ${ctx.state["name"] ?: "world"}!").id("greeting"),
            UI.text("Route: ${ctx.route}").id("route")
        ).id("root")
        if (ctx.state.containsKey("summary")) page.add(UI.text("Summary: ${ctx.state["summary"]}").id("summary"))
        if (ctx.state.containsKey("last")) page.add(UI.text("Last: ${ctx.state["last"]}").id("last"))
        page.add(UI.button("Increment").id("inc").on("click", "increment"))
        page.add(conformanceScene())
        page
    }

    app.on("increment") { ctx, _ -> ctx.state["count"] = ((ctx.state["count"] as? Long) ?: 0L) + 1L }
    app.on("set_name") { ctx, ev -> ctx.state["name"] = ev.value }
    app.on("submit") { ctx, ev ->
        ctx.toast("Saved ${ev.form["email"]} (${ev.form["plan"]} × ${ev.form["seats"]})", "success")
    }
    app.on("ask_ai") { ctx, _ ->
        ctx.state["summary"] = ctx.ai("content.summarize", mapOf("text" to "Fluidian"))["title"]
    }
    app.on("fail_ai") { ctx, _ ->
        try {
            ctx.ai("content.summarize")
        } catch (error: AIException) {
            ctx.toast("AI unavailable: ${error.message}", "warning")
        }
    }
    app.on("go") { ctx, ev -> ctx.navigate(ev.payloadMap["route"].toString()) }
    app.on("boom") { _, _ -> throw IllegalStateException("boom") }
    app.action("add_item", "Add an item to the list", mapOf("title" to "string title")) { ctx, ev ->
        ctx.state["last"] = ev.payloadMap["title"]
    }

    app.run()
}
