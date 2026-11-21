/**
 * Fluidian SDK for TypeScript (no dependencies; compiles with plain `tsc`).
 *
 *   import { App, ui } from "fluidian";
 *   const app = new App("Counter");
 *   app.view((ctx) => ui.page("Counter",
 *     ui.text(`Count: ${ctx.state.count ?? 0}`),
 *     ui.button("Add one").on("click", "increment")));
 *   app.on("increment", (ctx) => { ctx.state.count = ((ctx.state.count as number) ?? 0) + 1; });
 *   app.run();
 */
import { Json, Node } from "./node";
import { ui } from "./ui";

declare const require: (name: string) => any;
declare const Buffer: any;

const fs = require("fs");

export const VERSION = "1.2.0";
const PROTOCOL = 1;

export { Node, Json, ui };
export type State = { [key: string]: any };
export interface Event { name: string; target: string | null; value: any; form: { [key: string]: any }; payload: any; }
export interface ActionSpec { name: string; description: string; params: { [name: string]: string }; }
export type Handler = (ctx: Ctx, event: Event) => void;
interface Session { state: State; route: string; locale: string; }
type Message = { [key: string]: any };

export class AIError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AIError";
    Object.setPrototypeOf(this, AIError.prototype);
  }
}

function pause(ms: number): void {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

/** Blocking line reader over a file descriptor, so `ctx.ai()` can be synchronous. */
class LineReader {
  private buffer: any = Buffer.alloc(0);
  private eof = false;
  constructor(private readonly fd: number) {}

  read(): string | null {
    for (;;) {
      const newline: number = this.buffer.indexOf(10);
      if (newline >= 0) {
        const line: string = this.buffer.subarray(0, newline).toString("utf8");
        this.buffer = this.buffer.subarray(newline + 1);
        return line;
      }
      if (this.eof) {
        if (!this.buffer.length) return null;
        const rest: string = this.buffer.toString("utf8");
        this.buffer = Buffer.alloc(0);
        return rest;
      }
      const chunk = Buffer.alloc(65536);
      let count = 0;
      try {
        count = fs.readSync(this.fd, chunk, 0, chunk.length, null);
      } catch (err) {
        const code = (err as { code?: string }).code;
        if (code === "EAGAIN") { pause(10); continue; }
        if (code !== "EOF") throw err;
      }
      if (count === 0) this.eof = true;
      else this.buffer = Buffer.concat([this.buffer, chunk.subarray(0, count)]);
    }
  }
}

function writeLine(text: string): void {
  const data = Buffer.from(text + "\n", "utf8");
  let offset = 0;
  while (offset < data.length) {
    try {
      offset += fs.writeSync(1, data, offset);
    } catch (err) {
      if ((err as { code?: string }).code !== "EAGAIN") throw err;
      pause(5);
    }
  }
}

/** Per-session context: state, navigation, notifications and AI. */
export class Ctx {
  readonly state: State;
  constructor(private readonly app: App, readonly sid: string, private readonly session: Session) {
    this.state = session.state;
  }

  get route(): string { return this.session.route; }
  get locale(): string { return this.session.locale; }

  toast(text: string, tone: string = "info"): void {
    this.app.send({ t: "toast", sid: this.sid, text, tone });
  }

  navigate(route: string): void {
    this.session.route = route;
    this.app.send({ t: "navigate", sid: this.sid, route });
  }

  /** Invoke a capability and wait for its result. Throws AIError on failure. */
  ai(capability: string, input: { [key: string]: Json } = {}): { [key: string]: any } {
    return this.app.invoke(this.sid, capability, input);
  }
}

export class App {
  private viewFn: ((ctx: Ctx) => Node) | null = null;
  private handlers = new Map<string, Handler>();
  private actions: ActionSpec[] = [];
  private sessions = new Map<string, Session>();
  private backlog: Message[] = [];
  private rid = 0;
  private reader = new LineReader(0);

  constructor(readonly name: string, readonly meta: { [key: string]: Json } = {}) {}

  /** Register the function that renders a session's scene. */
  view(fn: (ctx: Ctx) => Node): this { this.viewFn = fn; return this; }

  /** Register a handler for a named action. */
  on(action: string, fn: Handler): this { this.handlers.set(action, fn); return this; }

  /** Register a handler that the Intent Bar and Copilot may invoke; arguments arrive in `event.payload`. */
  action(name: string, description: string, params: { [name: string]: string }, fn: Handler): this {
    this.actions.push({ name, description, params: params || {} });
    return this.on(name, fn);
  }

  /** @internal */
  send(message: Message): void { writeLine(JSON.stringify(message)); }

  private read(): Message | null {
    for (;;) {
      const line = this.reader.read();
      if (line === null) return null;
      if (!line.trim()) continue;
      try {
        const message = JSON.parse(line);
        if (message && typeof message === "object") return message as Message;
      } catch (err) { /* ignore malformed lines */ }
    }
  }

  /** @internal */
  invoke(sid: string, capability: string, input: { [key: string]: Json }): { [key: string]: any } {
    const rid = "r" + ++this.rid;
    this.send({ t: "ai.invoke", rid, sid, capability, input });
    for (;;) {
      const message = this.read();
      if (message === null) throw new AIError("engine disconnected");
      if (message.t === "ai.result" && message.rid === rid) {
        if (message.ok) return message.data || {};
        throw new AIError(String(message.error || "capability failed"));
      }
      this.backlog.push(message);
    }
  }

  private render(sid: string): void {
    const session = this.sessions.get(sid);
    if (!session || !this.viewFn) return;
    this.send({ t: "scene", sid, root: this.viewFn(new Ctx(this, sid, session)).toJSON() });
  }

  private handle(message: Message): boolean {
    const sid = String(message.sid || "");
    if (message.t === "open") {
      this.sessions.set(sid, { state: {}, route: message.route || "/", locale: message.locale || "en-US" });
      this.render(sid);
    } else if (message.t === "route") {
      const session = this.sessions.get(sid);
      if (session) { session.route = message.route || "/"; this.render(sid); }
    } else if (message.t === "event") {
      const session = this.sessions.get(sid);
      const handler = this.handlers.get(message.name);
      if (!session) this.send({ t: "log", level: "warn", message: `event for unknown session ${sid}` });
      else if (!handler) this.send({ t: "log", level: "warn", message: `no handler for action ${message.name}` });
      else {
        const event: Event = { name: message.name, target: message.target ?? null, value: message.value ?? null, form: message.form || {}, payload: message.payload ?? null };
        try {
          handler(new Ctx(this, sid, session), event);
        } catch (err) {
          const e = err as Error;
          this.send({ t: "error", sid, message: `${e.name}: ${e.message}` });
          return true;
        }
        this.render(sid);
      }
    } else if (message.t === "close") {
      this.sessions.delete(sid);
    } else if (message.t === "shutdown") {
      return false;
    }
    return true;
  }

  /** Serve the wire protocol on stdin/stdout until the engine shuts the app down. */
  run(): void {
    this.send({ t: "ready", protocol: PROTOCOL, sdk: "typescript", sdkVersion: VERSION, app: { name: this.name, meta: this.meta }, actions: this.actions });
    for (;;) {
      const message = this.backlog.length ? (this.backlog.shift() as Message) : this.read();
      if (message === null || !this.handle(message)) break;
    }
  }
}
