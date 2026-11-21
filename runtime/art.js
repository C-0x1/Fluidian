// Fluidian runtime — procedural artwork.
// `Art` draws product shots, landscapes and abstract backdrops as inline SVG, so an
// interface can look finished before a single photograph exists. Every drawing is a
// pure function of its props: the same kind, hue and seed always give the same picture.
import { h } from "./core.js";
import { ICONS } from "./icons.js";

/** OKLCH → sRGB hex, clamped to gamut. */
export function oklch(L, C, H) {
  const a = C * Math.cos((H * Math.PI) / 180), b = C * Math.sin((H * Math.PI) / 180);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3, m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3, s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const lin = [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s];
  return "#" + lin.map((v) => {
    const g = v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(Math.max(v, 0), 1 / 2.4) - 0.055;
    return Math.round(Math.max(0, Math.min(1, g)) * 255).toString(16).padStart(2, "0");
  }).join("");
}
export function hashOf(text) { let x = 2166136261; for (const ch of String(text)) x = Math.imul(x ^ ch.charCodeAt(0), 16777619); return x >>> 0; }
export function rng(seed) { let t = (seed >>> 0) + 0x6d2b79f5; return () => { t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

const n1 = (v) => Number(v.toFixed(1));
const F = (c) => "fill:" + c;
const K = (c, w = 2) => `fill:none;stroke:${c};stroke-width:${w};stroke-linecap:round;stroke-linejoin:round`;
const rect = (x, y, w, hh, rx, style, extra) => h("rect", Object.assign({ x: n1(x), y: n1(y), width: n1(Math.max(0, w)), height: n1(Math.max(0, hh)), rx: n1(rx || 0), style }, extra));
const circ = (cx, cy, r, style, extra) => h("circle", Object.assign({ cx: n1(cx), cy: n1(cy), r: n1(Math.max(0, r)), style }, extra));
const ell = (cx, cy, rx, ry, style, extra) => h("ellipse", Object.assign({ cx: n1(cx), cy: n1(cy), rx: n1(rx), ry: n1(ry), style }, extra));
const path = (d, style, extra) => h("path", Object.assign({ d, style }, extra));
const stops = (list) => list.map(([o, c, a]) => h("stop", { offset: o, style: `stop-color:${c}` + (a === undefined ? "" : `;stop-opacity:${a}`) }));
const lin = (id, list, x1 = 0, y1 = 0, x2 = 0, y2 = 1) => h("linearGradient", { id, x1, y1, x2, y2 }, stops(list));
const rad = (id, list, cx = 0.5, cy = 0.5, r = 0.5) => h("radialGradient", { id, cx, cy, r }, stops(list));
const blur = (id, d) => h("filter", { id, x: "-50%", y: "-50%", width: "200%", height: "200%" }, h("feGaussianBlur", { stdDeviation: d }));
const url = (id) => `url(#${id})`;
const poly = (pts) => pts.map((p, i) => (i ? "L" : "M") + n1(p[0]) + " " + n1(p[1])).join(" ") + " Z";
function smooth(pts) { // Catmull-Rom through the points, as cubic Béziers
  let d = `M${n1(pts[0][0])} ${n1(pts[0][1])}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    d += ` C${n1(p1[0] + (p2[0] - p0[0]) / 6)} ${n1(p1[1] + (p2[1] - p0[1]) / 6)} ${n1(p2[0] - (p3[0] - p1[0]) / 6)} ${n1(p2[1] - (p3[1] - p1[1]) / 6)} ${n1(p2[0])} ${n1(p2[1])}`;
  }
  return d;
}

/** Colours for a drawing: derived from a hue when one is given, otherwise bound to the active theme. */
function palette(p, dark) {
  if (p.hue === undefined || p.hue === null || p.hue === "") {
    const mix = (v, pct, to) => `color-mix(in oklab, var(${v}) ${pct}%, ${to})`;
    return { themed: true, bgA: dark ? mix("--fl-surface-2", 80, "#000") : "var(--fl-surface-2)", bgB: dark ? mix("--fl-bg", 70, "#000") : "var(--fl-surface-3)",
      a: "var(--fl-ai-a)", aL: mix("--fl-ai-a", 55, "#fff"), aD: mix("--fl-ai-a", 72, "#000"), aX: mix("--fl-ai-a", 45, "#000"),
      b: "var(--fl-ai-b)", bL: mix("--fl-ai-b", 55, "#fff"), bD: mix("--fl-ai-b", 72, "#000"), c: "var(--fl-ai-c)", cL: mix("--fl-ai-c", 55, "#fff"),
      ink: "var(--fl-text)", paper: "var(--fl-surface)", line: "var(--fl-border-strong)", sky1: mix("--fl-ai-b", 30, "var(--fl-surface)"), sky2: mix("--fl-ai-a", 22, "var(--fl-surface)") };
  }
  const h1 = Number(p.hue) || 0, h2 = p.hue2 === undefined || p.hue2 === null ? (h1 + 48) % 360 : Number(p.hue2), h3 = (h2 + 48) % 360;
  return { themed: false, bgA: dark ? oklch(0.27, 0.05, h1) : oklch(0.965, 0.028, h1), bgB: dark ? oklch(0.15, 0.04, h1) : oklch(0.895, 0.06, h1),
    a: oklch(0.7, 0.16, h1), aL: oklch(0.87, 0.085, h1), aD: oklch(0.5, 0.16, h1), aX: oklch(0.33, 0.11, h1),
    b: oklch(0.74, 0.15, h2), bL: oklch(0.89, 0.08, h2), bD: oklch(0.54, 0.15, h2), c: oklch(0.8, 0.13, h3), cL: oklch(0.92, 0.07, h3),
    ink: oklch(0.24, 0.035, h1), paper: "#ffffff", line: oklch(0.8, 0.04, h1), sky1: oklch(0.9, 0.07, h2), sky2: oklch(0.82, 0.11, h1) };
}

// A lit backdrop with a soft floor shadow, shared by the product drawings.
function studio(W, H, P, id, dark, shadow = 0.3) {
  const u = Math.min(W, H);
  return {
    defs: [lin(id + "bg", [[0, P.bgA], [1, P.bgB]]), rad(id + "hl", [[0, "#fff", dark ? 0.16 : 0.7], [1, "#fff", 0]], 0.28, 0.12, 0.75), blur(id + "sh", u * 0.022),
      lin(id + "cy", [[0, P.aD], [0.22, P.a], [0.48, P.aL], [0.78, P.a], [1, P.aD]], 0, 0, 1, 0), lin(id + "v", [[0, P.aL], [1, P.aD]]), lin(id + "v2", [[0, P.b], [1, P.bD]]),
      lin(id + "mt", [[0, "#f4f4f5"], [0.5, "#c9cbd1"], [1, "#8d9099"]], 0, 0, 1, 0)],
    body: [rect(0, 0, W, H, 0, F(url(id + "bg"))), rect(0, 0, W, H, 0, F(url(id + "hl"))), ell(W / 2, H * 0.855, u * shadow, u * 0.034, F("rgba(0,0,0,.28)"), { filter: url(id + "sh") })],
  };
}
const gloss = (x, y, w, hh, o = 0.34) => rect(x, y, w, hh, w / 2, F("#fff"), { opacity: o });

const PRODUCTS = {
  bottle(W, H, P, id, o) {
    const u = Math.min(W, H), cx = W / 2, bw = u * 0.25, bh = u * 0.43, x = cx - bw / 2, y = H * 0.85 - bh;
    return [rect(cx - bw * 0.2, y - u * 0.2, bw * 0.4, u * 0.14, bw * 0.06, F(P.ink)), ell(cx, y - u * 0.2, bw * 0.17, u * 0.035, F(P.ink)), rect(cx - bw * 0.15, y - u * 0.065, bw * 0.3, u * 0.08, 3, F(P.aX)),
      rect(x, y, bw, bh, bw * 0.17, F(url(id + "cy"))), rect(x + bw * 0.13, y + bh * 0.3, bw * 0.74, bh * 0.44, 3, F(P.paper), { opacity: 0.9 }),
      rect(x + bw * 0.22, y + bh * 0.39, bw * 0.4, 3.2, 1.6, F(P.ink), { opacity: 0.85 }), rect(x + bw * 0.22, y + bh * 0.47, bw * 0.56, 2, 1, F(P.ink), { opacity: 0.4 }), rect(x + bw * 0.22, y + bh * 0.53, bw * 0.46, 2, 1, F(P.ink), { opacity: 0.4 }),
      gloss(x + bw * 0.09, y + bh * 0.05, bw * 0.07, bh * 0.2)];
  },
  jar(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, bw = u * 0.44, bh = u * 0.25, x = cx - bw / 2, y = H * 0.85 - bh;
    return [rect(x, y, bw, bh, bw * 0.09, F(url(id + "cy"))), rect(x - bw * 0.02, y - u * 0.085, bw * 1.04, u * 0.1, bw * 0.035, F(url(id + "mt"))), rect(x - bw * 0.02, y - u * 0.012, bw * 1.04, 2.2, 1, F("rgba(0,0,0,.2)")),
      rect(x + bw * 0.2, y + bh * 0.3, bw * 0.6, bh * 0.44, 3, F(P.paper), { opacity: 0.9 }), rect(x + bw * 0.28, y + bh * 0.42, bw * 0.3, 3, 1.5, F(P.ink), { opacity: 0.85 }), rect(x + bw * 0.28, y + bh * 0.56, bw * 0.44, 2, 1, F(P.ink), { opacity: 0.4 }),
      gloss(x + bw * 0.05, y + bh * 0.14, bw * 0.04, bh * 0.62)];
  },
  tube(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, top = H * 0.2, bot = H * 0.78, w1 = u * 0.26, w2 = u * 0.2;
    return [path(poly([[cx - w1 / 2, top], [cx + w1 / 2, top], [cx + w2 / 2, bot], [cx - w2 / 2, bot]]), F(url(id + "cy"))), rect(cx - w1 / 2, top - u * 0.03, w1, u * 0.04, 2, F(P.aX)),
      rect(cx - w2 * 0.42, bot, w2 * 0.84, u * 0.075, 4, F(P.ink)), rect(cx - w1 * 0.3, top + u * 0.14, w1 * 0.6, u * 0.2, 3, F(P.paper), { opacity: 0.9 }),
      rect(cx - w1 * 0.2, top + u * 0.19, w1 * 0.32, 3, 1.5, F(P.ink), { opacity: 0.85 }), rect(cx - w1 * 0.2, top + u * 0.25, w1 * 0.4, 2, 1, F(P.ink), { opacity: 0.4 }), gloss(cx - w1 * 0.4, top + u * 0.05, w1 * 0.06, u * 0.4, 0.3)];
  },
  can(W, H, P, id, o) {
    const u = Math.min(W, H), cx = W / 2, bw = u * 0.27, bh = u * 0.5, x = cx - bw / 2, y = H * 0.85 - bh;
    return [rect(x, y, bw, bh, bw * 0.12, F(url(id + "cy"))), ell(cx, y + 2, bw * 0.46, u * 0.022, F(url(id + "mt"))), rect(x, y + bh * 0.26, bw, bh * 0.36, 0, F(P.paper), { opacity: 0.92 }),
      path(smooth([[x, y + bh * 0.52], [x + bw * 0.3, y + bh * 0.4], [x + bw * 0.6, y + bh * 0.54], [x + bw, y + bh * 0.42]]) + ` L${n1(x + bw)} ${n1(y + bh * 0.62)} L${n1(x)} ${n1(y + bh * 0.62)} Z`, F(P.b), { opacity: 0.85 }),
      rect(x + bw * 0.14, y + bh * 0.3, bw * 0.34, 3.4, 1.7, F(P.ink), { opacity: 0.9 }), gloss(x + bw * 0.08, y + bh * 0.06, bw * 0.06, bh * 0.86, 0.3)];
  },
  candle(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, bw = u * 0.34, bh = u * 0.34, x = cx - bw / 2, y = H * 0.85 - bh;
    return [circ(cx, y - u * 0.13, u * 0.2, F(url(id + "gl"))), rect(x, y, bw, bh, bw * 0.08, F(url(id + "cy")), { opacity: 0.92 }), rect(x, y, bw, bh * 0.16, bw * 0.08, F("#fff"), { opacity: 0.35 }),
      rect(x + bw * 0.2, y + bh * 0.38, bw * 0.6, bh * 0.38, 3, F(P.paper), { opacity: 0.9 }), rect(x + bw * 0.3, y + bh * 0.5, bw * 0.3, 3, 1.5, F(P.ink), { opacity: 0.85 }), rect(x + bw * 0.3, y + bh * 0.62, bw * 0.4, 2, 1, F(P.ink), { opacity: 0.4 }),
      rect(cx - 1, y - u * 0.05, 2, u * 0.06, 1, F(P.ink)), path(`M${n1(cx)} ${n1(y - u * 0.17)} C${n1(cx + u * 0.05)} ${n1(y - u * 0.1)} ${n1(cx + u * 0.03)} ${n1(y - u * 0.04)} ${n1(cx)} ${n1(y - u * 0.04)} C${n1(cx - u * 0.03)} ${n1(y - u * 0.04)} ${n1(cx - u * 0.05)} ${n1(y - u * 0.1)} ${n1(cx)} ${n1(y - u * 0.17)} Z`, F("#ffb347")),
      ell(cx, y - u * 0.07, u * 0.012, u * 0.025, F("#fff6d8")), gloss(x + bw * 0.06, y + bh * 0.2, bw * 0.045, bh * 0.66, 0.3)];
  },
  vase(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, by = H * 0.85, t = by - u * 0.46, r = u * 0.17;
    const d = `M${n1(cx - r * 0.42)} ${n1(t)} C${n1(cx - r * 0.42)} ${n1(t + u * 0.1)} ${n1(cx - r * 1.25)} ${n1(t + u * 0.16)} ${n1(cx - r * 1.2)} ${n1(t + u * 0.3)} C${n1(cx - r * 1.15)} ${n1(by - u * 0.03)} ${n1(cx - r * 0.5)} ${n1(by)} ${n1(cx)} ${n1(by)} C${n1(cx + r * 0.5)} ${n1(by)} ${n1(cx + r * 1.15)} ${n1(by - u * 0.03)} ${n1(cx + r * 1.2)} ${n1(t + u * 0.3)} C${n1(cx + r * 1.25)} ${n1(t + u * 0.16)} ${n1(cx + r * 0.42)} ${n1(t + u * 0.1)} ${n1(cx + r * 0.42)} ${n1(t)} Z`;
    const stem = (dx, hh, lean) => [path(`M${n1(cx + dx * 0.3)} ${n1(t + 4)} Q${n1(cx + dx)} ${n1(t - hh * 0.5)} ${n1(cx + dx + lean)} ${n1(t - hh)}`, K("#4d7c57", 2.2)), ell(cx + dx + lean, t - hh, u * 0.035, u * 0.05, F(P.b), { transform: `rotate(${lean > 0 ? 24 : -24} ${n1(cx + dx + lean)} ${n1(t - hh)})` })];
    return [stem(-u * 0.05, u * 0.2, -u * 0.06), stem(u * 0.02, u * 0.27, u * 0.02), stem(u * 0.06, u * 0.17, u * 0.07), path(d, F(url(id + "cy"))), ell(cx, t, r * 0.42, u * 0.014, F(P.aX)), gloss(cx - r * 0.86, t + u * 0.2, u * 0.022, u * 0.16, 0.3)];
  },
  mug(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2 - u * 0.03, bw = u * 0.34, bh = u * 0.32, x = cx - bw / 2, y = H * 0.85 - bh;
    const steam = (dx) => path(`M${n1(cx + dx)} ${n1(y - u * 0.04)} c${n1(-u * 0.04)} ${n1(-u * 0.05)} ${n1(u * 0.04)} ${n1(-u * 0.08)} 0 ${n1(-u * 0.13)}`, K("#fff", 3), { opacity: 0.6 });
    return [path(`M${n1(x + bw - 2)} ${n1(y + bh * 0.2)} c${n1(u * 0.14)} 0 ${n1(u * 0.14)} ${n1(bh * 0.5)} 0 ${n1(bh * 0.5)}`, K(P.a, u * 0.04)), rect(x, y, bw, bh, bw * 0.12, F(url(id + "cy"))), ell(cx, y + 3, bw * 0.46, u * 0.022, F(P.aX)), ell(cx, y + 4, bw * 0.4, u * 0.014, F("#5b3a29")),
      steam(-u * 0.05), steam(u * 0.04), gloss(x + bw * 0.08, y + bh * 0.16, bw * 0.05, bh * 0.66, 0.3)];
  },
  speaker(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, bw = u * 0.36, bh = u * 0.56, x = cx - bw / 2, y = H * 0.85 - bh, cone = (cy, r) => [circ(cx, cy, r, F(P.ink)), circ(cx, cy, r * 0.8, F("#2a2d36")), circ(cx, cy, r * 0.5, F("#3a3e49")), circ(cx, cy, r * 0.2, F(url(id + "mt"))), circ(cx - r * 0.3, cy - r * 0.3, r * 0.12, F("#fff"), { opacity: 0.25 })];
    return [rect(x, y, bw, bh, bw * 0.16, F(url(id + "v"))), rect(x + bw * 0.06, y + bh * 0.035, bw * 0.88, bh * 0.93, bw * 0.12, F("rgba(0,0,0,.14)")), cone(y + bh * 0.26, bw * 0.17), cone(y + bh * 0.64, bw * 0.31), circ(cx, y + bh * 0.93, 2.4, F(P.b)), gloss(x + bw * 0.035, y + bh * 0.08, bw * 0.03, bh * 0.5, 0.35)];
  },
  headphones(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.5, r = u * 0.25, cup = (sx) => [rect(cx + sx * r - u * 0.065, cy + u * 0.02, u * 0.13, u * 0.25, u * 0.06, F(url(id + "v"))), rect(cx + sx * r + (sx < 0 ? u * 0.035 : -u * 0.075), cy + u * 0.045, u * 0.04, u * 0.2, u * 0.02, F(P.ink), { opacity: 0.85 }), gloss(cx + sx * r - u * 0.045, cy + u * 0.05, u * 0.02, u * 0.1, 0.4)];
    return [path(`M${n1(cx - r)} ${n1(cy + u * 0.06)} A${n1(r)} ${n1(r * 1.05)} 0 0 1 ${n1(cx + r)} ${n1(cy + u * 0.06)}`, K(P.ink, u * 0.05)), path(`M${n1(cx - r * 0.8)} ${n1(cy - u * 0.12)} A${n1(r)} ${n1(r * 1.05)} 0 0 1 ${n1(cx + r * 0.8)} ${n1(cy - u * 0.12)}`, K(P.aL, u * 0.016), { opacity: 0.6 }), cup(-1), cup(1)];
  },
  watch(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.48, r = u * 0.19, hand = (ang, len, w) => path(`M${n1(cx)} ${n1(cy)} L${n1(cx + Math.cos(ang) * len)} ${n1(cy + Math.sin(ang) * len)}`, K("#fff", w));
    return [rect(cx - r * 0.56, cy - r * 2.3, r * 1.12, r * 4.6, r * 0.3, F(url(id + "v"))), rect(cx - r * 0.56, cy - r * 2.3, r * 1.12, r * 4.6, r * 0.3, F("rgba(0,0,0,.2)")), rect(cx + r * 0.98, cy - r * 0.14, r * 0.14, r * 0.28, 2, F(url(id + "mt"))),
      circ(cx, cy, r * 1.06, F(url(id + "mt"))), circ(cx, cy, r * 0.93, F("#101218")), circ(cx, cy, r * 0.93, F(url(id + "fc"))), Array.from({ length: 12 }, (_, i) => { const a = (i / 12) * Math.PI * 2; return circ(cx + Math.cos(a) * r * 0.76, cy + Math.sin(a) * r * 0.76, i % 3 ? 1.3 : 2.3, F("#fff"), { opacity: i % 3 ? 0.5 : 0.95 }); }),
      hand(-2.2, r * 0.46, 3.2), hand(-0.5, r * 0.66, 2.2), path(`M${n1(cx)} ${n1(cy)} L${n1(cx + r * 0.1)} ${n1(cy + r * 0.7)}`, K(P.b, 1.3)), circ(cx, cy, 3.2, F(P.b)), path(`M${n1(cx - r * 0.7)} ${n1(cy - r * 0.5)} A${n1(r * 0.86)} ${n1(r * 0.86)} 0 0 1 ${n1(cx + r * 0.2)} ${n1(cy - r * 0.84)}`, K("#fff", 2), { opacity: 0.22 })];
  },
  phone(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, bw = u * 0.34, bh = u * 0.7, x = cx - bw / 2, y = H * 0.5 - bh / 2;
    return [rect(x, y, bw, bh, bw * 0.17, F("#15171c")), rect(x + bw * 0.035, y + bw * 0.035, bw * 0.93, bh - bw * 0.07, bw * 0.14, F(url(id + "scr"))), rect(cx - bw * 0.14, y + bw * 0.08, bw * 0.28, bw * 0.075, bw * 0.04, F("#0b0c0f")),
      rect(x + bw * 0.14, y + bh * 0.24, bw * 0.5, bw * 0.07, 3, F("#fff"), { opacity: 0.92 }), rect(x + bw * 0.14, y + bh * 0.32, bw * 0.34, bw * 0.04, 2, F("#fff"), { opacity: 0.55 }), rect(x + bw * 0.12, y + bh * 0.46, bw * 0.76, bh * 0.2, bw * 0.06, F("#fff"), { opacity: 0.18 }), rect(x + bw * 0.12, y + bh * 0.7, bw * 0.36, bh * 0.14, bw * 0.06, F("#fff"), { opacity: 0.18 }), rect(x + bw * 0.52, y + bh * 0.7, bw * 0.36, bh * 0.14, bw * 0.06, F("#fff"), { opacity: 0.28 }),
      path(`M${n1(x + bw * 0.1)} ${n1(y + bh * 0.2)} L${n1(x + bw * 0.5)} ${n1(y + bw * 0.04)} L${n1(x + bw * 0.74)} ${n1(y + bw * 0.04)} L${n1(x + bw * 0.1)} ${n1(y + bh * 0.44)} Z`, F("#fff"), { opacity: 0.07 })];
  },
  glasses(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.52, lw = u * 0.3, lh = u * 0.21, gap = u * 0.05, lens = (x) => [rect(x, cy - lh / 2, lw, lh, lh * 0.36, F(url(id + "ln"))), rect(x, cy - lh / 2, lw, lh, lh * 0.36, K(P.ink, u * 0.028)), path(`M${n1(x + lw * 0.16)} ${n1(cy + lh * 0.18)} L${n1(x + lw * 0.42)} ${n1(cy - lh * 0.28)}`, K("#fff", 3), { opacity: 0.5 }), path(`M${n1(x + lw * 0.3)} ${n1(cy + lh * 0.22)} L${n1(x + lw * 0.5)} ${n1(cy - lh * 0.14)}`, K("#fff", 1.6), { opacity: 0.4 })];
    return [path(`M${n1(cx - gap / 2 - lw)} ${n1(cy - lh * 0.2)} L${n1(cx - gap / 2 - lw - u * 0.09)} ${n1(cy - lh * 0.42)}`, K(P.ink, u * 0.026)), path(`M${n1(cx + gap / 2 + lw)} ${n1(cy - lh * 0.2)} L${n1(cx + gap / 2 + lw + u * 0.09)} ${n1(cy - lh * 0.42)}`, K(P.ink, u * 0.026)),
      lens(cx - gap / 2 - lw), lens(cx + gap / 2), path(`M${n1(cx - gap / 2)} ${n1(cy - lh * 0.12)} Q${n1(cx)} ${n1(cy - lh * 0.36)} ${n1(cx + gap / 2)} ${n1(cy - lh * 0.12)}`, K(P.ink, u * 0.024)), circ(cx + gap / 2 + lw - u * 0.03, cy - lh * 0.3, 2.2, F(P.b))];
  },
  lamp(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, by = H * 0.85, top = by - u * 0.56;
    return [path(poly([[cx - u * 0.3, by], [cx + u * 0.3, by], [cx + u * 0.15, top + u * 0.2], [cx - u * 0.15, top + u * 0.2]]), F(url(id + "gl")), { opacity: 0.5 }), rect(cx - 2.5, top + u * 0.18, 5, u * 0.36, 2, F(url(id + "mt"))), ell(cx, by - 3, u * 0.13, u * 0.022, F(P.ink)),
      path(poly([[cx - u * 0.1, top], [cx + u * 0.1, top], [cx + u * 0.19, top + u * 0.2], [cx - u * 0.19, top + u * 0.2]]), F(url(id + "v"))), ell(cx, top + u * 0.2, u * 0.19, u * 0.02, F("#fff6d8"))];
  },
  plant(W, H, P, id, o, R) {
    const u = Math.min(W, H), cx = W / 2, by = H * 0.85, pw = u * 0.3, ph = u * 0.2, top = by - ph, leaves = [];
    const greens = ["#2f7d4f", "#3f9460", "#56ab72", "#2a6e45", "#6cbf85"];
    for (let i = 0; i < 9; i++) {
      const ang = -Math.PI / 2 + (i - 4) * 0.33 + (R() - 0.5) * 0.12, len = u * (0.24 + R() * 0.14), tx = cx + Math.cos(ang) * len, ty = top + Math.sin(ang) * len, nx = -Math.sin(ang) * len * 0.22, ny = Math.cos(ang) * len * 0.22, mx = (cx + tx) / 2, my = (top + ty) / 2;
      leaves.push(path(`M${n1(cx)} ${n1(top + 4)} Q${n1(mx + nx)} ${n1(my + ny)} ${n1(tx)} ${n1(ty)} Q${n1(mx - nx)} ${n1(my - ny)} ${n1(cx)} ${n1(top + 4)} Z`, F(greens[i % greens.length])), path(`M${n1(cx)} ${n1(top + 4)} L${n1(tx)} ${n1(ty)}`, K("rgba(255,255,255,.22)", 1)));
    }
    return [leaves, path(poly([[cx - pw / 2, top], [cx + pw / 2, top], [cx + pw * 0.38, by], [cx - pw * 0.38, by]]), F(url(id + "cy"))), rect(cx - pw * 0.54, top - u * 0.03, pw * 1.08, u * 0.045, 4, F(P.a)), rect(cx - pw * 0.54, top + u * 0.012, pw * 1.08, 2, 1, F("rgba(0,0,0,.14)")), gloss(cx - pw * 0.38, top + u * 0.04, pw * 0.05, ph * 0.6, 0.3)];
  },
  fruit(W, H, P, id, o) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.52, r = u * 0.24, v = o.variant || "round";
    const shape = v === "oval" ? ell(cx, cy, r * 1.22, r * 0.86, F(url(id + "fr"))) : v === "pear" ? path(`M${n1(cx)} ${n1(cy - r * 1.25)} C${n1(cx + r * 0.5)} ${n1(cy - r * 1.25)} ${n1(cx + r * 0.5)} ${n1(cy - r * 0.4)} ${n1(cx + r * 0.9)} ${n1(cy + r * 0.2)} C${n1(cx + r * 1.3)} ${n1(cy + r * 0.9)} ${n1(cx + r * 0.6)} ${n1(cy + r * 1.3)} ${n1(cx)} ${n1(cy + r * 1.3)} C${n1(cx - r * 0.6)} ${n1(cy + r * 1.3)} ${n1(cx - r * 1.3)} ${n1(cy + r * 0.9)} ${n1(cx - r * 0.9)} ${n1(cy + r * 0.2)} C${n1(cx - r * 0.5)} ${n1(cy - r * 0.4)} ${n1(cx - r * 0.5)} ${n1(cy - r * 1.25)} ${n1(cx)} ${n1(cy - r * 1.25)} Z`, F(url(id + "fr"))) : circ(cx, cy, r, F(url(id + "fr")));
    const topY = cy - (v === "pear" ? r * 1.25 : v === "oval" ? r * 0.86 : r);
    return [shape, v === "pear" ? circ(cx, cy + r * 0.45, r * 0.42, F("#7a4a21"), { opacity: o.cut ? 1 : 0 }) : null, ell(cx - r * 0.38, cy - r * 0.42, r * 0.2, r * 0.12, F("#fff"), { opacity: 0.42, transform: `rotate(-32 ${n1(cx - r * 0.38)} ${n1(cy - r * 0.42)})` }),
      path(`M${n1(cx)} ${n1(topY + 4)} q${n1(u * 0.01)} ${n1(-u * 0.05)} ${n1(u * 0.03)} ${n1(-u * 0.07)}`, K("#5b3a29", 3)), path(`M${n1(cx + u * 0.03)} ${n1(topY - u * 0.05)} q${n1(u * 0.1)} ${n1(-u * 0.07)} ${n1(u * 0.16)} ${n1(u * 0.01)} q${n1(-u * 0.09)} ${n1(u * 0.06)} ${n1(-u * 0.16)} ${n1(-u * 0.01)} Z`, F("#3f9460"))];
  },
  box(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.52, s = u * 0.25, dy = s * 0.5;
    return [path(poly([[cx, cy - s], [cx + s, cy - s + dy], [cx, cy - s + dy * 2], [cx - s, cy - s + dy]]), F(P.aL)), path(poly([[cx - s, cy - s + dy], [cx, cy - s + dy * 2], [cx, cy + s + dy * 0.4], [cx - s, cy + s - dy * 0.6]]), F(P.a)), path(poly([[cx + s, cy - s + dy], [cx, cy - s + dy * 2], [cx, cy + s + dy * 0.4], [cx + s, cy + s - dy * 0.6]]), F(P.aD)),
      path(poly([[cx - s * 0.56, cy - s + dy * 0.44], [cx - s * 0.4, cy - s + dy * 0.36], [cx + s * 0.6, cy - s + dy * 1.36], [cx + s * 0.44, cy - s + dy * 1.44]]), F(P.paper), { opacity: 0.7 }), path(poly([[cx + s * 0.44, cy - s + dy * 1.44], [cx + s * 0.6, cy - s + dy * 1.36], [cx + s * 0.6, cy - s + dy * 2.1], [cx + s * 0.44, cy - s + dy * 2.2]]), F(P.paper), { opacity: 0.5 })];
  },
  bag(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, top = H * 0.36, by = H * 0.85, w1 = u * 0.42, w2 = u * 0.5;
    return [path(`M${n1(cx - w1 * 0.26)} ${n1(top + 4)} C${n1(cx - w1 * 0.26)} ${n1(top - u * 0.22)} ${n1(cx + w1 * 0.26)} ${n1(top - u * 0.22)} ${n1(cx + w1 * 0.26)} ${n1(top + 4)}`, K(P.aX, u * 0.022)), path(poly([[cx - w1 / 2, top], [cx + w1 / 2, top], [cx + w2 / 2, by], [cx - w2 / 2, by]]), F(url(id + "v"))),
      path(poly([[cx - w1 / 2, top], [cx + w1 / 2, top], [cx + w1 * 0.52, top + u * 0.04], [cx - w1 * 0.52, top + u * 0.04]]), F("rgba(0,0,0,.14)")), circ(cx, top + u * 0.2, u * 0.065, K("#fff", 2.4), { opacity: 0.85 }), path(`M${n1(cx - u * 0.03)} ${n1(top + u * 0.2)} l${n1(u * 0.022)} ${n1(u * 0.022)} l${n1(u * 0.04)} ${n1(-u * 0.045)}`, K("#fff", 2.4), { opacity: 0.85 })];
  },
  card(W, H, P, id, o) {
    const u = Math.min(W, H), cw = Math.min(W * 0.72, u * 1.15), ch = cw * 0.62, x = W / 2 - cw / 2, y = H / 2 - ch / 2;
    return h("g", { transform: `rotate(-8 ${n1(W / 2)} ${n1(H / 2)})` }, rect(x + 6, y + 12, cw, ch, cw * 0.06, F("rgba(0,0,0,.3)"), { filter: url(id + "sh") }), rect(x, y, cw, ch, cw * 0.06, F(url(id + "cd"))),
      circ(x + cw * 0.86, y + ch * 0.1, cw * 0.4, F("#fff"), { opacity: 0.1 }), circ(x + cw * 0.14, y + ch * 1.05, cw * 0.34, F("#fff"), { opacity: 0.08 }), rect(x + cw * 0.08, y + ch * 0.3, cw * 0.14, ch * 0.2, 4, F("#f1d38a")), rect(x + cw * 0.08, y + ch * 0.385, cw * 0.14, 1.2, 0, F("rgba(0,0,0,.25)")), rect(x + cw * 0.145, y + ch * 0.3, 1.2, ch * 0.2, 0, F("rgba(0,0,0,.25)")),
      [0, 1, 2].map((i) => path(`M${n1(x + cw * (0.27 + i * 0.035))} ${n1(y + ch * 0.33)} q${n1(cw * 0.03)} ${n1(ch * 0.07)} 0 ${n1(ch * 0.14)}`, K("#fff", 1.6), { opacity: 0.75 })),
      [0, 1, 2, 3].map((g) => [0, 1, 2, 3].map((i) => circ(x + cw * (0.1 + g * 0.2 + i * 0.034), y + ch * 0.68, g === 3 ? 0 : 2.1, F("#fff"), { opacity: 0.9 }))), h("text", { x: n1(x + cw * 0.7), y: n1(y + ch * 0.705), style: `fill:#fff;font:600 ${n1(cw * 0.055)}px var(--fl-mono, monospace);letter-spacing:.08em` }, String(o.label || "4821")),
      rect(x + cw * 0.08, y + ch * 0.82, cw * 0.3, 3.4, 1.7, F("#fff"), { opacity: 0.75 }), circ(x + cw * 0.82, y + ch * 0.82, ch * 0.09, F("#fff"), { opacity: 0.55 }), circ(x + cw * 0.89, y + ch * 0.82, ch * 0.09, F("#fff"), { opacity: 0.3 }));
  },
  dish(W, H, P, id, o, R) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.5, r = u * 0.34, bits = [], hues = ["#e85d3a", "#f2b632", "#5aa862", "#f4efe2", "#7a4a21", "#e98fa4", "#3f8f4f"];
    for (let i = 0; i < 26; i++) { const a = R() * 6.283, d = Math.sqrt(R()) * r * 0.56, s = u * (0.03 + R() * 0.045); bits.push(ell(cx + Math.cos(a) * d, cy + Math.sin(a) * d, s, s * (0.55 + R() * 0.45), F(hues[Math.floor(R() * hues.length)]), { transform: `rotate(${Math.round(R() * 180)} ${n1(cx + Math.cos(a) * d)} ${n1(cy + Math.sin(a) * d)})` })); }
    return [circ(cx + 3, cy + 8, r, F("rgba(0,0,0,.22)"), { filter: url(id + "sh") }), circ(cx, cy, r, F("#fbfaf7")), circ(cx, cy, r * 0.97, K("rgba(0,0,0,.06)", 1.5)), circ(cx, cy, r * 0.7, F(P.aL)), circ(cx, cy, r * 0.7, K("rgba(0,0,0,.08)", 2)), bits, path(`M${n1(cx - r * 0.2)} ${n1(cy - r * 0.1)} q${n1(r * 0.2)} ${n1(-r * 0.24)} ${n1(r * 0.42)} ${n1(-r * 0.04)}`, K("#3f8f4f", 3.4))];
  },
  burger(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, w = u * 0.52, x = cx - w / 2, by = H * 0.82;
    return [rect(x, by - u * 0.09, w, u * 0.09, u * 0.04, F("#d89b4a")), rect(x - 4, by - u * 0.165, w + 8, u * 0.075, u * 0.035, F("#6b3b22")), path(smooth([[x - 8, by - u * 0.17], [x + w * 0.2, by - u * 0.15], [x + w * 0.4, by - u * 0.18], [x + w * 0.6, by - u * 0.15], [x + w * 0.8, by - u * 0.18], [x + w + 8, by - u * 0.16]]) + ` L${n1(x + w + 8)} ${n1(by - u * 0.2)} L${n1(x - 8)} ${n1(by - u * 0.2)} Z`, F("#f4c53c")),
      rect(x - 2, by - u * 0.235, w + 4, u * 0.045, u * 0.02, F("#d9453a")), path(smooth([[x - 10, by - u * 0.25], [x + w * 0.16, by - u * 0.275], [x + w * 0.33, by - u * 0.245], [x + w * 0.5, by - u * 0.28], [x + w * 0.66, by - u * 0.245], [x + w * 0.84, by - u * 0.275], [x + w + 10, by - u * 0.25]]) + ` L${n1(x + w + 6)} ${n1(by - u * 0.23)} L${n1(x - 6)} ${n1(by - u * 0.23)} Z`, F("#5aa862")),
      path(`M${n1(x)} ${n1(by - u * 0.27)} C${n1(x)} ${n1(by - u * 0.52)} ${n1(x + w)} ${n1(by - u * 0.52)} ${n1(x + w)} ${n1(by - u * 0.27)} Z`, F(url(id + "bun"))), [[0.3, 0.38], [0.5, 0.43], [0.7, 0.38], [0.4, 0.33], [0.6, 0.33]].map(([px, py]) => ell(x + w * px, by - u * py, 3.4, 1.8, F("#fff3d6"))), path(`M${n1(x + w * 0.14)} ${n1(by - u * 0.33)} C${n1(x + w * 0.18)} ${n1(by - u * 0.44)} ${n1(x + w * 0.32)} ${n1(by - u * 0.47)} ${n1(x + w * 0.4)} ${n1(by - u * 0.47)}`, K("#fff", 3), { opacity: 0.35 })];
  },
  portrait(W, H, P, id) {
    const u = Math.min(W, H), cx = W / 2, cy = H * 0.42, r = u * 0.17;
    return [path(`M${n1(cx - u * 0.36)} ${n1(H)} C${n1(cx - u * 0.36)} ${n1(H * 0.68)} ${n1(cx - u * 0.14)} ${n1(cy + r * 1.25)} ${n1(cx)} ${n1(cy + r * 1.25)} C${n1(cx + u * 0.14)} ${n1(cy + r * 1.25)} ${n1(cx + u * 0.36)} ${n1(H * 0.68)} ${n1(cx + u * 0.36)} ${n1(H)} Z`, F(url(id + "v2"))), circ(cx, cy, r, F(P.cL)), path(`M${n1(cx - r)} ${n1(cy - r * 0.1)} A${n1(r)} ${n1(r)} 0 0 1 ${n1(cx + r)} ${n1(cy - r * 0.1)} C${n1(cx + r * 0.5)} ${n1(cy - r * 0.5)} ${n1(cx - r * 0.2)} ${n1(cy - r * 0.2)} ${n1(cx - r)} ${n1(cy - r * 0.1)} Z`, F(P.ink), { opacity: 0.85 })];
  },
};

