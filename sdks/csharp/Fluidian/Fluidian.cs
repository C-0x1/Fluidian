// Fluidian SDK for .NET (no dependencies beyond the base class library).
//
//   using Fluidian;
//   var app = new App("Counter");
//   app.View(ctx => UI.Page("Counter",
//       UI.Text($"Count: {ctx.State.GetValueOrDefault("count", 0L)}"),
//       UI.Button("Add one").On("click", "increment")));
//   app.On("increment", (ctx, ev) => ctx.State["count"] = (long)ctx.State.GetValueOrDefault("count", 0L)! + 1);
//   app.Run();
//
// Run it with `fluidian run -- dotnet run`.
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;

namespace Fluidian;

/// <summary>Raised by <see cref="Ctx.Ai"/> when a capability cannot be fulfilled.</summary>
public sealed class AIException : Exception
{
    public AIException(string message) : base(message) { }
}

/// <summary>Helpers for writing JSON literals.</summary>
public static class J
{
    /// <summary>Build a JSON object from alternating keys and values.</summary>
    public static Dictionary<string, object?> Obj(params object?[] pairs)
    {
        var map = new Dictionary<string, object?>();
        for (var i = 0; i + 1 < pairs.Length; i += 2) map[Convert.ToString(pairs[i]) ?? ""] = pairs[i + 1];
        return map;
    }

    /// <summary>Build a JSON array.</summary>
    public static List<object?> Arr(params object?[]? items) => items is null ? new List<object?> { null } : new List<object?>(items);
}

/// <summary>One element of a scene. Every method returns the node so calls can be chained.</summary>
public sealed class Node
{
    private readonly string _type;
    private string? _id;
    private readonly Dictionary<string, object?> _props = new();
    private readonly List<Node> _children = new();
    private readonly Dictionary<string, object?> _on = new();
    private readonly List<object?> _ai = new();

    public Node(string type) => _type = type;

    /// <summary>Set a property. Values may be any JSON-compatible data.</summary>
    public Node Prop(string key, object? value) { _props[key] = value; return this; }

    /// <summary>Give the node a stable identity (used for events, focus and AI targeting).</summary>
    public Node Id(string value) { _id = value; return this; }

    /// <summary>Bind a component event to a named action.</summary>
    public Node On(string @event, string action) { _on[@event] = J.Obj("action", action); return this; }

    /// <summary>Bind a component event to a named action with a payload.</summary>
    public Node On(string @event, string action, object? payload) { _on[@event] = J.Obj("action", action, "payload", payload); return this; }

    /// <summary>Attach an AI capability to this node.</summary>
    public Node Ai(string capability, Dictionary<string, object?>? options = null)
    {
        _ai.Add(J.Obj("capability", capability, "options", options ?? new Dictionary<string, object?>()));
        return this;
    }

    /// <summary>Append child nodes; null entries are skipped.</summary>
    public Node Add(params Node?[] children)
    {
        foreach (var child in children) if (child is not null) _children.Add(child);
        return this;
    }

    public Dictionary<string, object?> ToJson()
    {
        var o = new Dictionary<string, object?> { ["type"] = _type, ["props"] = _props };
        if (_id is not null) o["id"] = _id;
        if (_children.Count > 0) o["children"] = _children.ConvertAll(c => (object?)c.ToJson());
        if (_on.Count > 0) o["on"] = _on;
        if (_ai.Count > 0) o["ai"] = _ai;
        return o;
    }
}

/// <summary>An interaction delivered to a handler.</summary>
public sealed record Event(string Name, string? Target, object? Value, Dictionary<string, object?> Form, object? Payload);

internal sealed class Session
{
    public readonly Dictionary<string, object?> State = new();
    public string Route = "/";
    public string Locale = "en-US";
}

/// <summary>Per-session context: state, navigation, notifications and AI.</summary>
public sealed class Ctx
{
    private readonly App _app;
    private readonly Session _session;
    public string Sid { get; }
    public Dictionary<string, object?> State => _session.State;
    public string Route => _session.Route;
    public string Locale => _session.Locale;

    internal Ctx(App app, string sid, Session session) { _app = app; Sid = sid; _session = session; }

    public void Toast(string text, string tone = "info") => _app.Send(J.Obj("t", "toast", "sid", Sid, "text", text, "tone", tone));

    public void Navigate(string route)
    {
        _session.Route = route;
        _app.Send(J.Obj("t", "navigate", "sid", Sid, "route", route));
    }

    /// <summary>Invoke a capability and wait for its result. Throws <see cref="AIException"/> on failure.</summary>
    public Dictionary<string, object?> Ai(string capability, Dictionary<string, object?>? input = null) =>
        _app.Invoke(Sid, capability, input ?? new Dictionary<string, object?>());
}

