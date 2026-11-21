# Fluidian for Go

Build AI-native interfaces from Go. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Go 1.18+ |
| Verified with | Go 1.24 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```go
// go.mod
require github.com/fluidian/fluidian/sdks/go v1.2.0
replace github.com/fluidian/fluidian/sdks/go => /path/to/fluidian/sdks/go   // until you depend on a tagged release
```

## Quickstart

`cmd/quickstart/main.go`

```go
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//	fluidian run -- go run ./cmd/quickstart
package main

import (
	"fmt"

	fl "github.com/fluidian/fluidian/sdks/go"
)

func main() {
	app := fl.NewApp("Quickstart")

	app.View(func(ctx *fl.Ctx) *fl.Node {
		count, _ := ctx.State["count"].(int)
		page := fl.Page("Quickstart",
			fl.Text(fmt.Sprintf("Count: %d", count)).ID("count"),
			fl.Button("Add one").ID("add").On("click", "increment"),
			fl.TextArea("notes").Prop("label", "Notes").ID("notes").AI("input.ghost").On("change", "set_notes"),
			fl.Button("Summarise").ID("summarise").On("click", "summarise"),
		)
		if summary, ok := ctx.State["summary"]; ok {
			page.Add(fl.Callout(fmt.Sprint(summary)).ID("summary"))
		}
		return page
	})

	app.On("increment", func(ctx *fl.Ctx, ev fl.Event) {
		count, _ := ctx.State["count"].(int)
		ctx.State["count"] = count + 1
	})
	app.On("set_notes", func(ctx *fl.Ctx, ev fl.Event) { ctx.State["notes"] = ev.Value })
	app.On("summarise", func(ctx *fl.Ctx, ev fl.Event) {
		notes, _ := ctx.State["notes"].(string)
		result, err := ctx.AI("content.summarize", fl.M{"text": notes})
		if err != nil {
			ctx.Toast("Could not summarise: "+err.Error(), "warning")
			return
		}
		ctx.State["summary"] = result["title"]
	})
	app.Action("reset", "Reset the counter to zero", fl.M{}, func(ctx *fl.Ctx, ev fl.Event) { ctx.State["count"] = 0 })

	app.Run()
}
```

Run it from the repository root:

```bash
cd sdks/go && ../../fluidian run -- go run ./cmd/quickstart
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Go

`ctx.State` is `map[string]any`; JSON integers decode to `int`. `ctx.AI()` returns `(fl.M, error)`. A panic in a handler is reported to the engine, not fatal.

## Move to or from Go

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to go          # from another language to Go
./fluidian convert my-go-app/ --to all     # from a Go project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk go
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Go, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