const SCENES = {
  mesh(W, H, P, id, o, R) {
    const cols = [P.a, P.b, P.c, P.aL, P.b], blobs = cols.map((c, i) => circ(W * (0.12 + R() * 0.76), H * (0.1 + R() * 0.8), Math.max(W, H) * (0.22 + R() * 0.2), F(c), { opacity: 0.85, filter: url(id + "bl") }));
    return { defs: [blur(id + "bl", Math.max(W, H) * 0.09)], body: [rect(0, 0, W, H, 0, F(P.bgA)), blobs] };
  },
  orbs(W, H, P, id, o, R) {
    const u = Math.min(W, H), defs = [lin(id + "bg", [[0, P.bgA], [1, P.bgB]]), rad(id + "o0", [[0, "#fff", 0.95], [0.3, P.aL], [1, P.aD]], 0.32, 0.28, 0.75), rad(id + "o1", [[0, "#fff", 0.95], [0.3, P.bL], [1, P.bD]], 0.32, 0.28, 0.75), rad(id + "o2", [[0, "#fff", 0.95], [0.3, P.cL], [1, P.b]], 0.32, 0.28, 0.75), blur(id + "sh", u * 0.03)], body = [rect(0, 0, W, H, 0, F(url(id + "bg")))];
    const spots = [[0.3, 0.56, 0.26], [0.66, 0.4, 0.2], [0.74, 0.74, 0.11], [0.14, 0.26, 0.08], [0.5, 0.2, 0.06]];
    spots.forEach(([x, y, r], i) => { const X = W * (x + (R() - 0.5) * 0.06), Y = H * (y + (R() - 0.5) * 0.06); body.push(ell(X, Y + u * r * 1.02, u * r * 0.8, u * r * 0.12, F("rgba(0,0,0,.25)"), { filter: url(id + "sh") }), circ(X, Y, u * r, F(url(id + "o" + (i % 3))))); });
    return { defs, body };
  },
  rings(W, H, P, id) {
    const m = Math.max(W, H), cx = W * 0.72, cy = H * 0.3, body = [rect(0, 0, W, H, 0, F(url(id + "bg")))];
    for (let i = 14; i >= 1; i--) body.push(circ(cx, cy, (m * 0.09) * i, K(i % 3 === 0 ? P.b : P.a, i % 3 === 0 ? 1.6 : 1), { opacity: n1(Math.max(0.06, 0.6 - i * 0.04)) }));
    body.push(circ(cx, cy, m * 0.06, F(url(id + "core"))));
    return { defs: [lin(id + "bg", [[0, P.bgA], [1, P.bgB]]), rad(id + "core", [[0, "#fff"], [0.5, P.aL], [1, P.a]])], body };
  },
  waves(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "bg")))], cols = [P.a, P.b, P.c, P.aL];
    for (let k = 0; k < 5; k++) { const base = H * (0.34 + k * 0.14), amp = H * (0.05 + R() * 0.05), ph = R() * 6.28, pts = []; for (let i = 0; i <= 8; i++) pts.push([(W / 8) * i, base + Math.sin(ph + i * 0.9) * amp]); body.push(path(smooth(pts) + ` L${W} ${H} L0 ${H} Z`, F(cols[k % cols.length]), { opacity: n1(0.3 + k * 0.12) })); }
    return { defs: [lin(id + "bg", [[0, P.bgA], [1, P.bgB]])], body };
  },
  grid(W, H, P, id) {
    const hz = H * 0.56, body = [rect(0, 0, W, H, 0, F(url(id + "bg"))), circ(W / 2, hz, Math.min(W, H) * 0.3, F(url(id + "sun"))), rect(0, hz, W, H - hz, 0, F(url(id + "fl")))];
    for (let i = -12; i <= 12; i++) body.push(path(`M${n1(W / 2 + i * W * 0.02)} ${n1(hz)} L${n1(W / 2 + i * W * 0.2)} ${H}`, K(P.a, 1), { opacity: 0.55 }));
    for (let j = 0; j < 9; j++) { const y = hz + (H - hz) * Math.pow(j / 9, 1.9); body.push(path(`M0 ${n1(y)} L${W} ${n1(y)}`, K(P.b, 1), { opacity: n1(0.2 + j * 0.06) })); }
    body.push(rect(0, hz - 1, W, 2, 0, F(P.aL), { opacity: 0.9 }));
    return { defs: [lin(id + "bg", [[0, P.bgB], [1, P.bgA]]), lin(id + "sun", [[0, P.c], [0.6, P.b], [1, P.a]]), lin(id + "fl", [[0, P.bgB], [1, P.bgA]])], body };
  },
  dots(W, H, P, id) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "bg")))], step = Math.max(W, H) / 26, fx = W * 0.68, fy = H * 0.36, m = Math.hypot(W, H);
    for (let y = step / 2; y < H; y += step) for (let x = step / 2; x < W; x += step) { const d = Math.hypot(x - fx, y - fy) / m, r = Math.max(0.5, step * 0.42 * (1 - d * 2.1)); if (r > 0.6) body.push(circ(x, y, r, F(d < 0.2 ? P.b : P.a), { opacity: n1(Math.max(0.12, 1 - d * 2.2)) })); }
    return { defs: [lin(id + "bg", [[0, P.bgA], [1, P.bgB]])], body };
  },
  blocks(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(P.bgA))], n = W >= H ? 10 : 7, s = W / n, rows = Math.ceil(H / s), cols = [P.a, P.b, P.c, P.aL, P.bL, P.aD];
    for (let y = 0; y < rows; y++) for (let x = 0; x < n; x++) { const v = R(); if (v < 0.28) continue; body.push(rect(x * s + s * 0.07, y * s + s * 0.07, s * 0.86, s * 0.86, s * 0.2, F(cols[Math.floor(R() * cols.length)]), { opacity: n1(0.25 + v * 0.75) })); }
    return { defs: [], body };
  },
  topo(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "bg")))], cx = W * (0.3 + R() * 0.4), cy = H * (0.35 + R() * 0.3), m = Math.max(W, H), ph = Array.from({ length: 5 }, () => R() * 6.28);
    for (let k = 1; k <= 13; k++) { const pts = []; for (let i = 0; i <= 28; i++) { const a = (i / 28) * 6.283, wob = 1 + 0.16 * Math.sin(a * 2 + ph[0]) + 0.1 * Math.sin(a * 3 + ph[1]) + 0.05 * Math.sin(a * 5 + ph[2] + k * 0.3); pts.push([cx + Math.cos(a) * m * 0.062 * k * wob, cy + Math.sin(a) * m * 0.048 * k * wob]); } body.push(path(smooth(pts), K(k % 4 === 0 ? P.b : P.a, k % 4 === 0 ? 1.6 : 1), { opacity: n1(Math.max(0.12, 0.75 - k * 0.045)) })); }
    return { defs: [lin(id + "bg", [[0, P.bgA], [1, P.bgB]])], body };
  },
  beams(W, H, P, id) {
    const body = [rect(0, 0, W, H, 0, F(P.bgB))], cols = [P.a, P.b, P.c, P.a];
    cols.forEach((c, i) => body.push(rect(W * (0.08 + i * 0.22), -H * 0.4, W * 0.11, H * 1.9, 0, F(url(id + "b" + i)), { transform: `rotate(24 ${n1(W / 2)} ${n1(H / 2)})`, filter: url(id + "bl"), opacity: 0.85 })));
    return { defs: cols.map((c, i) => lin(id + "b" + i, [[0, c, 0.95], [1, c, 0]])).concat([blur(id + "bl", Math.max(W, H) * 0.028)]), body };
  },
  facets(W, H, P, id, o, R) {
    const nx = W >= H ? 7 : 5, ny = Math.max(4, Math.round(nx * H / W)), pts = [], body = [], cols = [P.aX, P.aD, P.a, P.b, P.bL, P.c, P.cL];
    for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) pts.push([(W / nx) * (i + (i && i < nx ? (R() - 0.5) * 0.7 : 0)), (H / ny) * (j + (j && j < ny ? (R() - 0.5) * 0.7 : 0))]);
    const at = (i, j) => pts[j * (nx + 1) + i], shade = (a, b, c) => { const t = ((a[0] + b[0] + c[0]) / 3 / W) * 0.6 + ((a[1] + b[1] + c[1]) / 3 / H) * 0.4 + (R() - 0.5) * 0.22; return cols[Math.max(0, Math.min(cols.length - 1, Math.floor(t * cols.length)))]; };
    for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) { const a = at(i, j), b = at(i + 1, j), c = at(i, j + 1), d = at(i + 1, j + 1); [[a, b, c], [b, d, c]].forEach((t) => { const col = shade(t[0], t[1], t[2]); body.push(path(poly(t), `fill:${col};stroke:${col};stroke-width:.6`)); }); }
    return { defs: [], body };
  },
  orbit(W, H, P, id, o, R) {
    const m = Math.max(W, H), body = [rect(0, 0, W, H, 0, F(url(id + "bg")))];
    for (let i = 0; i < 70; i++) body.push(circ(R() * W, R() * H * 0.8, 0.5 + R() * 1.2, F("#fff"), { opacity: n1(0.2 + R() * 0.7) }));
    body.push(circ(W * 0.5, H * 1.5, m * 0.86, F(url(id + "gl")), { filter: url(id + "bl") }), circ(W * 0.5, H * 1.52, m * 0.8, F(url(id + "pl"))), path(`M${n1(W * 0.5 - m * 0.8)} ${n1(H * 1.52)} A${n1(m * 0.8)} ${n1(m * 0.8)} 0 0 1 ${n1(W * 0.5 + m * 0.8)} ${n1(H * 1.52)}`, K(P.aL, 1.6), { opacity: 0.8 }),
      ell(W * 0.5, H * 0.5, m * 0.42, m * 0.1, K(P.b, 1.2), { opacity: 0.5, transform: `rotate(-12 ${n1(W / 2)} ${n1(H / 2)})` }), circ(W * 0.5 + m * 0.36, H * 0.5 - m * 0.115, 4.5, F(P.c)), circ(W * 0.2, H * 0.28, m * 0.035, F(url(id + "mn"))));
    return { defs: [lin(id + "bg", [[0, "#05060d"], [1, P.aX]]), rad(id + "pl", [[0.7, "#06070f"], [1, P.aX]]), rad(id + "gl", [[0.8, P.a, 0.9], [1, P.a, 0]]), rad(id + "mn", [[0, P.bL], [1, P.bD]], 0.35, 0.35, 0.7), blur(id + "bl", m * 0.02)], body };
  },
  aurora(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "bg")))], cols = [P.c, P.b, P.a];
    for (let i = 0; i < 60; i++) body.push(circ(R() * W, R() * H * 0.7, 0.4 + R() * 1.1, F("#fff"), { opacity: n1(0.2 + R() * 0.6) }));
    cols.forEach((c, k) => { const pts = [], base = H * (0.2 + k * 0.1), ph = R() * 6.28; for (let i = 0; i <= 8; i++) pts.push([(W / 8) * i, base + Math.sin(ph + i * 0.8) * H * 0.09]); const back = pts.map(([x, y]) => [x, y + H * (0.24 + k * 0.03)]).reverse(); body.push(path(smooth(pts) + " L" + back.map((q) => n1(q[0]) + " " + n1(q[1])).join(" L") + " Z", F(url(id + "au" + k)), { filter: url(id + "bl"), opacity: 0.8 })); });
    const hill = [[0, H * 0.86], [W * 0.2, H * 0.78], [W * 0.42, H * 0.86], [W * 0.63, H * 0.76], [W * 0.84, H * 0.84], [W, H * 0.79]];
    body.push(path(smooth(hill) + ` L${W} ${H} L0 ${H} Z`, F("#05070d")));
    return { defs: [lin(id + "bg", [[0, "#060913"], [1, "#101a33"]]), blur(id + "bl", Math.max(W, H) * 0.02)].concat(cols.map((c, k) => lin(id + "au" + k, [[0, c, 0.9], [1, c, 0]]))), body };
  },
  peaks(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "sky"))), circ(W * 0.7, H * 0.34, Math.min(W, H) * 0.12, F("#fff"), { opacity: 0.9 }), circ(W * 0.7, H * 0.34, Math.min(W, H) * 0.2, F("#fff"), { opacity: 0.18 })], layers = [[0.52, 0.2, P.bL], [0.64, 0.17, P.a], [0.76, 0.14, P.aD], [0.9, 0.08, P.aX]];
    layers.forEach(([base, amp, col], k) => { const pts = [[0, H * base]], n = 7 + k * 2; for (let i = 1; i < n; i++) pts.push([(W / n) * i + (R() - 0.5) * W * 0.05, H * (base - (i % 2 ? amp * (0.5 + R() * 0.7) : amp * R() * 0.3))]); pts.push([W, H * base]); body.push(path(poly(pts.concat([[W, H], [0, H]])), F(col), { opacity: k === 0 ? 0.8 : 1 })); });
    return { defs: [lin(id + "sky", [[0, P.sky2], [1, P.sky1]])], body };
  },
  dunes(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "sky"))), circ(W * 0.28, H * 0.36, Math.min(W, H) * 0.13, F(url(id + "sun")))], layers = [[0.56, P.bL], [0.68, P.b], [0.8, P.a], [0.92, P.aD]];
    layers.forEach(([base, col]) => { const pts = [], ph = R() * 6.28; for (let i = 0; i <= 6; i++) pts.push([(W / 6) * i, H * (base + Math.sin(ph + i * 1.25) * 0.055)]); body.push(path(smooth(pts) + ` L${W} ${H} L0 ${H} Z`, F(col))); });
    return { defs: [lin(id + "sky", [[0, P.sky2], [1, P.cL]]), lin(id + "sun", [[0, "#fff"], [1, P.cL]])], body };
  },
  coast(W, H, P, id, o, R) {
    const hz = H * 0.56, body = [rect(0, 0, W, hz, 0, F(url(id + "sky"))), circ(W * 0.62, hz - H * 0.07, Math.min(W, H) * 0.12, F("#fff"), { opacity: 0.92 }), rect(0, hz, W, H - hz, 0, F(url(id + "sea")))];
    for (let i = 0; i < 7; i++) body.push(rect(W * 0.62 - W * (0.03 + i * 0.022), hz + 6 + i * (H - hz) * 0.1, W * (0.06 + i * 0.044), 2.4, 1.2, F("#fff"), { opacity: n1(0.6 - i * 0.07) }));
    body.push(path(smooth([[0, hz + H * 0.02], [W * 0.12, hz - H * 0.1], [W * 0.26, hz - H * 0.04], [W * 0.36, hz + H * 0.02]]) + ` L0 ${n1(hz + H * 0.02)} Z`, F(P.aX)), path(smooth([[0, H * 0.86], [W * 0.3, H * 0.8], [W * 0.62, H * 0.9], [W, H * 0.82]]) + ` L${W} ${H} L0 ${H} Z`, F(P.cL)));
    return { defs: [lin(id + "sky", [[0, P.sky2], [1, P.cL]]), lin(id + "sea", [[0, P.b], [1, P.aD]])], body };
  },
  city(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "sky"))), circ(W * 0.78, H * 0.24, Math.min(W, H) * 0.08, F("#fff"), { opacity: 0.85 })];
    [[0.5, P.a, 0.55], [0.36, P.aX, 1]].forEach(([top, col, op], k) => { let x = -4; while (x < W) { const w = W * (0.05 + R() * 0.07), hh = H * (top - 0.14 + R() * 0.3), y = H - hh; body.push(rect(x, y, w, hh, 2, F(col), { opacity: op })); if (k) for (let wy = y + 9; wy < H - 8; wy += 11) for (let wx = x + 6; wx < x + w - 6; wx += 9) if (R() < 0.42) body.push(rect(wx, wy, 3.6, 5, 0.8, F(R() < 0.7 ? "#ffd98a" : P.bL), { opacity: 0.9 })); x += w + 3; } });
    return { defs: [lin(id + "sky", [[0, P.aX], [0.6, P.aD], [1, P.b]])], body };
  },
  forest(W, H, P, id, o, R) {
    const body = [rect(0, 0, W, H, 0, F(url(id + "sky"))), circ(W * 0.3, H * 0.3, Math.min(W, H) * 0.1, F("#fff"), { opacity: 0.85 })], rows = [[0.62, 0.2, P.bL, 0.75], [0.76, 0.26, P.a, 1], [0.94, 0.32, P.aX, 1]];
    rows.forEach(([base, size, col, op]) => { let x = -W * 0.03; while (x < W + W * 0.03) { const s = Math.min(W, H) * size * (0.7 + R() * 0.5), y = H * base; body.push(path(poly([[x, y], [x + s * 0.24, y - s], [x + s * 0.48, y]]), F(col), { opacity: op })); x += s * (0.26 + R() * 0.16); } body.push(rect(0, H * base - 1, W, H * (1 - base) + 1, 0, F(col), { opacity: op })); });
    return { defs: [lin(id + "sky", [[0, P.sky2], [1, P.cL]])], body };
  },
  ui(W, H, P, id, o, R) {
    const m = Math.min(W, H) * 0.07, w = W - m * 2, hh = H - m * 2, v = o.variant || ["dashboard", "landing", "mobile"][Math.floor(R() * 3)], body = [rect(0, 0, W, H, 0, F(url(id + "bg"))), rect(m + 3, m + 8, w, hh, 10, F("rgba(0,0,0,.2)"), { filter: url(id + "sh") }), rect(m, m, w, hh, 10, F(P.paper)), rect(m, m, w, hh * 0.1, 10, F(P.themed ? "var(--fl-surface-2)" : "#f1f2f6")), [0, 1, 2].map((i) => circ(m + 12 + i * 10, m + hh * 0.05, 2.6, F([P.a, P.b, P.c][i])))];
    const bar = (x, y, bw, bh, col, op = 1, rx = 3) => body.push(rect(m + w * x, m + hh * y, w * bw, hh * bh, rx, F(col), { opacity: op })), mute = P.themed ? "var(--fl-surface-3)" : "#e6e8ee";
    if (v === "landing") { bar(0.3, 0.2, 0.4, 0.055, P.ink, 0.85); bar(0.36, 0.29, 0.28, 0.03, mute); bar(0.42, 0.36, 0.16, 0.06, P.a, 1, 6); bar(0.08, 0.5, 0.26, 0.38, P.aL, 0.7, 8); bar(0.37, 0.5, 0.26, 0.38, P.bL, 0.7, 8); bar(0.66, 0.5, 0.26, 0.38, P.cL, 0.7, 8); }
    else if (v === "mobile") { bar(0.34, 0.16, 0.32, 0.78, mute, 1, 14); bar(0.38, 0.22, 0.24, 0.16, P.a, 1, 8); bar(0.38, 0.42, 0.24, 0.07, P.paper, 1, 6); bar(0.38, 0.52, 0.24, 0.07, P.paper, 1, 6); bar(0.38, 0.62, 0.24, 0.07, P.paper, 1, 6); bar(0.38, 0.8, 0.24, 0.07, P.ink, 0.85, 8); }
    else { bar(0.03, 0.15, 0.17, 0.8, mute, 1, 6); [0, 1, 2, 3].forEach((i) => bar(0.05, 0.2 + i * 0.07, 0.11, 0.03, i ? P.line : P.a, i ? 0.8 : 1)); [0, 1, 2].forEach((i) => { bar(0.23 + i * 0.25, 0.15, 0.23, 0.2, [P.aL, P.bL, P.cL][i], 0.6, 6); bar(0.25 + i * 0.25, 0.2, 0.1, 0.05, P.ink, 0.8); });
      bar(0.23, 0.4, 0.73, 0.55, mute, 0.7, 6); const pts = []; for (let i = 0; i <= 9; i++) pts.push([m + w * (0.26 + i * 0.073), m + hh * (0.84 - R() * 0.3 - i * 0.012)]); body.push(path(smooth(pts) + ` L${n1(pts[9][0])} ${n1(m + hh * 0.92)} L${n1(pts[0][0])} ${n1(m + hh * 0.92)} Z`, F(P.a), { opacity: 0.18 }), path(smooth(pts), K(P.a, 2.4))); }
    return { defs: [lin(id + "bg", [[0, P.aL], [1, P.b]], 0, 0, 1, 1), blur(id + "sh", 8)], body };
  },
  cover(W, H, P, id, o, R) {
    const v = Math.floor(R() * 5), m = Math.max(W, H), body = [rect(0, 0, W, H, 0, F(url(id + "bg")))];
    if (v === 0) for (let i = 7; i >= 1; i--) body.push(circ(W * 0.5, H * 0.94, m * 0.11 * i, F(i % 2 ? P.b : P.aX), { opacity: 0.55 }));
    else if (v === 1) [0, 1, 2, 3].forEach((i) => body.push(path(`M0 ${n1(H * (0.34 + i * 0.17))} A${n1(W / 2)} ${n1(W / 2)} 0 0 1 ${W} ${n1(H * (0.34 + i * 0.17))} L${W} ${H} L0 ${H} Z`, F([P.c, P.b, P.a, P.aX][i]), { opacity: 0.9 })));
    else if (v === 2) for (let i = -6; i < 14; i++) body.push(rect(i * W * 0.1, -H * 0.3, W * 0.05, H * 1.7, 0, F(i % 2 ? P.c : P.aX), { opacity: 0.55, transform: `rotate(32 ${n1(W / 2)} ${n1(H / 2)})` }));
    else if (v === 3) { body.push(circ(W * 0.5, H * 0.46, m * 0.3, F(url(id + "sun")))); for (let i = 0; i < 6; i++) body.push(rect(0, H * (0.5 + i * 0.065), W, H * (0.012 + i * 0.008), 0, F(url(id + "bg")))); }
    else for (let y = 0; y < 6; y++) for (let x = 0; x < 6; x++) body.push(circ(W * (0.14 + x * 0.145), H * (0.14 + y * 0.145), m * 0.006 * (1 + x + y), F((x + y) % 3 ? P.cL : P.b), { opacity: 0.9 }));
    if (o.label) body.push(h("text", { x: n1(W * 0.08), y: n1(H * 0.16), style: `fill:#fff;font:700 ${n1(m * 0.075)}px var(--fl-font-display, sans-serif);letter-spacing:-.03em` }, String(o.label).slice(0, 16)));
    return { defs: [lin(id + "bg", [[0, P.aD], [1, P.aX]], 0, 0, 1, 1), lin(id + "sun", [[0, P.cL], [1, P.b]])], body };
  },
  poster(W, H, P, id, o) {
    const m = Math.min(W, H);
    return { defs: [lin(id + "bg", [[0, P.bgA], [1, P.bgB]], 0, 0, 1, 1)], body: [rect(0, 0, W, H, 0, F(url(id + "bg"))), h("text", { x: n1(W * 0.1), y: n1(H * 0.66), style: `fill:${P.ink};font:${o.variant === "serif" ? "400" : "700"} ${n1(m * 0.5)}px ${o.variant === "serif" ? 'var(--fl-font-serif, "Instrument Serif", serif)' : o.variant === "mono" ? "var(--fl-mono, monospace)" : 'var(--fl-font-display, sans-serif)'};letter-spacing:-.05em` }, String(o.label || "Aa").slice(0, 3)),
      rect(W * 0.1, H * 0.76, W * 0.4, 3, 1.5, F(P.ink), { opacity: 0.7 }), rect(W * 0.1, H * 0.82, W * 0.26, 3, 1.5, F(P.ink), { opacity: 0.35 }), circ(W * 0.84, H * 0.18, m * 0.05, F(P.a))] };
  },
  glyph(W, H, P, id, o) {
    const m = Math.min(W, H), s = m * 0.4, d = ICONS[o.glyph] || ICONS.sparkles;
    return { defs: [lin(id + "bg", [[0, P.a], [1, P.b]], 0, 0, 1, 1), rad(id + "hl", [[0, "#fff", 0.35], [1, "#fff", 0]], 0.25, 0.15, 0.8)], body: [rect(0, 0, W, H, 0, F(url(id + "bg"))), rect(0, 0, W, H, 0, F(url(id + "hl"))), circ(W * 0.85, H * 0.9, m * 0.4, F("#fff"), { opacity: 0.1 }),
      h("g", { transform: `translate(${n1(W / 2 - s / 2)} ${n1(H / 2 - s / 2)}) scale(${n1(s / 24)})` }, path(d, "fill:none;stroke:#fff;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round"))] };
  },
  qr(W, H, P, id, o, R) {
    const n = 21, s = Math.min(W, H) * 0.8 / n, ox = W / 2 - (s * n) / 2, oy = H / 2 - (s * n) / 2, body = [rect(0, 0, W, H, 0, F(P.paper))], finder = (x, y) => [rect(ox + x * s, oy + y * s, s * 7, s * 7, s, F(P.ink)), rect(ox + (x + 1) * s, oy + (y + 1) * s, s * 5, s * 5, s * 0.6, F(P.paper)), rect(ox + (x + 2) * s, oy + (y + 2) * s, s * 3, s * 3, s * 0.5, F(P.ink))];
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) { if ((x < 8 && y < 8) || (x > 12 && y < 8) || (x < 8 && y > 12)) continue; if (R() < 0.48) body.push(rect(ox + x * s, oy + y * s, s * 0.94, s * 0.94, s * 0.25, F(P.ink))); }
    body.push(finder(0, 0), finder(14, 0), finder(0, 14));
    return { defs: [], body };
  },
  weather(W, H, P, id, o) {
    const u = Math.min(W, H), cx = W / 2, cy = H / 2, v = o.variant || "sun", body = [rect(0, 0, W, H, 0, F(url(id + "bg")))];
    const sun = (x, y, r) => [circ(x, y, r * 1.7, F("#ffd76a"), { opacity: 0.25 }), circ(x, y, r, F(url(id + "sun")))], cloud = (x, y, s, col = "#fff") => [circ(x - s * 0.5, y + s * 0.1, s * 0.42, F(col)), circ(x, y - s * 0.16, s * 0.58, F(col)), circ(x + s * 0.56, y + s * 0.12, s * 0.4, F(col)), rect(x - s * 0.9, y + s * 0.1, s * 1.86, s * 0.42, s * 0.21, F(col))];
    if (v === "sun") body.push(sun(cx, cy, u * 0.18));
    else if (v === "moon") body.push(circ(cx, cy, u * 0.19, F("#f4f1ff")), circ(cx + u * 0.085, cy - u * 0.05, u * 0.17, F(url(id + "bg"))), [[-0.3, -0.24], [0.28, 0.2], [0.34, -0.3]].map(([x, y]) => circ(cx + u * x, cy + u * y, 1.8, F("#fff"))));
    else if (v === "partly") body.push(sun(cx + u * 0.14, cy - u * 0.12, u * 0.13), cloud(cx - u * 0.04, cy + u * 0.08, u * 0.24));
    else { body.push(cloud(cx, cy - u * 0.06, u * 0.27, v === "storm" ? "#c5cbe0" : "#fff"));
      if (v === "rain" || v === "storm") [-0.2, -0.07, 0.06, 0.19].forEach((x, i) => body.push(path(`M${n1(cx + u * x)} ${n1(cy + u * 0.17)} l${n1(-u * 0.035)} ${n1(u * 0.1)}`, K("#8fd0ff", 3.4), { opacity: i % 2 ? 0.75 : 1 })));
      if (v === "storm") body.push(path(poly([[cx + u * 0.02, cy + u * 0.1], [cx - u * 0.07, cy + u * 0.24], [cx, cy + u * 0.24], [cx - u * 0.04, cy + u * 0.36], [cx + u * 0.09, cy + u * 0.19], [cx + u * 0.02, cy + u * 0.19]]), F("#ffd76a")));
      if (v === "snow") [-0.19, -0.06, 0.07, 0.2].forEach((x, i) => body.push(circ(cx + u * x, cy + u * (0.2 + (i % 2) * 0.07), 3.6, F("#fff")))); }
    return { defs: [lin(id + "bg", [[0, P.a], [1, P.b]], 0, 0, 1, 1), rad(id + "sun", [[0, "#fff3b0"], [1, "#ffb83d"]], 0.35, 0.35, 0.7)], body };
  },
};