public sealed class App
{
    public const string Version = "1.2.0";
    private const int Protocol = 1;
    private static readonly JsonSerializerOptions Options = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };

    public string Name { get; }
    public Dictionary<string, object?> Meta { get; } = new();
    private Func<Ctx, Node>? _view;
    private readonly Dictionary<string, Action<Ctx, Event>> _handlers = new();
    private readonly List<object?> _actions = new();
    private readonly Dictionary<string, Session> _sessions = new();
    private readonly Queue<Dictionary<string, object?>> _backlog = new();
    private int _rid;
    private readonly StreamReader _in = new(Console.OpenStandardInput(), new UTF8Encoding(false));
    private readonly StreamWriter _out = new(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true, NewLine = "\n" };

    public App(string name) => Name = name;

    /// <summary>Register the function that renders a session's scene.</summary>
    public App View(Func<Ctx, Node> fn) { _view = fn; return this; }

    /// <summary>Register a handler for a named action.</summary>
    public App On(string action, Action<Ctx, Event> fn) { _handlers[action] = fn; return this; }

    /// <summary>Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in Event.Payload.</summary>
    public App Action(string name, string description, Dictionary<string, object?>? parameters, Action<Ctx, Event> fn)
    {
        _actions.Add(J.Obj("name", name, "description", description, "params", parameters ?? new Dictionary<string, object?>()));
        return On(name, fn);
    }

    internal void Send(Dictionary<string, object?> message) => _out.WriteLine(JsonSerializer.Serialize(message, Options));

    private static object? Convert(JsonElement e) => e.ValueKind switch
    {
        JsonValueKind.Object => e.EnumerateObject().ToDictionary(p => p.Name, p => Convert(p.Value)),
        JsonValueKind.Array => e.EnumerateArray().Select(Convert).ToList(),
        JsonValueKind.String => e.GetString(),
        JsonValueKind.Number => e.TryGetInt64(out var n) ? n : e.GetDouble(),
        JsonValueKind.True => true,
        JsonValueKind.False => false,
        _ => null,
    };

    private Dictionary<string, object?>? Read()
    {
        while (true)
        {
            var line = _in.ReadLine();
            if (line is null) return null;
            if (string.IsNullOrWhiteSpace(line)) continue;
            try
            {
                using var doc = JsonDocument.Parse(line);
                if (Convert(doc.RootElement) is Dictionary<string, object?> message) return message;
            }
            catch (JsonException) { }
        }
    }

    internal Dictionary<string, object?> Invoke(string sid, string capability, Dictionary<string, object?> input)
    {
        var rid = "r" + ++_rid;
        Send(J.Obj("t", "ai.invoke", "rid", rid, "sid", sid, "capability", capability, "input", input));
        while (true)
        {
            var message = Read() ?? throw new AIException("engine disconnected");
            if (message.GetValueOrDefault("t") as string == "ai.result" && message.GetValueOrDefault("rid") as string == rid)
            {
                if (message.GetValueOrDefault("ok") is true) return message.GetValueOrDefault("data") as Dictionary<string, object?> ?? new();
                throw new AIException(message.GetValueOrDefault("error")?.ToString() ?? "capability failed");
            }
            _backlog.Enqueue(message);
        }
    }

    private void Render(string sid)
    {
        if (_view is null || !_sessions.TryGetValue(sid, out var session)) return;
        Send(J.Obj("t", "scene", "sid", sid, "root", _view(new Ctx(this, sid, session)).ToJson()));
    }

    private bool Handle(Dictionary<string, object?> message)
    {
        var sid = message.GetValueOrDefault("sid")?.ToString() ?? "";
        switch (message.GetValueOrDefault("t") as string)
        {
            case "open":
                _sessions[sid] = new Session { Route = message.GetValueOrDefault("route") as string ?? "/", Locale = message.GetValueOrDefault("locale") as string ?? "en-US" };
                Render(sid);
                break;
            case "route":
                if (_sessions.TryGetValue(sid, out var routed))
                {
                    routed.Route = message.GetValueOrDefault("route") as string ?? "/";
                    Render(sid);
                }
                break;
            case "event":
                var name = message.GetValueOrDefault("name") as string ?? "";
                if (!_sessions.TryGetValue(sid, out var session)) Send(J.Obj("t", "log", "level", "warn", "message", $"event for unknown session {sid}"));
                else if (!_handlers.TryGetValue(name, out var handler)) Send(J.Obj("t", "log", "level", "warn", "message", $"no handler for action {name}"));
                else
                {
                    var ev = new Event(name, message.GetValueOrDefault("target") as string, message.GetValueOrDefault("value"),
                        message.GetValueOrDefault("form") as Dictionary<string, object?> ?? new(), message.GetValueOrDefault("payload"));
                    try { handler(new Ctx(this, sid, session), ev); }
                    catch (Exception error)
                    {
                        Send(J.Obj("t", "error", "sid", sid, "message", $"{error.GetType().Name}: {error.Message}"));
                        break;
                    }
                    Render(sid);
                }
                break;
            case "close":
                _sessions.Remove(sid);
                break;
            case "shutdown":
                return false;
        }
        return true;
    }

    /// <summary>Serve the wire protocol on stdin/stdout until the engine shuts the app down.</summary>
    public void Run()
    {
        Send(J.Obj("t", "ready", "protocol", Protocol, "sdk", "csharp", "sdkVersion", Version, "app", J.Obj("name", Name, "meta", Meta), "actions", _actions));
        while (true)
        {
            var message = _backlog.Count > 0 ? _backlog.Dequeue() : Read();
            if (message is null || !Handle(message)) break;
        }
    }
}
