"use strict";

const MISSING = Symbol("missing");

/** One element of a scene. Every method returns the node so calls can be chained. */
class Node {
  constructor(type) {
    this.type = type;
    this._id = null;
    this._props = {};
    this._children = [];
    this._on = {};
    this._ai = [];
  }

  /** Set a property. Values may be any JSON-compatible data. */
  prop(key, value) {
    this._props[key] = value === undefined ? null : value;
    return this;
  }

  /** Give the node a stable identity (used for events, focus and AI targeting). */
  id(value) {
    this._id = value;
    return this;
  }

  /** Bind a component event to a named action, optionally with a payload. */
  on(event, action, payload = MISSING) {
    const binding = { action };
    if (payload !== MISSING) binding.payload = payload;
    this._on[event] = binding;
    return this;
  }

  /** Attach an AI capability to this node. */
  ai(capability, options) {
    this._ai.push({ capability, options: options || {} });
    return this;
  }

  /** Append child nodes; null and undefined entries are skipped. */
  add(...children) {
    for (const child of children.flat()) if (child) this._children.push(child);
    return this;
  }

  toJSON() {
    const out = { type: this.type, props: this._props };
    if (this._id !== null) out.id = this._id;
    if (this._children.length) out.children = this._children.map((c) => c.toJSON());
    if (Object.keys(this._on).length) out.on = this._on;
    if (this._ai.length) out.ai = this._ai;
    return out;
  }
}

module.exports = { Node };