export const ART_KINDS = Object.keys(PRODUCTS).concat(Object.keys(SCENES));
const RATIO = { "1:1": [400, 400], "4:3": [400, 300], "3:2": [420, 280], "16:9": [480, 270], "21:9": [560, 240], "3:4": [300, 400], "2:3": [280, 420], "9:16": [270, 480], "2:1": [480, 240], "3:1": [600, 200], "5:4": [400, 320], "4:5": [320, 400] };

/** Build the SVG for an Art node. `uid` keeps gradient ids unique within the document. */
export function drawArt(p, uid) {
  const kind = PRODUCTS[p.kind] || SCENES[p.kind] ? p.kind : "mesh", [W, H] = RATIO[p.ratio] || RATIO["4:3"], dark = p.tone === "dark";
  const id = "fa" + hashOf(uid + kind).toString(36), P = palette(p, dark), R = rng(hashOf(kind + (p.seed ?? p.label ?? p.hue ?? uid)));
  let defs, body;
  if (PRODUCTS[kind]) {
    const st = studio(W, H, P, id, dark, { glasses: 0.36, card: 0, headphones: 0.3, dish: 0, phone: 0.2, watch: 0.14, portrait: 0, fruit: 0.22, box: 0.26 }[kind] ?? 0.3);
    defs = st.defs.concat([rad(id + "gl", [[0, "#ffd98a", 0.75], [1, "#ffd98a", 0]]), rad(id + "fc", [[0, P.aD, 0.9], [1, "#0b0c10", 0.2]], 0.5, 0.3, 0.8), lin(id + "scr", [[0, P.a], [0.55, P.b], [1, P.c]], 0, 0, 1, 1), lin(id + "ln", [[0, P.aL, 0.75], [1, P.b, 0.55]], 0, 0, 1, 1),
      rad(id + "fr", [[0, P.aL], [0.55, P.a], [1, P.aD]], 0.36, 0.3, 0.8), lin(id + "cd", [[0, P.a], [0.5, P.b], [1, P.aX]], 0, 0, 1, 1), lin(id + "bun", [[0, "#f0b867"], [1, "#d08a35"]])]);
    body = st.body.concat(PRODUCTS[kind](W, H, P, id, p, R));
    if (kind === "card" || kind === "dish" || kind === "portrait") body.splice(2, 1); // these cast their own shadow or sit flat
    if (p.bare) body.splice(0, 2); // no backdrop: the drawing sits on whatever is behind it
  } else ({ defs, body } = SCENES[kind](W, H, P, id, p, R));
  return h("svg", { class: "fl-art-svg", viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: p.fit === "contain" ? "xMidYMid meet" : "xMidYMid slice", role: "img", "aria-label": p.alt || p.label || `${kind} artwork` }, h("defs", null, defs), body);
}
