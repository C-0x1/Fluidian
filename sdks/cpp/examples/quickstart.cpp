// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   g++ -std=c++17 -Iinclude examples/quickstart.cpp -o quickstart && fluidian run -- ./quickstart
#include <fluidian/fluidian.hpp>

using namespace fluidian;

int main() {
  App app("Quickstart");

  app.view([](Ctx& ctx) {
    Node page = ui::page("Quickstart", {
      ui::text("Count: " + std::to_string(ctx.state.get("count").as_int())).id("count"),
      ui::button("Add one").id("add").on("click", "increment"),
      ui::text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
      ui::button("Summarise").id("summarise").on("click", "summarise"),
    });
    if (ctx.state.has("summary")) page.add(ui::callout(ctx.state.get("summary").str()).id("summary"));
    return page;
  });

  app.on("increment", [](Ctx& ctx, const Event&) { ctx.state.set("count", ctx.state.get("count").as_int() + 1); });
  app.on("set_notes", [](Ctx& ctx, const Event& ev) { ctx.state.set("notes", ev.value); });
  app.on("summarise", [](Ctx& ctx, const Event&) {
    try {
      Json result = ctx.ai("content.summarize", Json::object({{"text", ctx.state.get("notes").as_string()}}));
      ctx.state.set("summary", result.get("title"));
    } catch (const AIError& error) {
      ctx.toast(std::string("Could not summarise: ") + error.what(), "warning");
    }
  });
  app.action("reset", "Reset the counter to zero", Json::object(),
             [](Ctx& ctx, const Event&) { ctx.state.set("count", 0); });

  app.run();
  return 0;
}
