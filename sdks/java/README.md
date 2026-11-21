# Fluidian for Java

Build AI-native interfaces from Java. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Java 11+ |
| Verified with | OpenJDK 21 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

Compile the sources under `sdks/java/src/main/java` with your application, or build a jar with the provided `pom.xml`.

## Quickstart

`src/examples/java/dev/fluidian/examples/Quickstart.java`

```java
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
```

Run it from the repository root:

```bash
javac -encoding UTF-8 -d out $(find sdks/java/src -name '*.java')
./fluidian run -- java -cp out dev.fluidian.examples.Quickstart
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Java

`ctx.state` is a `Map<String, Object>`; JSON integers decode to `Long`. `J.obj(...)` and `J.arr(...)` build JSON literals. `ctx.ai()` throws `AIException`.

## Move to or from Java

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to java          # from another language to Java
./fluidian convert my-java-app/ --to all     # from a Java project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk java
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Java, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
