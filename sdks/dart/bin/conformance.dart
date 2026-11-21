// Conformance application: exercises every SDK feature against the shared transcript.
import '../lib/fluidian.dart';
import 'conformance_scene.dart';

void main() {
  final app = App('Conformance');

  app.view((ctx) {
    final page = UI.page('Conformance', [
      UI.text('Count: ${ctx.state['count'] ?? 0}').id('count'),
      UI.text('Hello, ${ctx.state['name'] ?? 'world'}!').id('greeting'),
      UI.text('Route: ${ctx.route}').id('route'),
    ]).id('root');
    if (ctx.state.containsKey('summary')) page.add(UI.text('Summary: ${ctx.state['summary']}').id('summary'));
    if (ctx.state.containsKey('last')) page.add(UI.text('Last: ${ctx.state['last']}').id('last'));
    page.add(UI.button('Increment').id('inc').on('click', 'increment'));
    page.add(conformanceScene());
    return page;
  });

  app.on('increment', (ctx, event) => ctx.state['count'] = ((ctx.state['count'] as int?) ?? 0) + 1);
  app.on('set_name', (ctx, event) => ctx.state['name'] = event.value);
  app.on('submit', (ctx, event) {
    final form = event.form;
    ctx.toast('Saved ${form['email']} (${form['plan']} × ${form['seats']})', 'success');
  });
  app.on('ask_ai', (ctx, event) => ctx.state['summary'] = ctx.ai('content.summarize', {'text': 'Fluidian'})['title']);
  app.on('fail_ai', (ctx, event) {
    try {
      ctx.ai('content.summarize');
    } on AIError catch (error) {
      ctx.toast('AI unavailable: ${error.message}', 'warning');
    }
  });
  app.on('go', (ctx, event) => ctx.navigate('${(event.payload as Map<String, Object?>)['route']}'));
  app.on('boom', (ctx, event) => throw StateError('boom'));
  app.action('add_item', 'Add an item to the list', {'title': 'string title'},
      (ctx, event) => ctx.state['last'] = (event.payload as Map<String, Object?>)['title']);

  app.run();
}
