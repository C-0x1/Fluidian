/// Fluidian SDK for Dart (no dependencies).
///
/// ```dart
/// import 'package:fluidian/fluidian.dart';
///
/// void main() {
///   final app = App('Counter');
///   app.view((ctx) => UI.page('Counter', [
///         UI.text('Count: ${ctx.state['count'] ?? 0}'),
///         UI.button('Add one').on('click', 'increment'),
///       ]));
///   app.on('increment', (ctx, event) => ctx.state['count'] = ((ctx.state['count'] as int?) ?? 0) + 1);
///   app.run();
/// }
/// ```
///
/// Run it with `fluidian run -- dart run app.dart`.
library fluidian;

import 'dart:collection';
import 'dart:convert';
import 'dart:io';

part 'ui.dart';

const String version = '1.2.0';
const int _protocol = 1;
const Object _missing = Object();

/// Thrown by [Ctx.ai] when a capability cannot be fulfilled.
class AIError implements Exception {
  final String message;
  AIError(this.message);
  @override
  String toString() => message;
}

/// One element of a scene. Every method returns the node so calls can be chained.
class Node {
  final String type;
  String? _id;
  final Map<String, Object?> _props = {};
  final List<Node> _children = [];
  final Map<String, Object?> _on = {};
  final List<Object?> _ai = [];

  Node(this.type);

  /// Set a property. Values may be any JSON-compatible data.
  Node prop(String key, Object? value) {
    _props[key] = value;
    return this;
  }

  /// Give the node a stable identity (used for events, focus and AI targeting).
  Node id(String value) {
    _id = value;
    return this;
  }

  /// Bind a component event to a named action, optionally with a payload.
  Node on(String event, String action, [Object? payload = _missing]) {
    final binding = <String, Object?>{'action': action};
    if (!identical(payload, _missing)) binding['payload'] = payload;
    _on[event] = binding;
    return this;
  }

  /// Attach an AI capability to this node.
  Node ai(String capability, [Map<String, Object?>? options]) {
    _ai.add(<String, Object?>{'capability': capability, 'options': options ?? <String, Object?>{}});
    return this;
  }

  /// Append one child node; `null` is skipped.
  Node add(Node? child) {
    if (child != null) _children.add(child);
    return this;
  }

  /// Append child nodes; `null` entries are skipped.
  Node addAll(Iterable<Node?> children) {
    for (final child in children) {
      if (child != null) _children.add(child);
    }
    return this;
  }

  Map<String, Object?> toJson() {
    final out = <String, Object?>{'type': type, 'props': _props};
    if (_id != null) out['id'] = _id;
    if (_children.isNotEmpty) out['children'] = _children.map((c) => c.toJson()).toList();
    if (_on.isNotEmpty) out['on'] = _on;
    if (_ai.isNotEmpty) out['ai'] = _ai;
    return out;
  }
}

/// An interaction delivered to a handler.
class Event {
  final String name;
  final String? target;
  final Object? value;
  final Map<String, Object?> form;
  final Object? payload;
  Event(this.name, this.target, this.value, this.form, this.payload);
}

class _Session {
  final Map<String, Object?> state = {};
  String route;
  String locale;
  _Session(this.route, this.locale);
}

/// Per-session context: state, navigation, notifications and AI.
class Ctx {
  final App _app;
  final _Session _session;
  final String sid;
  Ctx._(this._app, this.sid, this._session);

  Map<String, Object?> get state => _session.state;
  String get route => _session.route;
  String get locale => _session.locale;

  void toast(String text, [String tone = 'info']) => _app._send({'t': 'toast', 'sid': sid, 'text': text, 'tone': tone});

  void navigate(String route) {
    _session.route = route;
    _app._send({'t': 'navigate', 'sid': sid, 'route': route});
  }

  /// Invoke a capability and wait for its result. Throws [AIError] on failure.
  Map<String, Object?> ai(String capability, [Map<String, Object?> input = const {}]) => _app._invoke(sid, capability, input);
}

