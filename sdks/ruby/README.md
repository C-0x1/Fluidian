# Fluidian for Ruby

Build AI-native interfaces from Ruby. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Ruby 3.0+ |
| Verified with | Ruby 3.3 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

Inside a checkout the CLI sets `RUBYLIB` for the app process. Elsewhere, build the gem:

```bash
cd sdks/ruby && gem build fluidian.gemspec && gem install fluidian-1.2.0.gem
```

## Quickstart

`examples/quickstart.rb`

```ruby
# frozen_string_literal: true

# Quickstart: a counter, an AI-assisted notes field and an AI summary.
#
#   fluidian run -- ruby -Isdks/ruby/lib sdks/ruby/examples/quickstart.rb
require "fluidian"

UI = Fluidian::UI
app = Fluidian::App.new("Quickstart")

app.view do |ctx|
  page = UI.page(
    "Quickstart",
    UI.text("Count: #{ctx.state.fetch('count', 0)}").id("count"),
    UI.button("Add one").id("add").on("click", "increment"),
    UI.text_area("notes").prop("label", "Notes").id("notes").ai("input.ghost").on("change", "set_notes"),
    UI.button("Summarise").id("summarise").on("click", "summarise")
  )
  page.add(UI.callout(ctx.state["summary"].to_s).id("summary")) if ctx.state.key?("summary")
  page
end

app.on("increment") { |ctx, _event| ctx.state["count"] = ctx.state.fetch("count", 0) + 1 }
app.on("set_notes") { |ctx, event| ctx.state["notes"] = event.value }
app.on("summarise") do |ctx, _event|
  ctx.state["summary"] = ctx.ai("content.summarize", { "text" => ctx.state.fetch("notes", "") })["title"]
rescue Fluidian::AIError => e
  ctx.toast("Could not summarise: #{e.message}", "warning")
end
app.action("reset", "Reset the counter to zero", {}) { |ctx, _event| ctx.state["count"] = 0 }

app.run
```

Run it from the repository root:

```bash
./fluidian run -- ruby -Isdks/ruby/lib sdks/ruby/examples/quickstart.rb
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Ruby

Handlers are blocks. `ctx.state` is a `Hash` with string keys. `ctx.ai` raises `Fluidian::AIError`.

## Move to or from Ruby

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to ruby          # from another language to Ruby
./fluidian convert my-ruby-app/ --to all     # from a Ruby project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk ruby
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Ruby, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
