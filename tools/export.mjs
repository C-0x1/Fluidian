#!/usr/bin/env node
// Render a scene to a single self-contained HTML document.
//
//   node tools/export.mjs scene.json out.html
//   cat scene.json | node tools/export.mjs - out.html
//
// The scene should be normalised (the CLI does this before calling the script).
// The output has no JavaScript: it is the server-rendered markup plus the
// framework stylesheet, suitable for email previews, documentation and snapshots.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { renderScene } from "../runtime/static.js";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const [input, output, scheme] = process.argv.slice(2);
if (!input || !output) {
  console.error("usage: node tools/export.mjs <scene.json | -> <out.html> [light|dark]");
  process.exit(2);
}

let data;
try {
  data = JSON.parse(readFileSync(input === "-" ? 0 : resolve(input), "utf8"));
} catch (err) {
  console.error(`Could not read the scene: ${err.message}`);
  process.exit(1);
}
const scene = data && typeof data.type === "string" ? data : data && typeof data === "object" ? data["/"] || Object.values(data)[0] : null;
if (!scene || typeof scene.type !== "string") {
  console.error("The file does not contain a scene (an object with a \"type\").");
  process.exit(1);
}

const escape = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const css = ["tokens.css", "themes.css", "fluidian.css", "skin.css", "blocks.css", "platform.css"]
  .map((file) => readFileSync(join(root, "runtime", file), "utf8"))
  .join("\n")
  .replace(/@font-face\s*{[^}]*}/g, "")
  .replace(/@import[^;]+;/g, "");
const title = (scene.props && scene.props.title) || "Fluidian";
const html = `<!doctype html>
<html lang="en"${scheme === "dark" ? ' data-scheme="dark"' : ""}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="Fluidian">
<title>${escape(title)}</title>
<style>
${css}
</style>
</head>
<body>
<div id="fl-root" class="fl-app">${renderScene(scene)}</div>
</body>
</html>
`;
writeFileSync(resolve(output), html);
console.log(`Wrote ${output} (${(Buffer.byteLength(html) / 1024).toFixed(1)} KB)`);
