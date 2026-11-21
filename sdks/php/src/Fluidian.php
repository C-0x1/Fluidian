<?php
/**
 * Fluidian SDK for PHP 8.0+ (no dependencies).
 *
 *   $app = new Fluidian\App('Counter');
 *   $app->view(fn($ctx) => Fluidian\UI::page('Counter',
 *       Fluidian\UI::text('Count: ' . ($ctx->state['count'] ?? 0)),
 *       Fluidian\UI::button('Add one')->on('click', 'increment')));
 *   $app->on('increment', function ($ctx, $event) { $ctx->state['count'] = ($ctx->state['count'] ?? 0) + 1; });
 *   $app->run();
 *
 * Run it with `fluidian run -- php app.php`.
 */

declare(strict_types=1);

namespace Fluidian;

const VERSION = '1.2.0';
const PROTOCOL = 1;

/** Thrown by Ctx::ai() when a capability cannot be fulfilled. */
class AIError extends \RuntimeException
{
}

/** One element of a scene. Every method returns the node so calls can be chained. */
final class Node implements \JsonSerializable
{
    private ?string $id = null;
    private array $props = [];
    private array $children = [];
    private array $on = [];
    private array $ai = [];

    public function __construct(public readonly string $type)
    {
    }

    /** Set a property. Values may be any JSON-compatible data. */
    public function prop(string $key, mixed $value): self
    {
        $this->props[$key] = $value;
        return $this;
    }

    /** Give the node a stable identity (used for events, focus and AI targeting). */
    public function id(string $value): self
    {
        $this->id = $value;
        return $this;
    }

    /** Bind a component event to a named action, optionally with a payload. */
    public function on(string $event, string $action, mixed ...$payload): self
    {
        $binding = ['action' => $action];
        if (count($payload) > 0) {
            $binding['payload'] = $payload[0];
        }
        $this->on[$event] = $binding;
        return $this;
    }

    /** Attach an AI capability to this node. */
    public function ai(string $capability, array|\stdClass|null $options = null): self
    {
        $this->ai[] = ['capability' => $capability, 'options' => empty((array) $options) ? new \stdClass() : $options];
        return $this;
    }

    /** Append child nodes; null entries are skipped. */
    public function add(?Node ...$children): self
    {
        foreach ($children as $child) {
            if ($child !== null) {
                $this->children[] = $child;
            }
        }
        return $this;
    }

    public function jsonSerialize(): array
    {
        $out = ['type' => $this->type, 'props' => $this->props === [] ? new \stdClass() : $this->props];
        if ($this->id !== null) {
            $out['id'] = $this->id;
        }
        if ($this->children !== []) {
            $out['children'] = $this->children;
        }
        if ($this->on !== []) {
            $out['on'] = $this->on;
        }
        if ($this->ai !== []) {
            $out['ai'] = $this->ai;
        }
        return $out;
    }
}

/** An interaction delivered to a handler. */
final class Event
{
    public function __construct(
        public readonly string $name,
        public readonly ?string $target,
        public readonly mixed $value,
        public readonly array $form,
        public readonly mixed $payload,
    ) {
    }
}

/** @internal */
final class Session
{
    public array $state = [];

    public function __construct(public string $route, public string $locale)
    {
    }
}

/** Per-session context: state, navigation, notifications and AI. */
final class Ctx
{
    /** @var array<string, mixed> Session state; assign to it directly. */
    public array $state;

    public function __construct(private App $app, public readonly string $sid, private Session $session)
    {
        $this->state = &$session->state;
    }

    public function route(): string
    {
        return $this->session->route;
    }

    public function locale(): string
    {
        return $this->session->locale;
    }

    public function toast(string $text, string $tone = 'info'): void
    {
        $this->app->send(['t' => 'toast', 'sid' => $this->sid, 'text' => $text, 'tone' => $tone]);
    }

    public function navigate(string $route): void
    {
        $this->session->route = $route;
        $this->app->send(['t' => 'navigate', 'sid' => $this->sid, 'route' => $route]);
    }

    /** Invoke a capability and wait for its result. Throws AIError on failure. */
    public function ai(string $capability, array $input = []): array
    {
        return $this->app->invoke($this->sid, $capability, $input);
    }
}

final class App
{
    /** @var callable|null */
    private $view = null;
    private array $handlers = [];
    private array $actions = [];
    /** @var array<string, Session> */
    private array $sessions = [];
    private array $backlog = [];
    private int $rid = 0;

