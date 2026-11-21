import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
export const readJson = (...parts) => JSON.parse(readFileSync(join(ROOT, ...parts), "utf8"));

/** The reference scene from the conformance transcript: one normalised instance of every component. */
export function referenceScene() {
  return readJson("spec", "conformance", "golden.json").find((m) => m.t === "scene").root;
}

export function walk(node, visit) {
  visit(node);
  for (const child of node.children || []) walk(child, visit);
}

export function node(type, props = {}, children = [], extra = {}) {
  return Object.assign({ type, id: extra.id || "n-" + type.toLowerCase(), props, children, on: {}, ai: [] }, extra);
}
