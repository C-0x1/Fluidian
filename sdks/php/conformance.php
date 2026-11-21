<?php
// Conformance application: exercises every SDK feature against the shared transcript.
declare(strict_types=1);

require __DIR__ . '/src/Fluidian.php';
require __DIR__ . '/conformance_scene.php';

use Fluidian\AIError;
use Fluidian\App;
use Fluidian\UI;

$app = new App('Conformance');

$app->view(function ($ctx) {
    $page = UI::page(
        'Conformance',
        UI::text('Count: ' . ($ctx->state['count'] ?? 0))->id('count'),
        UI::text('Hello, ' . ($ctx->state['name'] ?? 'world') . '!')->id('greeting'),
        UI::text('Route: ' . $ctx->route())->id('route'),
    )->id('root');
    if (array_key_exists('summary', $ctx->state)) {
        $page->add(UI::text('Summary: ' . $ctx->state['summary'])->id('summary'));
    }
    if (array_key_exists('last', $ctx->state)) {
        $page->add(UI::text('Last: ' . $ctx->state['last'])->id('last'));
    }
    $page->add(UI::button('Increment')->id('inc')->on('click', 'increment'));
    $page->add(conformance_scene());
    return $page;
});

$app->on('increment', function ($ctx, $event) { $ctx->state['count'] = ($ctx->state['count'] ?? 0) + 1; });
$app->on('set_name', function ($ctx, $event) { $ctx->state['name'] = $event->value; });
$app->on('submit', function ($ctx, $event) {
    $f = $event->form;
    $ctx->toast("Saved {$f['email']} ({$f['plan']} × {$f['seats']})", 'success');
});
$app->on('ask_ai', function ($ctx, $event) { $ctx->state['summary'] = $ctx->ai('content.summarize', ['text' => 'Fluidian'])['title']; });
$app->on('fail_ai', function ($ctx, $event) {
    try {
        $ctx->ai('content.summarize');
    } catch (AIError $e) {
        $ctx->toast('AI unavailable: ' . $e->getMessage(), 'warning');
    }
});
$app->on('go', function ($ctx, $event) { $ctx->navigate($event->payload['route']); });
$app->on('boom', function ($ctx, $event) { throw new \RuntimeException('boom'); });
$app->action('add_item', 'Add an item to the list', ['title' => 'string title'], function ($ctx, $event) { $ctx->state['last'] = $event->payload['title']; });

$app->run();