    public function __construct(public readonly string $name, public readonly array $meta = [])
    {
    }

    /** Register the function that renders a session's scene. */
    public function view(callable $fn): self
    {
        $this->view = $fn;
        return $this;
    }

    /** Register a handler for a named action. */
    public function on(string $action, callable $fn): self
    {
        $this->handlers[$action] = $fn;
        return $this;
    }

    /** Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in $event->payload. */
    public function action(string $name, string $description, array $params, callable $fn): self
    {
        $this->actions[] = ['name' => $name, 'description' => $description, 'params' => $params === [] ? new \stdClass() : $params];
        return $this->on($name, $fn);
    }

    /** @internal */
    public function send(array $message): void
    {
        fwrite(STDOUT, json_encode($message, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION) . "\n");
        fflush(STDOUT);
    }

    private function read(): ?array
    {
        while (($line = fgets(STDIN)) !== false) {
            $line = trim($line);
            if ($line === '') {
                continue;
            }
            $message = json_decode($line, true);
            if (is_array($message)) {
                return $message;
            }
        }
        return null;
    }

    /** @internal */
    public function invoke(string $sid, string $capability, array $input): array
    {
        $rid = 'r' . ++$this->rid;
        $this->send(['t' => 'ai.invoke', 'rid' => $rid, 'sid' => $sid, 'capability' => $capability, 'input' => $input === [] ? new \stdClass() : $input]);
        while (true) {
            $message = $this->read();
            if ($message === null) {
                throw new AIError('engine disconnected');
            }
            if (($message['t'] ?? '') === 'ai.result' && ($message['rid'] ?? '') === $rid) {
                if (!empty($message['ok'])) {
                    return $message['data'] ?? [];
                }
                throw new AIError((string) ($message['error'] ?? 'capability failed'));
            }
            $this->backlog[] = $message;
        }
    }

    private function render(string $sid): void
    {
        if (!isset($this->sessions[$sid]) || $this->view === null) {
            return;
        }
        $root = ($this->view)(new Ctx($this, $sid, $this->sessions[$sid]));
        $this->send(['t' => 'scene', 'sid' => $sid, 'root' => $root]);
    }

    private function handle(array $message): bool
    {
        $sid = (string) ($message['sid'] ?? '');
        switch ($message['t'] ?? '') {
            case 'open':
                $this->sessions[$sid] = new Session($message['route'] ?? '/', $message['locale'] ?? 'en-US');
                $this->render($sid);
                break;
            case 'route':
                if (isset($this->sessions[$sid])) {
                    $this->sessions[$sid]->route = $message['route'] ?? '/';
                    $this->render($sid);
                }
                break;
            case 'event':
                $name = (string) ($message['name'] ?? '');
                if (!isset($this->sessions[$sid])) {
                    $this->send(['t' => 'log', 'level' => 'warn', 'message' => "event for unknown session $sid"]);
                } elseif (!isset($this->handlers[$name])) {
                    $this->send(['t' => 'log', 'level' => 'warn', 'message' => "no handler for action $name"]);
                } else {
                    $event = new Event($name, $message['target'] ?? null, $message['value'] ?? null, $message['form'] ?? [], $message['payload'] ?? null);
                    try {
                        ($this->handlers[$name])(new Ctx($this, $sid, $this->sessions[$sid]), $event);
                    } catch (\Throwable $e) {
                        $this->send(['t' => 'error', 'sid' => $sid, 'message' => get_class($e) . ': ' . $e->getMessage()]);
                        break;
                    }
                    $this->render($sid);
                }
                break;
            case 'close':
                unset($this->sessions[$sid]);
                break;
            case 'shutdown':
                return false;
        }
        return true;
    }

    /** Serve the wire protocol on stdin/stdout until the engine shuts the app down. */
    public function run(): void
    {
        $this->send(['t' => 'ready', 'protocol' => PROTOCOL, 'sdk' => 'php', 'sdkVersion' => VERSION,
            'app' => ['name' => $this->name, 'meta' => $this->meta === [] ? new \stdClass() : $this->meta], 'actions' => $this->actions]);
        while (true) {
            $message = $this->backlog !== [] ? array_shift($this->backlog) : $this->read();
            if ($message === null || !$this->handle($message)) {
                break;
            }
        }
    }
}

require_once __DIR__ . '/UI.php';
