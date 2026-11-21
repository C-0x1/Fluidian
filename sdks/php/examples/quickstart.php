<?php
// Quickstart: a counter, an AI-assisted notes field and an AI summary.
//
//   fluidian run -- php sdks/php/examples/quickstart.php
declare(strict_types=1);

require __DIR__ . '/../src/Fluidian.php';

use Fluidian\AIError;
use Fluidian\App;
use Fluidian\UI;

$app = new App('Quickstart');

$app->view(function ($ctx) {
    $page = UI::page(
        'Quickstart',
        UI::text('Count: ' . ($ctx->state['count'] ?? 0))->id('count'),
        UI::button('Add one')->id('add')->on('click', 'increment'),
        UI::textArea('notes')->prop('label', 'Notes')->id('notes')->ai('input.ghost')->on('change', 'set_notes'),
        UI::button('Summarise')->id('summarise')->on('click', 'summarise'),
    );
    if (isset($ctx->state['summary'])) {
        $page->add(UI::callout((string) $ctx->state['summary'])->id('summary'));
    }
    return $page;
});

$app->on('increment', function ($ctx, $event) { $ctx->state['count'] = ($ctx->state['count'] ?? 0) + 1; });
$app->on('set_notes', function ($ctx, $event) { $ctx->state['notes'] = $event->value; });
$app->on('summarise', function ($ctx, $event) {
    try {
        $ctx->state['summary'] = $ctx->ai('content.summarize', ['text' => $ctx->state['notes'] ?? ''])['title'];
    } catch (AIError $e) {
        $ctx->toast('Could not summarise: ' . $e->getMessage(), 'warning');
    }
});
$app->action('reset', 'Reset the counter to zero', [], function ($ctx, $event) { $ctx->state['count'] = 0; });

$app->run();
