"use strict";
/**
 * Fluidian SDK for JavaScript (Node.js 14+, no dependencies).
 *
 *   const { App, ui } = require("fluidian");
 *   const app = new App("Counter");
 *   app.view((ctx) => ui.page("Counter",
 *     ui.text(`Count: ${ctx.state.count || 0}`),
 *     ui.button("Add one").on("click", "increment")));
 *   app.on("increment", (ctx) => { ctx.state.count = (ctx.state.count || 0) + 1; });
 *   app.run();
 *
 * Run it with `fluidian run -- node app.js`.
 */
const fs = require("fs");
const { Node } = require("./node.js");
const { ui } = require("./ui.js");

const VERSION = "1.2.0";
const PROTOCOL = 1;

class AIError extends Error {}

/** Blocking line reader over a file descriptor, so `ctx.ai()` can be synchronous. */
class LineReader {
  constructor(fd) {
    this.fd = fd;
    this.buffer = Buffer.alloc(0);
    this.eof = false;
  }

  read() {
    for (;;) {
      const newline = this.buffer.indexOf(10);
      if (newline >= 0) {
        const line = this.buffer.subarray(0, newline).toString("utf8");
        this.buffer = this.buffer.subarray(newline + 1);
        return line;
      }
      if (this.eof) {
        if (!this.buffer.length) return null;
        const rest = this.buffer.toString("utf8");
        this.buffer = Buffer.alloc(0);
        return rest;
      }
      const chunk = Buffer.alloc(65536);
      let count = 0;
      try {
        count = fs.readSync(this.fd, chunk, 0, chunk.length, null);
      } catch (err) {
        if (err.code === "EAGAIN") {
          Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
          continue;
        }
        if (err.code !== "EOF") throw err;
      }
      if (count === 0) this.eof = true;
      else this.buffer = Buffer.concat([this.buffer, chunk.subarray(0, count)]);
    }
  }
}

function writeLine(text) {
  const data = Buffer.from(text + "\n", "utf8");
  let offset = 0;
  while (offset < data.length) {
    try {
      offset += fs.writeSync(1, data, offset);
    } catch (err) {
      if (err.code !== "EAGAIN") throw err;
      Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 5);
    }
  }
}

/** Per-session context: state, navigation, notifications and AI. */
class Ctx {
  constructor(app, sid, session) {
    this._app = app;
    this._session = session;
    this.sid = sid;
    this.state = session.state;
  }

  get route() { return this._session.route; }
  get locale() { return this._session.locale; }

  toast(text, tone = "info") {
    this._app._send({ t: "toast", sid: this.sid, text, tone });
  }

  navigate(route) {
    this._session.route = route;
    this._app._send({ t: "navigate", sid: this.sid, route });
  }

  /** Invoke a capability and wait for its result. Throws AIError on failure. */
  ai(capability, input = {}) {
    return this._app._ai(this.sid, capability, input);
  }
}

class App {
  constructor(name, meta = {}) {
    this.name = name;
    this.meta = meta;
    this._view = null;
    this._handlers = new Map();
    this._actions = [];
    this._sessions = new Map();
    this._backlog = [];
    this._rid = 0;
    this._reader = new LineReader(0);
  }

  /** Register the function that renders a session's scene. */
  view(fn) { this._view = fn; return this; }

  /** Register a handler for a named action. */
  on(action, fn) { this._handlers.set(action, fn); return this; }

  /** Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`. */
  action(name, description, params, fn) {
    this._actions.push({ name, description, params: params || {} });
    return this.on(name, fn);
  }

  _send(message) { writeLine(JSON.stringify(message)); }

  _read() {
    for (;;) {
      const line = this._reader.read();
      if (line === null) return null;
      if (!line.trim()) continue;
      try {
        const message = JSON.parse(line);
        if (message && typeof message === "object") return message;
      } catch (err) { /* ignore malformed lines */ }
    }
  }

  _ai(sid, capability, input) {
    const rid = "r" + ++this._rid;
    this._send({ t: "ai.invoke", rid, sid, capability, input });
    for (;;) {
      const message = this._read();
      if (message === null) throw new AIError("engine disconnected");
      if (message.t === "ai.result" && message.rid === rid) {
        if (message.ok) return message.data || {};
        throw new AIError(String(message.error || "capability failed"));
      }
      this._backlog.push(message);
    }
  }

  _render(sid) {
    const session = this._sessions.get(sid);
    if (!session || !this._view) return;
    this._send({ t: "scene", sid, root: this._view(new Ctx(this, sid, session)).toJSON() });
  }

  _handle(message) {
    const sid = String(message.sid || "");
    switch (message.t) {
      case "open":
        this._sessions.set(sid, { state: {}, route: message.route || "/", locale: message.locale || "en-US" });
        this._render(sid);
        break;
      case "route":
        if (this._sessions.has(sid)) {
          this._sessions.get(sid).route = message.route || "/";
          this._render(sid);
        }
        break;
      case "event": {
        const session = this._sessions.get(sid);
        const handler = this._handlers.get(message.name);
        if (!session) this._send({ t: "log", level: "warn", message: `event for unknown session ${sid}` });
        else if (!handler) this._send({ t: "log", level: "warn", message: `no handler for action ${message.name}` });
        else {
          const event = { name: message.name, target: message.target ?? null, value: message.value ?? null, form: message.form || {}, payload: message.payload ?? null };
          try {
            handler(new Ctx(this, sid, session), event);
          } catch (err) {
            this._send({ t: "error", sid, message: `${err.name}: ${err.message}` });
            break;
          }
          this._render(sid);
        }
        break;
      }
      case "close":
        this._sessions.delete(sid);
        break;
      case "shutdown":
        return false;
      default:
        break;
    }
    return true;
  }

  /** Serve the wire protocol on stdin/stdout until the engine shuts the app down. */
  run() {
    this._send({ t: "ready", protocol: PROTOCOL, sdk: "javascript", sdkVersion: VERSION, app: { name: this.name, meta: this.meta }, actions: this._actions });
    for (;;) {
      const message = this._backlog.length ? this._backlog.shift() : this._read();
      if (message === null || !this._handle(message)) break;
    }
  }
}

module.exports = { App, Ctx, Node, AIError, ui, VERSION };