typedef Handler = void Function(Ctx ctx, Event event);

class App {
  final String name;
  final Map<String, Object?> meta;
  Node Function(Ctx ctx)? _view;
  final Map<String, Handler> _handlers = {};
  final List<Object?> _actions = [];
  final Map<String, _Session> _sessions = {};
  final Queue<Map<String, Object?>> _backlog = Queue();
  int _rid = 0;

  App(this.name, [this.meta = const {}]);

  /// Register the function that renders a session's scene.
  void view(Node Function(Ctx ctx) fn) => _view = fn;

  /// Register a handler for a named action.
  void on(String action, Handler fn) => _handlers[action] = fn;

  /// Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`.
  void action(String name, String description, Map<String, String> params, Handler fn) {
    _actions.add({'name': name, 'description': description, 'params': params});
    on(name, fn);
  }

  void _send(Map<String, Object?> message) {
    stdout.write('${jsonEncode(message)}\n');
  }

  Map<String, Object?>? _read() {
    while (true) {
      final line = stdin.readLineSync(encoding: utf8);
      if (line == null) return null;
      if (line.trim().isEmpty) continue;
      try {
        final message = jsonDecode(line);
        if (message is Map<String, Object?>) return message;
      } on FormatException {
        continue;
      }
    }
  }

  Map<String, Object?> _invoke(String sid, String capability, Map<String, Object?> input) {
    final rid = 'r${++_rid}';
    _send({'t': 'ai.invoke', 'rid': rid, 'sid': sid, 'capability': capability, 'input': input});
    while (true) {
      final message = _read();
      if (message == null) throw AIError('engine disconnected');
      if (message['t'] == 'ai.result' && message['rid'] == rid) {
        if (message['ok'] == true) return (message['data'] as Map<String, Object?>?) ?? <String, Object?>{};
        throw AIError('${message['error'] ?? 'capability failed'}');
      }
      _backlog.add(message);
    }
  }

  void _render(String sid) {
    final session = _sessions[sid];
    final view = _view;
    if (session == null || view == null) return;
    _send({'t': 'scene', 'sid': sid, 'root': view(Ctx._(this, sid, session)).toJson()});
  }

  bool _handle(Map<String, Object?> message) {
    final sid = '${message['sid'] ?? ''}';
    switch (message['t']) {
      case 'open':
        _sessions[sid] = _Session('${message['route'] ?? '/'}', '${message['locale'] ?? 'en-US'}');
        _render(sid);
        break;
      case 'route':
        final session = _sessions[sid];
        if (session != null) {
          session.route = '${message['route'] ?? '/'}';
          _render(sid);
        }
        break;
      case 'event':
        final name = '${message['name'] ?? ''}';
        final session = _sessions[sid];
        final handler = _handlers[name];
        if (session == null) {
          _send({'t': 'log', 'level': 'warn', 'message': 'event for unknown session $sid'});
        } else if (handler == null) {
          _send({'t': 'log', 'level': 'warn', 'message': 'no handler for action $name'});
        } else {
          final event = Event(name, message['target'] as String?, message['value'],
              (message['form'] as Map<String, Object?>?) ?? <String, Object?>{}, message['payload']);
          try {
            handler(Ctx._(this, sid, session), event);
          } catch (error) {
            _send({'t': 'error', 'sid': sid, 'message': '$error'});
            break;
          }
          _render(sid);
        }
        break;
      case 'close':
        _sessions.remove(sid);
        break;
      case 'shutdown':
        return false;
    }
    return true;
  }

  /// Serve the wire protocol on stdin/stdout until the engine shuts the app down.
  void run() {
    _send({'t': 'ready', 'protocol': _protocol, 'sdk': 'dart', 'sdkVersion': version, 'app': {'name': name, 'meta': meta}, 'actions': _actions});
    while (true) {
      final message = _backlog.isNotEmpty ? _backlog.removeFirst() : _read();
      if (message == null || !_handle(message)) break;
    }
  }
}
