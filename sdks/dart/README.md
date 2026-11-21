# Fluidian for Dart

Build AI-native interfaces from Dart. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | Dart 3 |
| Verified with | Dart 3.14 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```yaml
# pubspec.yaml
dependencies:
  fluidian:
    path: /path/to/fluidian/sdks/dart
```

## Quickstart

`example/quickstart.dart`

```dart
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- dart run sdks/dart/example/quickstart.dart
import '../lib/fluidian.dart';

void main() {
  final app = App('Quickstart');

  app.view((ctx) {
    final page = UI.page('Quickstart', [
      UI.text('Count: ${ctx.state['count'] ?? 0}').id('count'),
      UI.button('Add one').id('add').on('click', 'increment'),
      UI.textArea('notes').prop('label', 'Notes').id('notes').ai('input.ghost').on('change', 'set_notes'),
      UI.button('Summarise').id('summarise').on('click', 'summarise'),
    ]);
    if (ctx.state.containsKey('summary')) page.add(UI.callout('${ctx.state['summary']}').id('summary'));
    return page;
  });

  app.on('increment', (ctx, event) => ctx.state['count'] = ((ctx.state['count'] as int?) ?? 0) + 1);
  app.on('set_notes', (ctx, event) => ctx.state['notes'] = event.value);
  app.on('summarise', (ctx, event) {
    try {
      ctx.state['summary'] = ctx.ai('content.summarize', {'text': ctx.state['notes'] ?? ''})['title'];
    } on AIError catch (error) {
      ctx.toast('Could not summarise: ${error.message}', 'warning');
    }
  });
  app.action('reset', 'Reset the counter to zero', {}, (ctx, event) => ctx.state['count'] = 0);

  app.run();
}
```

Run it from the repository root:

```bash
./fluidian run -- dart run sdks/dart/example/quickstart.dart
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for Dart

`ctx.state` is a `Map<String, Object?>`. `ctx.ai()` is synchronous and throws `AIError`.

## Move to or from Dart

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to dart          # from another language to Dart
./fluidian convert my-dart-app/ --to all     # from a Dart project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk dart
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into Dart, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
