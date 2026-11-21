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
