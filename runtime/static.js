// Fluidian runtime — server-side rendering entry (Node.js). Used by `fluidian export` and the runtime tests.
import { renderToString } from "./core.js";
import { renderNode } from "./components.js";
import "./ai.js";
import "./blocks.js";
import "./viz.js";
import { createStore } from "./logic.js";

export function staticContext(extra) {
  const ui = new Map();
  return Object.assign({
    local: createStore(), catalog: null, values: new Map(), route: "/", live: false, locale: "en-US",
    state: (id, init) => { if (!ui.has(id)) ui.set(id, Object.assign({}, init)); return ui.get(id); },
    aiState: () => ({ results: {}, busy: {}, sig: {} }), fieldEvents: () => ({}), slots: () => null, emit: () => false,
    set() {}, press() {}, rerender() {}, navigate() {}, toast() {}, setValue() {}, event() {},
  }, extra);
}

/** Render a normalised scene to an HTML string. */
export function renderScene(scene, extra) {
  return renderToString(renderNode(scene, staticContext(extra)));
}
