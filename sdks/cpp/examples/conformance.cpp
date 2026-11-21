// Conformance application: exercises every SDK feature against the shared transcript.
#include <fluidian/fluidian.hpp>

#include "conformance_scene.hpp"

using namespace fluidian;

int main() {
  App app("Conformance");

  app.view([](Ctx& ctx) {
    Node page = ui::page("Conformance", {
      ui::text("Count: " + std::to_string(ctx.state.get("count").as_int())).id("count"),
      ui::text("Hello, " + ctx.state.get("name").as_string("world") + "!").id("greeting"),
      ui::text("Route: " + ctx.route()).id("route"),
    }).id("root");
    if (ctx.state.has("summary")) page.add(ui::text("Summary: " + ctx.state.get("summary").str()).id("summary"));
    if (ctx.state.has("last")) page.add(ui::text("Last: " + ctx.state.get("last").str()).id("last"));
    page.add(ui::button("Increment").id("inc").on("click", "increment"));
    page.add(conformance_scene());
    return page;
  });

  app.on("increment", [](Ctx& ctx, const Event&) { ctx.state.set("count", ctx.state.get("count").as_int() + 1); });
  app.on("set_name", [](Ctx& ctx, const Event& ev) { ctx.state.set("name", ev.value); });
  app.on("submit", [](Ctx& ctx, const Event& ev) {
    ctx.toast("Saved " + ev.form.get("email").str() + " (" + ev.form.get("plan").str() + " × " + ev.form.get("seats").str() + ")", "success");
  });
  app.on("ask_ai", [](Ctx& ctx, const Event&) {
    ctx.state.set("summary", ctx.ai("content.summarize", Json::object({{"text", "Fluidian"}})).get("title"));
  });
  app.on("fail_ai", [](Ctx& ctx, const Event&) {
    try {
      ctx.ai("content.summarize");
    } catch (const AIError& error) {
      ctx.toast(std::string("AI unavailable: ") + error.what(), "warning");
    }
  });
  app.on("go", [](Ctx& ctx, const Event& ev) { ctx.navigate(ev.payload.get("route").str()); });
  app.on("boom", [](Ctx&, const Event&) { throw std::runtime_error("boom"); });
  app.action("add_item", "Add an item to the list", Json::object({{"title", "string title"}}),
             [](Ctx& ctx, const Event& ev) { ctx.state.set("last", ev.payload.get("title")); });

  app.run();
  return 0;
}
