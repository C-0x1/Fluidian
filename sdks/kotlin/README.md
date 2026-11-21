# Fluidian for Kotlin

Build AI-native interfaces from Kotlin. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Kotlin 1.3+ on JVM 11+ |
| Verified with | kotlinc 1.3 on OpenJDK 21 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

Add `sdks/kotlin/src/main/kotlin` to your source set, or use the provided `build.gradle.kts`.

## Quickstart

`src/examples/kotlin/dev/fluidian/examples/Quickstart.kt`

```kotlin
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
```

Run it from the repository root:

```bash
kotlinc sdks/kotlin/src/main/kotlin sdks/kotlin/src/examples/kotlin/dev/fluidian/examples/Quickstart.kt -include-runtime -d quickstart.jar
./fluidian run -- java -cp quickstart.jar dev.fluidian.examples.QuickstartKt
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Kotlin

Handlers are lambdas `(Ctx, Event) -> Unit`. `ctx.state` is a `MutableMap<String, Any?>`; JSON integers decode to `Long`. `ctx.ai()` throws `AIException`.

## Move to or from Kotlin

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to kotlin          # from another language to Kotlin
./fluidian convert my-kotlin-app/ --to all     # from a Kotlin project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk kotlin
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Kotlin, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
