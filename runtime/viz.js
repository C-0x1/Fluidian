// Fluidian runtime — data visualisation blocks beyond the core Chart: rings, gauges, heatmaps,
// ranked bars, tickers, candlesticks, funnels, maps, calendars, schedules and roadmaps.
import { h, cx } from "./core.js";
import { R, renderNode, icon, fmt, spark } from "./components.js";
import { hashOf, rng, oklch } from "./art.js";

const arr = (v) => (Array.isArray(v) ? v : []);
const str = (v) => (v === null || v === undefined ? "" : String(v));
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(v) || 0));
const n1 = (v) => Number(v.toFixed(1));

const sparkline = (values, w, hgt, opts) => spark(values, w, hgt, opts);
R.Sparkline = (n) => h("div", { class: `fl-sparkline fl-tone-${n.props.tone || "brand"}` }, sparkline(n.props.values, Number(n.props.width) || 160, Number(n.props.height) || 44, { kind: n.props.kind === "bar" ? "bar" : "line", area: n.props.kind !== "line" }));

R.Rings = (n) => {
  const p = n.props, items = arr(p.items).slice(0, 4), size = clamp(p.size || 168, 72, 360), sw = size * [0.12, 0.12, 0.105, 0.085, 0.07][items.length], mid = size / 2, hole = mid - items.length * (sw + 3);
  return h("div", { class: cx("fl-rings", p.legend === false && "no-legend") }, h("svg", { viewBox: `0 0 ${size} ${size}`, width: size, height: size, role: "img", "aria-label": items.map((it) => `${it.label}: ${it.display || it.value}`).join(", ") },
    items.map((it, i) => { const r = mid - sw / 2 - i * (sw + 3), len = 2 * Math.PI * r, pct = clamp((Number(it.value) || 0) / (Number(it.max) || 100)), col = it.color ? `stroke:${str(it.color)}` : null;
      return [h("circle", { cx: mid, cy: mid, r: n1(r), class: `fl-ring-track s${i}`, "stroke-width": n1(sw), style: col }), h("circle", { cx: mid, cy: mid, r: n1(r), class: `fl-ring-value s${i}`, "stroke-width": n1(sw), "stroke-dasharray": `${n1(len * pct)} ${n1(len)}`, transform: `rotate(-90 ${mid} ${mid})`, style: col })]; }),
    p.center ? h("text", { x: mid, y: mid + 1, class: "fl-ring-center", "text-anchor": "middle", "dominant-baseline": "middle", style: `font-size:${n1(Math.max(11, Math.min(34, (hole * 1.5) / Math.max(2, str(p.center).length * 0.5))))}px` }, str(p.center)) : null),
    p.legend === false ? null : h("ul", { class: "fl-rings-legend" }, items.map((it, i) => h("li", null, h("i", { class: `fl-series-dot s${i}`, style: it.color ? { background: str(it.color) } : null }), h("span", null, it.label), h("strong", null, str(it.display ?? it.value))))));
};
R.Gauge = (n) => {
  const p = n.props, pct = clamp((Number(p.value) || 0) / (Number(p.max) || 100)), size = clamp(p.size || 180, 80, 360), sw = size * 0.085, r = size / 2 - sw, mid = size / 2, len = 2 * Math.PI * r, arc = len * 0.75;
  return h("div", { class: `fl-gauge fl-tone-${p.tone || "brand"}` }, h("svg", { viewBox: `0 0 ${size} ${n1(size * 0.88)}`, width: size, height: n1(size * 0.88), role: "img", "aria-label": `${p.label || "Gauge"}: ${p.display ?? p.value}${p.unit ? " " + p.unit : ""}` },
    h("circle", { cx: mid, cy: mid, r: n1(r), class: "fl-gauge-track", "stroke-width": n1(sw), "stroke-dasharray": `${n1(arc)} ${n1(len)}`, transform: `rotate(135 ${mid} ${mid})` }),
    h("circle", { cx: mid, cy: mid, r: n1(r), class: "fl-gauge-value", "stroke-width": n1(sw), "stroke-dasharray": `${n1(arc * pct)} ${n1(len)}`, transform: `rotate(135 ${mid} ${mid})` }),
    h("text", { x: mid, y: mid + size * 0.03, class: "fl-gauge-num", "text-anchor": "middle", style: `font-size:${n1(size * 0.2)}px` }, str(p.display ?? p.value)), p.unit && h("text", { x: mid, y: mid + size * 0.17, class: "fl-gauge-unit", "text-anchor": "middle" }, p.unit)),
    p.label && h("div", { class: "fl-gauge-label" }, p.label), p.detail && h("div", { class: "fl-gauge-detail" }, p.detail));
};
R.Heatmap = (n) => {
  const p = n.props;
  let rows = arr(p.values);
  if (rows.length && !Array.isArray(rows[0])) { const cols = clamp(p.columns || 7, 1, 60), flat = rows; rows = []; for (let i = 0; i < flat.length; i += cols) rows.push(flat.slice(i, i + cols)); }
  const max = Number(p.max) || Math.max(1, ...rows.flat().map((v) => Number(v) || 0)), rl = arr(p.rowLabels), cl = arr(p.colLabels), width = Math.max(1, ...rows.map((r) => r.length));
  return h("div", { class: `fl-heatmap fl-tone-${p.tone || "brand"} is-${p.shape || "square"}`, style: { "--fl-cols": width }, role: "img", "aria-label": p.label || "Heatmap" },
    cl.length ? h("div", { class: "fl-heatmap-row is-head" }, rl.length ? h("span", { class: "fl-heatmap-label" }) : null, cl.map((l) => h("span", { class: "fl-heatmap-col" }, str(l)))) : null,
    rows.map((row, ri) => h("div", { class: "fl-heatmap-row" }, rl.length ? h("span", { class: "fl-heatmap-label" }, str(rl[ri] ?? "")) : null, arr(row).map((v) => h("i", { class: "fl-heatmap-cell", style: { "--v": Math.round(clamp((Number(v) || 0) / max) * 100) + "%" }, title: str(v) })))));
};
R.BarList = (n) => {
  const p = n.props, items = arr(p.items), max = Number(p.max) || Math.max(1, ...items.map((it) => Number(it.value) || 0));
  return h("ul", { class: `fl-barlist fl-tone-${p.tone || "brand"} is-${p.variant || "bar"}` }, items.map((it, i) => h("li", { class: "fl-barlist-row" }, p.ranked ? h("span", { class: "fl-barlist-rank" }, String(i + 1)) : null,
    it.icon || it.hue !== undefined ? h("span", { class: "fl-barlist-icon", style: it.hue !== undefined ? { background: oklch(0.62, 0.17, Number(it.hue)), color: "#fff" } : null }, it.icon ? icon(it.icon, 14) : str(it.label).slice(0, 1).toUpperCase()) : null,
    h("div", { class: "fl-barlist-main" }, h("div", { class: "fl-barlist-top" }, h("span", { class: "fl-barlist-label" }, it.label), it.detail && h("span", { class: "fl-barlist-detail" }, it.detail), h("span", { class: "fl-barlist-value" }, str(it.display ?? fmt(it.value, p.format || "compact")))),
      h("div", { class: "fl-barlist-track" }, h("i", { style: { width: (clamp((Number(it.value) || 0) / max) * 100).toFixed(1) + "%", background: it.color ? str(it.color) : null } }))))));
};
R.Ticker = (n) => h("ul", { class: `fl-ticker is-${n.props.layout || "list"}` }, arr(n.props.items).map((it) => {
  const up = !/^\s*[-−]/.test(str(it.change));
  return h("li", { class: cx("fl-ticker-row", up ? "is-up" : "is-down") }, h("span", { class: "fl-ticker-sym" }, h("b", null, it.symbol), it.name && h("small", null, it.name)), sparkline(it.spark, 72, 26, { dot: false }), h("span", { class: "fl-ticker-px" }, h("b", null, str(it.price)), h("small", null, str(it.change))));
}));
R.Funnel = (n) => {
  const p = n.props, st = arr(p.stages), max = Math.max(1, ...st.map((s) => Number(s.value) || 0));
  return h("ol", { class: `fl-funnel fl-tone-${p.tone || "brand"}` }, st.map((s, i) => h("li", { class: "fl-funnel-row" }, h("div", { class: "fl-funnel-label" }, s.label),
    h("div", { class: "fl-funnel-track" }, h("div", { class: "fl-funnel-bar", style: { width: Math.max(14, Math.pow((Number(s.value) || 0) / max, 0.5) * 100).toFixed(1) + "%", opacity: Math.max(0.45, 1 - i * 0.12).toFixed(2) } }, h("span", null, fmt(s.value, p.format || "compact")))),
    h("div", { class: "fl-funnel-rate" }, i && Number(st[i - 1].value) ? Math.round((Number(s.value) || 0) / Number(st[i - 1].value) * 100) + "%" : ""))));
};
R.Waveform = (n) => {
  const p = n.props, count = clamp(p.bars || 56, 8, 200), R0 = rng(hashOf(str(p.seed ?? n.id))), given = arr(p.values).map(Number).filter(isFinite), peak = Math.max(1, ...given);
  const vals = given.length ? given.map((v) => v / peak) : Array.from({ length: count }, (_, i) => 0.18 + 0.82 * Math.abs(Math.sin(i * 0.29 + R0() * 1.6)) * (0.35 + R0() * 0.65)), prog = clamp(p.progress);
  return h("div", { class: `fl-waveform fl-tone-${p.tone || "brand"}`, style: { height: clamp(p.height || 48, 16, 240) + "px" }, role: "img", "aria-label": p.label || "Waveform" }, vals.map((v, i) => h("i", { class: cx(i / vals.length < prog && "is-played"), style: { height: Math.round(clamp(v, 0.08, 1) * 100) + "%" } })));
};
R.Candles = (n, c) => {
  const p = n.props, data = arr(p.data), box = c.state(n.id, { w: 640 }), W = Math.max(280, Math.round(box.w)), H = clamp(p.height || 280, 120, 640), m = { l: 8, r: 52, t: 10, b: 22 }, vol = p.volume !== false && data.some((d) => d.v), vh = vol ? H * 0.16 : 0, iw = W - m.l - m.r, ih = H - m.t - m.b - vh;
  const measure = (el) => { const w = el.clientWidth; if (w && Math.abs(w - box.w) > 6) c.set(n.id, { w }); };
  if (!data.length) return h("figure", { class: "fl-chart fl-candles", hook: { mount: measure, update: measure } }, h("svg", { class: "fl-chart-svg", viewBox: `0 0 ${W} ${H}` }, h("text", { x: W / 2, y: H / 2, class: "fl-chart-empty", "text-anchor": "middle" }, "No data")));
  const lo = Math.min(...data.map((d) => Number(d.l))), hi = Math.max(...data.map((d) => Number(d.h))), pad = (hi - lo) * 0.06 || 1, Y = (v) => m.t + ih - ((v - lo + pad) / (hi - lo + pad * 2)) * ih, step = iw / data.length, bw = Math.max(2, Math.min(14, step * 0.62)), vmax = Math.max(1, ...data.map((d) => Number(d.v) || 0));
  const g = [0, 1, 2, 3, 4].map((i) => { const v = lo + ((hi - lo) / 4) * i; return [h("line", { x1: m.l, x2: W - m.r, y1: n1(Y(v)), y2: n1(Y(v)), class: "fl-grid-line" }), h("text", { x: W - m.r + 8, y: n1(Y(v) + 4), class: "fl-chart-tick" }, fmt(v, p.format || "number"))]; });
  data.forEach((d, i) => { const x = m.l + step * i + step / 2, up = Number(d.c) >= Number(d.o), cls = up ? "is-up" : "is-down";
    g.push(h("line", { x1: n1(x), x2: n1(x), y1: n1(Y(Number(d.h))), y2: n1(Y(Number(d.l))), class: `fl-candle-wick ${cls}` }), h("rect", { x: n1(x - bw / 2), y: n1(Math.min(Y(Number(d.o)), Y(Number(d.c)))), width: n1(bw), height: n1(Math.max(1.5, Math.abs(Y(Number(d.o)) - Y(Number(d.c))))), rx: 1.5, class: `fl-candle-body ${cls}` }, h("title", null, `${d.t ?? i}: open ${d.o}, high ${d.h}, low ${d.l}, close ${d.c}`)));
    if (vol) g.push(h("rect", { x: n1(x - bw / 2), y: n1(H - m.b - ((Number(d.v) || 0) / vmax) * vh), width: n1(bw), height: n1(Math.max(1, ((Number(d.v) || 0) / vmax) * vh)), rx: 1, class: `fl-candle-vol ${cls}` }));
    if (d.t !== undefined && i % Math.ceil(data.length / 7) === 0) g.push(h("text", { x: n1(x), y: H - 6, class: "fl-chart-tick", "text-anchor": "middle" }, str(d.t))); });
  const last = data[data.length - 1], ly = Y(Number(last.c)), lup = Number(last.c) >= Number(last.o);
  g.push(h("line", { x1: m.l, x2: W - m.r, y1: n1(ly), y2: n1(ly), class: `fl-candle-last ${lup ? "is-up" : "is-down"}` }), h("rect", { x: W - m.r + 2, y: n1(ly - 9), width: m.r - 4, height: 18, rx: 4, class: `fl-candle-tag ${lup ? "is-up" : "is-down"}` }), h("text", { x: W - m.r + (m.r - 4) / 2 + 2, y: n1(ly + 4), class: "fl-candle-tag-text", "text-anchor": "middle" }, fmt(last.c, p.format || "number")));
  return h("figure", { class: "fl-chart fl-candles", hook: { mount: measure, update: measure } }, p.title && h("figcaption", { class: "fl-chart-title" }, p.title), h("svg", { class: "fl-chart-svg", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": p.title || "Candlestick chart" }, g));
};

// --- maps ------------------------------------------------------------------------
// Coarse continent outlines (longitude, latitude). They are only used to place dots, so a few points per coast are enough.
const LAND = [
  [[-168, 66], [-156, 71], [-130, 70], [-110, 73], [-95, 72], [-82, 70], [-78, 62], [-64, 60], [-56, 52], [-66, 45], [-75, 39], [-81, 31], [-81, 25], [-90, 30], [-97, 26], [-97, 18], [-88, 16], [-84, 10], [-79, 8], [-92, 15], [-105, 20], [-110, 24], [-117, 32], [-124, 40], [-124, 48], [-135, 58], [-150, 60], [-165, 55]],
  [[-55, 60], [-45, 60], [-22, 70], [-20, 80], [-45, 83], [-70, 78], [-55, 70]],
  [[-80, 9], [-72, 12], [-60, 10], [-50, 2], [-35, -6], [-39, -15], [-48, -25], [-58, -38], [-65, -45], [-68, -54], [-74, -50], [-72, -35], [-71, -18], [-80, -5]],
  [[-10, 36], [-9, 43], [-2, 44], [-5, 48], [2, 51], [8, 54], [9, 58], [5, 61], [12, 66], [25, 71], [40, 68], [42, 62], [30, 60], [28, 56], [21, 55], [30, 46], [40, 46], [36, 40], [27, 40], [23, 37], [18, 40], [12, 44], [15, 38], [10, 44], [3, 43], [0, 38], [-6, 36]],
  [[-17, 15], [-16, 24], [-6, 35], [10, 37], [20, 32], [32, 31], [35, 24], [43, 12], [51, 11], [42, -2], [40, -15], [35, -24], [27, -34], [19, -34], [13, -17], [9, -1], [5, 5], [-8, 5]],
  [[40, 68], [60, 70], [75, 73], [100, 77], [115, 74], [140, 73], [160, 70], [180, 68], [178, 62], [162, 58], [156, 51], [142, 54], [135, 44], [128, 38], [122, 31], [120, 23], [110, 20], [108, 12], [104, 9], [100, 13], [98, 8], [100, 2], [104, 1], [98, 16], [92, 22], [88, 22], [80, 13], [77, 8], [73, 18], [68, 24], [58, 25], [52, 16], [44, 13], [35, 28], [36, 36], [42, 41], [50, 45], [55, 55]],
  [[130, 32], [136, 34], [141, 38], [142, 44], [145, 44], [141, 36], [135, 33]], [[95, 5], [105, -6], [115, -8], [120, -5], [118, 2], [117, 7], [110, 2], [102, -2]], [[131, -1], [141, -3], [150, -6], [146, -9], [138, -8], [132, -4]],
  [[114, -22], [122, -17], [130, -12], [137, -12], [142, -11], [146, -19], [153, -27], [150, -37], [143, -39], [135, -35], [129, -32], [116, -34]], [[172, -34], [178, -38], [174, -41], [168, -46], [166, -45], [172, -41]],
  [[-6, 50], [1, 51], [0, 54], [-3, 58], [-6, 58], [-5, 54]], [[-24, 65], [-14, 66], [-14, 63.5], [-22, 63.5]], [[44, -13], [50, -15], [47, -25], [44, -22]], [[120, 18], [123, 13], [126, 7], [122, 8], [120, 13]],
];
function inside(poly, x, y) {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) { const [xi, yi] = poly[i], [xj, yj] = poly[j]; if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit; }
  return hit;
}
let worldDots = null;
function world(W, H, step) {
  if (worldDots) return worldDots;
  let d = "";
  for (let y = step / 2; y < H; y += step) for (let x = step / 2; x < W; x += step) { const lon = (x / W) * 360 - 180, lat = 84 - (y / H) * 142; if (LAND.some((poly) => inside(poly, lon, lat))) d += `M${n1(x)} ${n1(y)}h0`; }
  return (worldDots = d);
}
R.MapView = (n, c) => {
  const p = n.props, W = 720, H = clamp(p.height || 360, 160, 720), pins = arr(p.pins), routes = arr(p.routes), kind = p.kind === "world" ? "world" : "city", R0 = rng(hashOf(str(p.seed ?? n.id))), g = [];
  const at = (q) => (kind === "world" && q.lon !== undefined ? [((Number(q.lon) + 180) / 360) * W, ((84 - Number(q.lat)) / 142) * H] : [(clamp(q.x, 0, 100) / 100) * W, (clamp(q.y, 0, 100) / 100) * H]);
  if (kind === "world") g.push(h("path", { d: world(W, 364, 9), class: "fl-map-dots", transform: `scale(1 ${n1(H / 364)})` }));
  else {
    const water = [[W * 0.62, 0], [W * 0.7, H * 0.2], [W * 0.86, H * 0.34], [W, H * 0.46], [W, 0]];
    g.push(h("path", { d: `M${water[0][0]} 0 C${n1(W * 0.64)} ${n1(H * 0.16)} ${n1(W * 0.78)} ${n1(H * 0.2)} ${n1(W * 0.84)} ${n1(H * 0.36)} S${n1(W * 0.96)} ${n1(H * 0.5)} ${W} ${n1(H * 0.52)} L${W} 0 Z`, class: "fl-map-water" }));
    [[0.08, 0.58, 0.2, 0.26], [0.42, 0.1, 0.13, 0.2], [0.66, 0.66, 0.16, 0.2]].forEach(([x, y, w, hh]) => g.push(h("rect", { x: n1(W * x), y: n1(H * y), width: n1(W * w), height: n1(H * hh), rx: 14, class: "fl-map-park" })));
    const streets = [];
    for (let i = 1; i < 12; i++) streets.push([`M${n1((W / 12) * i + (R0() - 0.5) * 18)} -40 L${n1((W / 12) * i + (R0() - 0.5) * 18)} ${H + 40}`, i % 4 === 0]);
    for (let j = 1; j < 8; j++) streets.push([`M-40 ${n1((H / 8) * j + (R0() - 0.5) * 14)} L${W + 40} ${n1((H / 8) * j + (R0() - 0.5) * 14)}`, j % 3 === 0]);
    streets.push([`M-40 ${n1(H * 0.9)} L${W + 40} ${n1(H * 0.18)}`, true]);
    g.push(h("g", { transform: `rotate(-9 ${W / 2} ${H / 2})` }, streets.map(([d, major]) => h("path", { d, class: cx("fl-map-road", major && "is-major") }))));
  }
  routes.forEach((r) => {
    const pts = arr(r.points || r).map((q) => (Array.isArray(q) ? at(kind === "world" ? { lon: q[0], lat: q[1] } : { x: q[0], y: q[1] }) : at(pins[q] || q || {})));
    if (pts.length < 2) return;
    let d;
    if (kind === "world") d = pts.slice(1).map((b, i) => { const a = pts[i], mx = (a[0] + b[0]) / 2, my = Math.min(a[1], b[1]) - Math.hypot(b[0] - a[0], b[1] - a[1]) * 0.22; return `M${n1(a[0])} ${n1(a[1])} Q${n1(mx)} ${n1(my)} ${n1(b[0])} ${n1(b[1])}`; }).join(" ");
    else d = pts.map((q, i) => (i ? "L" : "M") + n1(q[0]) + " " + n1(q[1])).join(" ");
    g.push(kind === "city" ? h("path", { d, class: "fl-map-route-case" }) : null, h("path", { d, class: `fl-map-route fl-tone-${r.tone || "brand"}`, "stroke-dasharray": r.dashed ? "2 7" : null }));
  });
  pins.forEach((q, i) => { const [x, y] = at(q), tw = str(q.label).length * 6.2 + 18;
    g.push(h("g", { class: `fl-map-pin fl-tone-${q.tone || "brand"}`, onclick: () => c.emit(n, "select", { value: i }) }, q.pulse ? h("circle", { cx: n1(x), cy: n1(y), r: 13, class: "fl-map-halo" }) : null, h("circle", { cx: n1(x), cy: n1(y), r: q.size || 6, class: "fl-map-dot" }),
      q.label ? [h("rect", { x: n1(Math.min(W - tw - 4, x + 10)), y: n1(y - 11), width: n1(tw), height: 22, rx: 11, class: "fl-map-tag" }), h("text", { x: n1(Math.min(W - tw - 4, x + 10) + tw / 2), y: n1(y + 4), class: "fl-map-tag-text", "text-anchor": "middle" }, str(q.label))] : null)); });
  return h("div", { class: `fl-map is-${kind}` }, h("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "xMidYMid slice", role: "img", "aria-label": p.label || "Map" }, g), arr(n.children).length ? h("div", { class: "fl-map-over" }, arr(n.children).map((k) => renderNode(k, c))) : null);
};

// --- time ------------------------------------------------------------------------
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
R.Calendar = (n, c) => {
  const p = n.props, m = /^(\d{4})-(\d{1,2})$/.exec(str(p.month)) || [0, "2026", "1"], year = Number(m[1]), month = Number(m[2]), first = new Date(year, month - 1, 1), lead = (first.getDay() + 6) % 7, days = new Date(year, month, 0).getDate();
  const st = c.state(n.id, { day: Number(p.selected) || 0 }), by = {};
  arr(p.events).forEach((ev) => { (by[ev.day] = by[ev.day] || []).push(ev); });
  const cells = Array.from({ length: Math.ceil((lead + days) / 7) * 7 }, (_, i) => (i < lead || i >= lead + days ? 0 : i - lead + 1));
  return h("div", { class: cx("fl-calendar", p.compact && "is-compact") }, h("div", { class: "fl-calendar-head" }, h("div", { class: "fl-calendar-title" }, `${MONTHS[month - 1] || ""} ${year}`),
      h("div", { class: "fl-calendar-nav" }, h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Previous month", onclick: () => c.emit(n, "navigate", { value: -1 }) }, icon("chevron-left", 15)), h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Next month", onclick: () => c.emit(n, "navigate", { value: 1 }) }, icon("chevron-right", 15)))),
    h("div", { class: "fl-calendar-grid", role: "grid" }, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => h("div", { class: "fl-calendar-dow" }, d)), cells.map((day, i) => h(day ? "button" : "div", { class: cx("fl-calendar-day", !day && "is-blank", day && day === st.day && "is-selected", day && day === Number(p.today) && "is-today", i % 7 > 4 && "is-weekend"), type: day ? "button" : null, key: "d" + i,
      onclick: day ? () => { c.set(n.id, { day }); c.emit(n, "select", { value: day }); } : null }, day ? h("span", { class: "fl-calendar-num" }, String(day)) : null,
      day ? arr(by[day]).slice(0, p.compact ? 3 : 2).map((ev) => (p.compact ? h("i", { class: `fl-calendar-pip fl-tone-${ev.tone || "brand"}` }) : h("span", { class: `fl-calendar-ev fl-tone-${ev.tone || "brand"}` }, ev.label))) : null,
      day && !p.compact && arr(by[day]).length > 2 ? h("span", { class: "fl-calendar-more" }, `+${by[day].length - 2}`) : null))));
};
const hours = (t) => { const m = /^(\d{1,2})(?::(\d{2}))?$/.exec(str(t)); return m ? Number(m[1]) + (Number(m[2]) || 0) / 60 : Number(t) || 0; };
R.Schedule = (n, c) => {
  const p = n.props, from = Number(p.from ?? 8), to = Math.max(from + 1, Number(p.to ?? 18)), lanes = arr(p.lanes), cols = Math.max(1, lanes.length), span = to - from, rowH = clamp(p.rowHeight || 46, 24, 120);
  return h("div", { class: "fl-schedule" }, lanes.length ? h("div", { class: "fl-schedule-lanes" }, lanes.map((l) => h("span", null, str(l)))) : null,
    h("div", { class: "fl-schedule-grid", style: { height: span * rowH + "px" } }, Array.from({ length: span + 1 }, (_, i) => h("div", { class: "fl-schedule-hour", style: { top: (i / span) * 100 + "%" } }, h("span", null, `${String(from + i).padStart(2, "0")}:00`))),
      p.now !== undefined ? h("div", { class: "fl-schedule-now", style: { top: clamp((hours(p.now) - from) / span) * 100 + "%" } }) : null,
      h("div", { class: "fl-schedule-items" }, arr(p.items).map((it, i) => { const s = hours(it.start), e = Math.max(s + 0.25, hours(it.end)), lane = clamp(it.lane || 0, 0, cols - 1);
        return h("div", { class: cx("fl-schedule-item", `fl-tone-${it.tone || "brand"}`, (e - s) * rowH < 40 && "is-short"), role: "button", tabindex: 0, key: "i" + i, onclick: () => c.emit(n, "select", { value: i }), style: { top: ((s - from) / span) * 100 + "%", height: ((e - s) / span) * 100 + "%", left: (lane / cols) * 100 + "%", width: 100 / cols + "%" } },
          h("b", null, it.title), h("small", null, `${it.start}–${it.end}` + (it.detail ? ` · ${it.detail}` : ""))); }))));
};
R.Roadmap = (n) => {
  const p = n.props, cols = arr(p.columns), count = Math.max(1, cols.length);
  return h("div", { class: "fl-roadmap", style: { "--fl-cols": count } }, h("div", { class: "fl-roadmap-head" }, h("span", null, p.label || ""), h("div", { class: "fl-roadmap-cols" }, cols.map((cl) => h("span", null, str(cl))))),
    arr(p.rows).map((r) => h("div", { class: "fl-roadmap-row" }, h("div", { class: "fl-roadmap-label" }, r.avatar ? R.Avatar({ props: { name: r.avatar, size: "sm" } }) : null, h("span", null, r.label)),
      h("div", { class: "fl-roadmap-track" }, p.today !== undefined ? h("i", { class: "fl-roadmap-today", style: { left: clamp(Number(p.today) / count) * 100 + "%" } }) : null,
        arr(r.bars).map((b) => h("div", { class: `fl-roadmap-bar fl-tone-${b.tone || "brand"}`, style: { left: clamp(Number(b.start) / count) * 100 + "%", width: clamp((Number(b.end) - Number(b.start)) / count) * 100 + "%" } },
          b.progress !== undefined ? h("i", { style: { width: clamp(Number(b.progress) / 100) * 100 + "%" } }) : null, h("span", null, b.label)))))));
};
