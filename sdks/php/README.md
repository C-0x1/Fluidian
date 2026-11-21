# Fluidian for PHP

Build AI-native interfaces from PHP. This SDK implements version 1 of the Fluidian wire protocol, has no dependencies, and passes the shared conformance suite.

| | |
| --- | --- |
| Language level | PHP 8.1+ |
| Verified with | PHP 8.3 |
| Dependencies | none |
| Component factories | 123, generated from the registry |

## Install

```php
require '/path/to/fluidian/sdks/php/src/Fluidian.php';
```

A `composer.json` is provided for use as a path repository.

## Quickstart

`examples/quickstart.php`

```php
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
```

Run it from the repository root:

```bash
./fluidian run -- php sdks/php/examples/quickstart.php
```

Then open the printed URL. Without an API key the kernel answers from the offline Reflex engine; export `OPENAI_API_KEY` to use a model.

## Notes for PHP

`$ctx->state` is an array. `$ctx->ai()` returns an array and throws `Fluidian\AIError`.

## Move to or from PHP

An application written with any Fluidian SDK can be rewritten for this one, and the other way round. The converter builds and runs the result and compares it with the source, route by route.

```bash
./fluidian convert app.py --to php          # from another language to PHP
./fluidian convert my-php-app/ --to all     # from a PHP project to the other thirteen
```

See [Converting between languages](../../docs/convert.md).

## Verify

```bash
./fluidian test --sdk php
```

This builds the conformance app and the quickstart, drives both through scripted sessions and compares every message with the reference transcript. It then scaffolds a project with `fluidian new`, converts a six-route application into PHP, and checks that both build and serve what they should.

## More

- [SDK guide](../../docs/sdks.md) — the concepts shared by all SDKs
- [Portable logic](../../docs/portable-logic.md) — behaviour that is the same in every language
- [Cross-platform](../../docs/cross-platform.md) — one scene on the web, iOS, Android and desktop
- [Component reference](../../docs/reference/components.md)
- [Capability reference](../../docs/reference/capabilities.md)
- [Wire protocol](../../docs/protocol.md)
