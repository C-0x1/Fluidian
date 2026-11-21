// Conformance application: exercises every SDK feature against the shared transcript.
package main

import (
	"fmt"

	fl "github.com/fluidian/fluidian/sdks/go"
)

func main() {
	app := fl.NewApp("Conformance")

	app.View(func(ctx *fl.Ctx) *fl.Node {
		count, _ := ctx.State["count"].(int)
		name, ok := ctx.State["name"].(string)
		if !ok {
			name = "world"
		}
		page := fl.Page("Conformance",
			fl.Text(fmt.Sprintf("Count: %d", count)).ID("count"),
			fl.Text(fmt.Sprintf("Hello, %s!", name)).ID("greeting"),
			fl.Text("Route: "+ctx.Route()).ID("route"),
		).ID("root")
		if summary, ok := ctx.State["summary"]; ok {
			page.Add(fl.Text(fmt.Sprintf("Summary: %v", summary)).ID("summary"))
		}
		if last, ok := ctx.State["last"]; ok {
			page.Add(fl.Text(fmt.Sprintf("Last: %v", last)).ID("last"))
		}
		page.Add(fl.Button("Increment").ID("inc").On("click", "increment"))
		page.Add(conformanceScene())
		return page
	})

	app.On("increment", func(ctx *fl.Ctx, ev fl.Event) {
		count, _ := ctx.State["count"].(int)
		ctx.State["count"] = count + 1
	})
	app.On("set_name", func(ctx *fl.Ctx, ev fl.Event) { ctx.State["name"] = ev.Value })
	app.On("submit", func(ctx *fl.Ctx, ev fl.Event) {
		ctx.Toast(fmt.Sprintf("Saved %v (%v × %v)", ev.Form["email"], ev.Form["plan"], ev.Form["seats"]), "success")
	})
	app.On("ask_ai", func(ctx *fl.Ctx, ev fl.Event) {
		if result, err := ctx.AI("content.summarize", fl.M{"text": "Fluidian"}); err == nil {
			ctx.State["summary"] = result["title"]
		}
	})
	app.On("fail_ai", func(ctx *fl.Ctx, ev fl.Event) {
		if _, err := ctx.AI("content.summarize", nil); err != nil {
			ctx.Toast("AI unavailable: "+err.Error(), "warning")
		}
	})
	app.On("go", func(ctx *fl.Ctx, ev fl.Event) { ctx.Navigate(ev.Payload.(fl.M)["route"].(string)) })
	app.On("boom", func(ctx *fl.Ctx, ev fl.Event) { panic("boom") })
	app.Action("add_item", "Add an item to the list", fl.M{"title": "string title"}, func(ctx *fl.Ctx, ev fl.Event) {
		ctx.State["last"] = ev.Payload.(fl.M)["title"]
	})

	app.Run()
}
