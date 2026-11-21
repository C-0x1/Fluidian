export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

const MISSING = Symbol("missing");

export interface NodeJson {
  type: string;
  props: { [key: string]: Json };
  id?: string;
  children?: NodeJson[];
  on?: { [event: string]: { action: string; payload?: Json } };
  ai?: { capability: string; options: { [key: string]: Json } }[];
}

/** One element of a scene. Every method returns the node so calls can be chained. */
export class Node {
  private _id: string | null = null;
  private _props: { [key: string]: Json } = {};
  private _children: Node[] = [];
  private _on: { [event: string]: { action: string; payload?: Json } } = {};
  private _ai: { capability: string; options: { [key: string]: Json } }[] = [];

  constructor(public readonly type: string) {}

  /** Set a property. Values may be any JSON-compatible data. */
  prop(key: string, value: Json | undefined): this {
    this._props[key] = value === undefined ? null : value;
    return this;
  }

  /** Give the node a stable identity (used for events, focus and AI targeting). */
  id(value: string): this {
    this._id = value;
    return this;
  }

  /** Bind a component event to a named action, optionally with a payload. */
  on(event: string, action: string, payload: Json | typeof MISSING = MISSING): this {
    const binding: { action: string; payload?: Json } = { action };
    if (payload !== MISSING) binding.payload = payload as Json;
    this._on[event] = binding;
    return this;
  }

  /** Attach an AI capability to this node. */
  ai(capability: string, options?: { [key: string]: Json }): this {
    this._ai.push({ capability, options: options || {} });
    return this;
  }

  /** Append child nodes; null and undefined entries are skipped. */
  add(...children: (Node | null | undefined)[]): this {
    for (const child of children) if (child) this._children.push(child);
    return this;
  }

  toJSON(): NodeJson {
    const out: NodeJson = { type: this.type, props: this._props };
    if (this._id !== null) out.id = this._id;
    if (this._children.length) out.children = this._children.map((c) => c.toJSON());
    if (Object.keys(this._on).length) out.on = this._on;
    if (this._ai.length) out.ai = this._ai;
    return out;
  }
}
