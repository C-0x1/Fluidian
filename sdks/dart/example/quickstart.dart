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
