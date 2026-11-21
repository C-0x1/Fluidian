// Fluidian runtime — page-building blocks: themes, marketing sections, commerce, messaging,
// device frames and mobile screens. Like every renderer these are pure (node, ctx) → vnode.
import { h, cx } from "./core.js";
import { R, renderNode, icon, fmt, markdown, fluidianMark } from "./components.js";
import { drawArt, hashOf, oklch } from "./art.js";
import { THEMES } from "./themes.js";

const arr = (v) => (Array.isArray(v) ? v : []);
const str = (v) => (v === null || v === undefined ? "" : String(v));
const kids = (n, c) => arr(n.children).map((k) => renderNode(k, c));
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(v) || 0));
const ratioOf = (r) => (/^\d+:\d+$/.test(r || "") ? r : "4:3").replace(":", " / ");
const go = (c, href) => (e) => { e.preventDefault(); if (href && href !== "#") c.navigate(href); };

/** An Art drawing inside a sized box. */
export const artBox = (spec, uid, cls) => h("div", { class: cx("fl-art", cls), style: { aspectRatio: ratioOf(spec && spec.ratio) } }, drawArt(spec || { kind: "mesh" }, uid));
export const stars = (value, size = 14) => h("span", { class: "fl-stars", role: "img", "aria-label": `${value} out of 5` }, [1, 2, 3, 4, 5].map((i) => h("span", { class: cx("fl-star", Number(value) >= i - 0.25 && "is-on") }, icon("star", size))));
/** Highlight `part` of a heading with the gradient treatment. */
export function accent(text, part) {
  const t = str(text), at = part ? t.indexOf(part) : -1;
  return at < 0 ? t : [t.slice(0, at), h("span", { class: "fl-grad-text" }, part), t.slice(at + part.length)];
}

// Small geometric brand marks, so demo brands and logo walls never borrow a real logo.
const MARKS = {
  orb: [["circle", { cx: 12, cy: 12, r: 9 }], ["circle", { cx: 15.5, cy: 8.5, r: 3.6, class: "cut" }]],
  ring: [["circle", { cx: 12, cy: 12, r: 7, class: "line" }]],
  diamond: [["rect", { x: 5.5, y: 5.5, width: 13, height: 13, rx: 2.5, transform: "rotate(45 12 12)" }]],
  hex: [["path", { d: "M12 2.8l8 4.6v9.2l-8 4.6-8-4.6V7.4z" }]],
  tri: [["path", { d: "M12 3.5l9.5 16.5h-19z" }]],
  bars: [["rect", { x: 3.5, y: 12, width: 4.2, height: 8.5, rx: 1.4 }], ["rect", { x: 9.9, y: 7.5, width: 4.2, height: 13, rx: 1.4 }], ["rect", { x: 16.3, y: 3.5, width: 4.2, height: 17, rx: 1.4 }]],
  wave: [["path", { d: "M3 9c3-4 6-4 9 0s6 4 9 0M3 16c3-4 6-4 9 0s6 4 9 0", class: "line" }]],
  leaf: [["path", { d: "M4 20C4 10 10 4 20 4c0 10-6 16-16 16z" }], ["path", { d: "M4 20L14 10", class: "cutline" }]],
  bolt: [["path", { d: "M13.5 2.5L4.5 13.5h6l-1.2 8 9.2-11.4h-6z" }]],
  star: [["path", { d: "M12 2.5c.8 5 3.5 8 9.5 9.5-6 1.5-8.7 4.5-9.5 9.5-.8-5-3.5-8-9.5-9.5 6-1.5 8.7-4.5 9.5-9.500z" }]],
  half: [["path", { d: "M12 3a9 9 0 0 0 0 18z" }], ["path", { d: "M12 3a9 9 0 0 1 0 18z", class: "soft" }]],
  grid: [["rect", { x: 3.5, y: 3.5, width: 7.5, height: 7.5, rx: 2 }], ["rect", { x: 13, y: 3.5, width: 7.5, height: 7.5, rx: 2, class: "soft" }], ["rect", { x: 3.5, y: 13, width: 7.5, height: 7.5, rx: 2, class: "soft" }], ["rect", { x: 13, y: 13, width: 7.5, height: 7.5, rx: 2 }]],
  arc: [["path", { d: "M4 20V12a8 8 0 0 1 16 0v8h-5v-8a3 3 0 0 0-6 0v8z" }]],
  drop: [["path", { d: "M12 2.800c4 4.5 6.5 7.7 6.5 11a6.500 6.5 0 0 1-13 0c0-3.3 2.5-6.5 6.5-11z" }]],
  slash: [["path", { d: "M5 20L11 4h3L8 20zM12 20l6-16h3l-6 16z" }]],
  dot: [["circle", { cx: 8, cy: 12, r: 5 }], ["circle", { cx: 17, cy: 12, r: 3.5, class: "soft" }]],
};
const MARK_NAMES = Object.keys(MARKS);
export function logoMark(kind, size = 22) {
  if (kind === "fluidian") return fluidianMark(size + 4);   // the framework's own mark, never handed to a demo brand
  const shapes = MARKS[kind] || MARKS[MARK_NAMES[hashOf(kind || "orb") % MARK_NAMES.length]];
  return h("svg", { class: "fl-mark", width: size, height: size, viewBox: "0 0 24 24", "aria-hidden": "true" }, shapes.map(([tag, attrs]) => h(tag, attrs)));
}

// --- theme and page frame ----------------------------------------------------
R.Theme = (n, c) => {
  const p = n.props, name = THEMES[p.preset] ? p.preset : null, style = {};
  for (const t of arr(p.tokens)) if (t && /^--fl-[\w-]+$/.test(t.name) && typeof t.value === "string" && !/[;{}<>]/.test(t.value)) style[t.name] = t.value;
  const scheme = p.scheme === "light" || p.scheme === "dark" ? p.scheme : name ? THEMES[name] : null;
  return h("div", { class: cx("fl-theme", p.fill !== false && "is-fill"), "data-fl-theme": name, "data-scheme": scheme, style }, kids(n, c));
};
R.Landing = (n, c) => h("div", { class: `fl-landing bd-${n.props.backdrop || "none"}` }, h("div", { class: "fl-landing-bg", "aria-hidden": "true" }), kids(n, c));
R.NavBar = (n, c) => {
  const p = n.props;
  return h("header", { class: cx("fl-navbar", p.sticky && "is-sticky", p.glass !== false && "is-glass", `is-${p.variant || "bar"}`) }, h("div", { class: "fl-navbar-in" },
    h("a", { class: "fl-navbar-brand", href: "/", onclick: go(c, p.home || "#") }, logoMark(p.logo || (/^fluidian\b/i.test(str(p.brand)) ? "fluidian" : "orb"), 22), h("span", null, p.brand), p.tag && h("span", { class: "fl-navbar-tag" }, p.tag)),
    h("nav", { class: "fl-navbar-links", "aria-label": "Primary" }, arr(p.links).map((l) => h("a", { class: cx("fl-navbar-link", l.active && "is-active"), href: l.href || "#", onclick: go(c, l.href) }, l.label, l.badge && h("span", { class: "fl-navbar-badge" }, l.badge)))),
    h("div", { class: "fl-navbar-actions" }, kids(n, c))));
};
R.Band = (n, c) => {
  const p = n.props;
  return h("section", { class: `fl-band tone-${p.tone || "plain"} align-${p.align || "center"} width-${p.width || "default"} pad-${p.pad || "md"}` }, h("div", { class: "fl-band-in" },
    (p.title || p.eyebrow || p.subtitle) ? h("header", { class: "fl-band-head" }, p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow), p.title && h("h2", { class: "fl-band-title" }, accent(p.title, p.highlight)), p.subtitle && h("p", { class: "fl-band-sub" }, p.subtitle)) : null,
    h("div", { class: "fl-band-body" }, kids(n, c))));
};
R.Bento = (n, c) => h("div", { class: "fl-bento", style: { "--fl-cols": clamp(n.props.columns || 6, 1, 12), "--fl-row": n.props.rowHeight ? n.props.rowHeight + "px" : null } }, kids(n, c));
R.BentoCell = (n, c) => {
  const p = n.props;
  return h("article", { class: `fl-bento-cell tone-${p.tone || "plain"} pad-${p.padding || "md"}`, style: { gridColumn: `span ${clamp(p.span || 2, 1, 12)}`, gridRow: `span ${clamp(p.rows || 1, 1, 6)}` } },
    (p.title || p.eyebrow || p.icon) ? h("header", { class: "fl-bento-head" }, p.icon && h("span", { class: "fl-bento-icon" }, icon(p.icon, 18)), p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow),
      p.title && h("h3", { class: "fl-bento-title" }, p.title), p.subtitle && h("p", { class: "fl-bento-sub" }, p.subtitle)) : null,
    arr(n.children).length ? h("div", { class: "fl-bento-body" }, kids(n, c)) : null);
};
R.Feature = (n, c) => {
  const p = n.props;
  return h("article", { class: `fl-feature is-${p.variant || "card"} fl-tone-${p.tone || "brand"}` },
    p.number ? h("span", { class: "fl-feature-num" }, str(p.number)) : p.icon ? h("span", { class: "fl-feature-icon" }, icon(p.icon, 20)) : null,
    h("div", { class: "fl-feature-main" }, p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow), h("h3", { class: "fl-feature-title" }, p.title), p.body && h("p", { class: "fl-feature-body" }, p.body), kids(n, c),
      p.link && h("span", { class: "fl-feature-link" }, p.link, icon("arrow-right", 13))));
};
R.LogoCloud = (n) => h("div", { class: `fl-logos is-${n.props.variant || "row"}` }, n.props.label && h("div", { class: "fl-logos-label" }, n.props.label),
  h("div", { class: "fl-logos-row" }, arr(n.props.names).map((name) => h("span", { class: `fl-logo f${hashOf(str(name)) % 5}` }, logoMark(MARK_NAMES[hashOf("m" + name) % MARK_NAMES.length], 20), str(name)))));
R.Metrics = (n) => h("dl", { class: `fl-metrics is-${n.props.variant || "plain"} align-${n.props.align || "center"}`, style: { "--fl-cols": Math.max(1, arr(n.props.items).length) } }, arr(n.props.items).map((it) => h("div", { class: "fl-metric" },
  h("dd", { class: "fl-metric-value" }, str(it.value)), h("dt", { class: "fl-metric-label" }, it.label), it.detail && h("div", { class: "fl-metric-detail" }, it.detail))));
R.Testimonial = (n) => {
  const p = n.props;
  return h("figure", { class: `fl-testimonial is-${p.variant || "card"}` }, p.rating ? stars(p.rating, 14) : null, h("blockquote", { class: "fl-testimonial-quote" }, "“" + str(p.quote) + "”"),
    h("figcaption", { class: "fl-testimonial-by" }, R.Avatar({ props: { name: p.author, size: "md" } }), h("div", null, h("div", { class: "fl-testimonial-name" }, p.author), h("div", { class: "fl-testimonial-role" }, [p.role, p.company].filter(Boolean).join(" · ")))));
};
R.PricingCard = (n, c) => {
  const p = n.props;
  return h("article", { class: cx("fl-price-card", p.featured && "is-featured") }, p.badge && h("span", { class: "fl-price-badge" }, p.badge), h("h3", { class: "fl-price-plan" }, p.plan), p.description && h("p", { class: "fl-price-desc" }, p.description),
    h("div", { class: "fl-price-amount" }, h("span", { class: "fl-price-value" }, str(p.price)), p.period && h("span", { class: "fl-price-period" }, p.period)),
    h("button", { class: cx("fl-btn size-lg is-block", p.featured ? "is-primary" : "is-secondary"), type: "button", onclick: () => c.emit(n, "select", { value: p.plan }) }, p.cta || "Choose plan"),
    h("ul", { class: "fl-price-features" }, arr(p.features).map((f) => { const o = f && typeof f === "object" ? f : { label: f }; return h("li", { class: cx(o.included === false && "is-off") }, icon(o.included === false ? "minus" : "check", 14), h("span", null, str(o.label))); })));
};
R.Comparison = (n) => {
  const p = n.props, plans = arr(p.plans);
  return h("div", { class: "fl-compare" }, h("table", null, h("thead", null, h("tr", null, h("th", null, p.label || ""), plans.map((pl) => h("th", { class: cx(pl.featured && "is-featured"), scope: "col" }, h("div", { class: "fl-compare-plan" }, pl.name), pl.price && h("div", { class: "fl-compare-price" }, pl.price))))),
    h("tbody", null, arr(p.rows).map((r) => r.group ? h("tr", { class: "is-group" }, h("td", { colspan: plans.length + 1 }, r.group)) : h("tr", null, h("th", { scope: "row" }, r.label, r.hint && h("span", { class: "fl-compare-hint" }, r.hint)),
      plans.map((pl, i) => { const v = arr(r.values)[i]; return h("td", { class: cx(pl.featured && "is-featured") }, v === true ? h("span", { class: "fl-compare-yes" }, icon("check", 15)) : v === false || v === null || v === undefined ? h("span", { class: "fl-compare-no" }, "—") : str(v)); }))))));
};
R.FAQ = (n, c) => {
  const st = c.state(n.id, { open: n.props.open === undefined || n.props.open === null ? 0 : Number(n.props.open) });
  return h("div", { class: "fl-faq" }, arr(n.props.items).map((it, i) => h("div", { class: cx("fl-faq-item", st.open === i && "is-open") },
    h("button", { class: "fl-faq-q", type: "button", "aria-expanded": String(st.open === i), onclick: () => c.set(n.id, { open: st.open === i ? -1 : i }) }, h("span", null, it.q), icon(st.open === i ? "minus" : "plus", 16)),
    st.open === i ? h("div", { class: "fl-faq-a" }, it.a) : null)));
};
R.CTA = (n, c) => {
  const p = n.props;
  return h("section", { class: `fl-cta tone-${p.tone || "gradient"} align-${p.align || "center"}` }, p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow), h("h2", { class: "fl-cta-title" }, accent(p.title, p.highlight)),
    p.subtitle && h("p", { class: "fl-cta-sub" }, p.subtitle), h("div", { class: "fl-cta-actions" }, kids(n, c)));
};
R.Footer = (n, c) => {
  const p = n.props;
  return h("footer", { class: "fl-footer" }, h("div", { class: "fl-footer-in" }, h("div", { class: "fl-footer-brand" }, h("div", { class: "fl-navbar-brand" }, logoMark(p.logo || (/^fluidian\b/i.test(str(p.brand)) ? "fluidian" : "orb"), 22), h("span", null, p.brand)), p.tagline && h("p", null, p.tagline),
      arr(p.social).length ? h("div", { class: "fl-footer-social" }, arr(p.social).map((s) => h("span", { class: "fl-iconbtn" }, icon(s, 16)))) : null),
    arr(p.columns).map((col) => h("div", { class: "fl-footer-col" }, h("div", { class: "fl-footer-title" }, col.title), arr(col.links).map((l) => h("a", { class: "fl-footer-link", href: "#", onclick: go(c, "#") }, str(l)))))),
    p.note && h("div", { class: "fl-footer-note" }, p.note));
};
R.PromoTile = (n, c) => {
  const p = n.props;
  return h("section", { class: `fl-promo tone-${p.tone || "light"} size-${p.size || "md"} layout-${p.layout || "stack"} align-${p.align || "center"}` },
    h("div", { class: "fl-promo-copy" }, p.eyebrow && h("div", { class: "fl-eyebrow" }, p.eyebrow), h("h2", { class: "fl-promo-title" }, accent(p.title, p.highlight)), p.subtitle && h("p", { class: "fl-promo-sub" }, p.subtitle),
      arr(n.children).length ? h("div", { class: "fl-promo-actions" }, kids(n, c)) : null),
    p.art ? artBox(p.art, n.id, "fl-promo-art") : null);
};
R.PromptBox = (n, c) => {
  const p = n.props, st = c.state(n.id, { mode: p.mode || arr(p.modes)[0] || "", text: str(p.value) });
  return h("div", { class: "fl-prompt-wrap" }, h("form", { class: "fl-prompt", onsubmit: (e) => { e.preventDefault(); c.emit(n, "submit", { value: st.text }); } },
    h("textarea", { class: "fl-prompt-input", rows: clamp(p.rows || 2, 1, 8), placeholder: p.placeholder || "Describe what you want to build…", "aria-label": p.placeholder || "Prompt", value: st.text, oninput: (e) => { st.text = e.target.value; c.setValue && c.setValue(n, st.text); } }),
    h("div", { class: "fl-prompt-bar" }, h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Attach" }, icon("paperclip", 16)),
      arr(p.modes).length ? h("div", { class: "fl-prompt-modes" }, arr(p.modes).map((m) => h("button", { class: cx("fl-prompt-mode", st.mode === m && "is-active"), type: "button", onclick: () => c.set(n.id, { mode: m }) }, m))) : null,
      p.hint && h("span", { class: "fl-prompt-hint" }, p.hint), h("button", { class: "fl-prompt-send", type: "submit", "aria-label": p.button || "Send" }, p.button ? h("span", null, p.button) : null, icon("arrow-up", 16)))),
    arr(p.chips).length ? h("div", { class: "fl-prompt-chips" }, arr(p.chips).map((ch) => h("button", { class: "fl-chip", type: "button", onclick: () => c.set(n.id, { text: str(ch) }) }, str(ch)))) : null);
};

// --- commerce ------------------------------------------------------------------
R.Art = (n) => h("figure", { class: cx("fl-art", n.props.rounded !== false && "is-rounded", n.props.shadow && "has-shadow"), style: { aspectRatio: ratioOf(n.props.ratio), width: n.props.width ? clamp(n.props.width, 16, 2000) + "px" : null, flex: n.props.width ? "none" : null } },
  drawArt(n.props, n.id), n.props.caption && h("figcaption", null, n.props.caption));
R.ProductCard = (n, c) => {
  const p = n.props;
  return h("article", { class: `fl-product is-${p.variant || "card"}`, onclick: () => c.emit(n, "select", { value: p.name }) },
    h("div", { class: "fl-product-media" }, artBox(p.art || { kind: "box" }, n.id), p.badge && h("span", { class: "fl-product-badge" }, p.badge),
      h("button", { class: "fl-product-fav", type: "button", "aria-label": "Save for later", onclick: (e) => e.stopPropagation() }, icon("heart", 15))),
    h("div", { class: "fl-product-info" }, p.brand && h("div", { class: "fl-product-brand" }, p.brand), h("h3", { class: "fl-product-name" }, p.name), p.detail && h("p", { class: "fl-product-detail" }, p.detail),
      p.rating ? h("div", { class: "fl-product-rating" }, stars(p.rating, 12), h("span", null, str(p.rating) + (p.reviews ? ` (${fmt(p.reviews, "compact")})` : ""))) : null,
      h("div", { class: "fl-product-foot" }, h("span", { class: "fl-product-price" }, str(p.price)), p.compareAt && h("s", { class: "fl-product-was" }, str(p.compareAt)),
        arr(p.swatches).length ? h("span", { class: "fl-product-swatches" }, arr(p.swatches).slice(0, 5).map((col) => h("i", { style: { background: str(col) } }))) : null,
        n.on && n.on.add ? h("button", { class: "fl-product-add", type: "button", "aria-label": `Add ${p.name} to cart`, onclick: (e) => { e.stopPropagation(); c.emit(n, "add", { value: p.name }); } }, icon("plus", 15)) : null)));
};
const qty = (value, change, cls) => h("div", { class: cx("fl-qty", cls) }, h("button", { type: "button", "aria-label": "Decrease", onclick: () => change(value - 1) }, icon("minus", 13)), h("span", { "aria-live": "polite" }, String(value)),
  h("button", { type: "button", "aria-label": "Increase", onclick: () => change(value + 1) }, icon("plus", 13)));
R.Cart = (n, c) => h("ul", { class: "fl-cart" }, arr(n.props.items).map((it, i) => h("li", { class: "fl-cart-line" }, artBox(Object.assign({ kind: "box" }, it.art, { ratio: "1:1" }), n.id + i, "fl-cart-art"),
  h("div", { class: "fl-cart-main" }, h("div", { class: "fl-cart-name" }, it.name), it.variant && h("div", { class: "fl-cart-variant" }, it.variant), it.note && h("div", { class: "fl-cart-note" }, it.note)),
  qty(Number(it.qty) || 1, (v) => c.emit(n, "change", { value: { index: i, qty: Math.max(0, v) } })), h("div", { class: "fl-cart-price" }, str(it.price)))));
R.OrderSummary = (n, c) => {
  const p = n.props;
  return h("div", { class: "fl-summary" }, p.title && h("div", { class: "fl-summary-title" }, p.title), h("dl", null, arr(p.lines).map((l) => h("div", { class: cx("fl-summary-line", l.tone && "tone-" + l.tone) }, h("dt", null, l.label), h("dd", null, str(l.value))))),
    h("div", { class: "fl-summary-total" }, h("span", null, p.totalLabel || "Total"), h("strong", null, str(p.total))), p.note && h("p", { class: "fl-summary-note" }, p.note), kids(n, c));
};
R.Swatches = (n, c) => {
  const p = n.props, opts = arr(p.options).map((o) => (o && typeof o === "object" ? o : { label: str(o) })), st = c.state(n.id, { value: p.value ?? (opts[0] || {}).label });
  return h("div", { class: "fl-field" }, p.label && h("div", { class: "fl-label" }, p.label, h("span", { class: "fl-swatch-current" }, str(st.value))),
    h("div", { class: `fl-swatches is-${p.variant || (opts.some((o) => o.color) ? "color" : "text")}`, role: "radiogroup", "aria-label": p.label || p.name }, h("input", { type: "hidden", name: p.name, value: str(st.value) }), opts.map((o) => h("button", { class: cx("fl-swatch", st.value === o.label && "is-active", o.disabled && "is-off"), type: "button", role: "radio", disabled: !!o.disabled,
      "aria-checked": String(st.value === o.label), "aria-label": o.label, title: o.label, onclick: () => { c.set(n.id, { value: o.label }); c.setValue(n, o.label); c.emit(n, "change", { value: o.label }); } }, o.color ? h("i", { style: { background: str(o.color) } }) : h("span", null, o.label)))));
};
R.Quantity = (n, c) => {
  const p = n.props, st = c.state(n.id, { value: Number(p.value) || 1 }), lo = Number(p.min ?? 1), hi = Number(p.max ?? 99);
  const change = (v) => { v = Math.max(lo, Math.min(hi, v)); c.set(n.id, { value: v }); c.setValue(n, v); c.emit(n, "change", { value: v }); };
  return h("div", { class: "fl-field" }, p.label && h("div", { class: "fl-label" }, p.label), h("input", { type: "hidden", name: p.name, value: st.value }), qty(st.value, change, "is-lg"));
};
R.RatingSummary = (n) => {
  const p = n.props, dist = arr(p.distribution).map((v) => Number(v) || 0), total = dist.reduce((a, b) => a + b, 0) || 1;
  return h("div", { class: "fl-ratings" }, h("div", { class: "fl-ratings-score" }, h("div", { class: "fl-ratings-avg" }, str(p.average)), stars(p.average, 15), h("div", { class: "fl-ratings-count" }, `${fmt(p.count, "number")} reviews`)),
    h("div", { class: "fl-ratings-bars" }, dist.map((v, i) => h("div", { class: "fl-ratings-row" }, h("span", null, String(dist.length - i)), h("div", { class: "fl-ratings-track" }, h("i", { style: { width: (v / total * 100).toFixed(1) + "%" } })), h("span", { class: "fl-ratings-pct" }, Math.round(v / total * 100) + "%")))));
};
R.MediaGallery = (n, c) => {
  const items = arr(n.props.items), st = c.state(n.id, { active: Number(n.props.active) || 0 }), cur = items[Math.min(st.active, items.length - 1)] || { kind: "mesh" };
  return h("div", { class: `fl-mediagallery is-${n.props.layout || "bottom"}` }, artBox(cur, n.id + "m" + st.active, "fl-mediagallery-main"),
    h("div", { class: "fl-mediagallery-thumbs" }, items.map((it, i) => h("button", { class: cx("fl-mediagallery-thumb", i === st.active && "is-active"), type: "button", "aria-label": `Show image ${i + 1}`, onclick: () => c.set(n.id, { active: i }) }, artBox(Object.assign({}, it, { ratio: "1:1" }), n.id + "t" + i)))));
};
R.PinInput = (n, c) => {
  const p = n.props, len = clamp(p.length || 6, 3, 8), st = c.state(n.id, { value: str(p.value).slice(0, len) });
  const commit = (el) => { const cells = [...el.parentNode.querySelectorAll(".fl-pin-cell")], v = cells.map((x) => x.value).join(""); st.value = v; c.setValue(n, v); if (v.length === len) c.emit(n, "complete", { value: v }); };
  return h("div", { class: "fl-field" }, p.label && h("div", { class: "fl-label" }, p.label), h("div", { class: "fl-pin", role: "group", "aria-label": p.label || "Verification code" }, Array.from({ length: len }, (_, i) => h("input", { class: cx("fl-pin-cell", st.value[i] && "is-filled"), key: "c" + i, inputmode: "numeric", maxlength: 1, autocomplete: "one-time-code", value: st.value[i] || "", "aria-label": `Digit ${i + 1}`,
    oninput: (e) => { e.target.value = e.target.value.replace(/\D/g, "").slice(0, 1); if (e.target.value && e.target.nextElementSibling) e.target.nextElementSibling.focus(); commit(e.target); },
    onkeydown: (e) => { if (e.key === "Backspace" && !e.target.value && e.target.previousElementSibling) e.target.previousElementSibling.focus(); } }))), p.help && h("div", { class: "fl-help" }, p.help));
};

// --- messaging and media -----------------------------------------------------------
R.Chat = (n, c) => {
  const p = n.props;
  const message = (m, i) => {
    if (m.from === "system") return h("div", { class: "fl-chat-system", key: "m" + i }, m.text);
    const who = m.from === "me" ? "me" : m.from === "ai" ? "ai" : "them";
    return h("div", { class: `fl-chat-msg from-${who}`, key: "m" + i }, who === "me" || p.avatars === false ? null : who === "ai" ? h("span", { class: "fl-chat-ai" }, icon("sparkles", 14)) : R.Avatar({ props: { name: m.name || p.title || "?", size: "sm" } }),
      h("div", { class: "fl-chat-col" }, m.name && who !== "me" ? h("div", { class: "fl-chat-name" }, m.name) : null,
        m.tool ? h("div", { class: `fl-chat-tool is-${m.tool.status || "done"}` }, icon(m.tool.icon || "terminal", 13), h("span", null, m.tool.label), m.tool.detail && h("code", null, m.tool.detail), h("span", { class: "fl-chat-tool-state" }, m.tool.status === "running" ? h("span", { class: "fl-spinner" }) : icon("check", 12))) : null,
        m.text ? h("div", { class: "fl-chat-bubble" }, m.rich ? markdown(m.text) : str(m.text)) : null, m.art ? artBox(m.art, n.id + "a" + i, "fl-chat-art") : null,
        arr(m.citations).length ? h("div", { class: "fl-chat-cites" }, arr(m.citations).map((ct, k) => h("span", { class: "fl-chat-cite" }, h("b", null, String(k + 1)), str(ct)))) : null,
        arr(m.chips).length ? h("div", { class: "fl-chat-chips" }, arr(m.chips).map((ch) => h("button", { class: "fl-chip", type: "button", onclick: () => c.emit(n, "send", { value: str(ch) }) }, str(ch)))) : null,
        m.time || m.status ? h("div", { class: "fl-chat-meta" }, m.time, m.status === "read" ? icon("check", 11) : null) : null));
  };
  return h("div", { class: `fl-chat is-${p.variant || "bubbles"}` }, p.title ? h("header", { class: "fl-chat-head" }, R.Avatar({ props: { name: p.title, size: "sm", status: p.status } }), h("div", { class: "fl-chat-who" }, h("div", { class: "fl-chat-title" }, p.title), p.subtitle && h("div", { class: "fl-chat-sub" }, p.subtitle)),
      arr(p.actions).map((a) => h("button", { class: "fl-iconbtn", type: "button", "aria-label": a, onclick: () => c.emit(n, "action", { value: a }) }, icon(a, 17)))) : null,
    h("div", { class: "fl-chat-log", role: "log" }, arr(p.messages).map(message), p.typing ? h("div", { class: "fl-chat-msg from-them" }, h("div", { class: "fl-bubble is-typing is-assistant" }, h("i"), h("i"), h("i"))) : null),
    p.composer !== false ? h("form", { class: "fl-chat-form", onsubmit: (e) => { e.preventDefault(); const el = e.target.querySelector("input"); if (el.value.trim()) { c.emit(n, "send", { value: el.value.trim() }); el.value = ""; } } },
      h("button", { class: "fl-iconbtn", type: "button", "aria-label": "Attach" }, icon("plus", 17)), h("input", { class: "fl-chat-input", placeholder: p.placeholder || "Message", "aria-label": p.placeholder || "Message" }),
      h("button", { class: "fl-chat-send", type: "submit", "aria-label": "Send" }, icon("arrow-up", 16))) : null);
};
R.Terminal = (n) => {
  const p = n.props, tabs = arr(p.tabs);
  return h("div", { class: "fl-terminal" }, h("div", { class: "fl-terminal-bar" }, h("span", { class: "fl-device-dots" }, h("i"), h("i"), h("i")),
      tabs.length ? h("div", { class: "fl-terminal-tabs" }, tabs.map((t, i) => h("span", { class: cx("fl-terminal-tab", i === (Number(p.active) || 0) && "is-active") }, str(t)))) : h("span", { class: "fl-terminal-title" }, p.title || "terminal")),
    h("pre", { class: "fl-terminal-body" }, arr(p.lines).map((ln) => { const o = ln && typeof ln === "object" ? ln : { text: str(ln), kind: /^\$ /.test(str(ln)) ? "cmd" : "out" };
      return h("div", { class: `fl-term-line is-${o.kind || "out"}` }, o.kind === "cmd" ? [h("span", { class: "fl-term-prompt" }, p.prompt || "$"), " " + str(o.text).replace(/^\$ /, "")] : str(o.text) || " "); }),
    p.cursor !== false ? h("div", { class: "fl-term-line is-cmd" }, h("span", { class: "fl-term-prompt" }, p.prompt || "$"), " ", h("span", { class: "fl-term-cursor" })) : null));
};
const clock = (sec) => { const s = Math.max(0, Math.round(Number(sec) || 0)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
R.Player = (n, c) => {
  const p = n.props, st = c.state(n.id, { playing: !!p.playing }), pct = clamp((Number(p.progress) || 0) / (Number(p.duration) || 1)), ctl = (name, label) => h("button", { class: "fl-player-btn", type: "button", "aria-label": label, onclick: () => c.emit(n, "control", { value: name }) }, icon(name, 17));
  return h("div", { class: `fl-player is-${p.variant || "card"}` }, artBox(Object.assign({ kind: "cover" }, p.art, { ratio: "1:1" }), n.id, "fl-player-art"),
    h("div", { class: "fl-player-main" }, h("div", { class: "fl-player-title" }, p.title), h("div", { class: "fl-player-artist" }, p.artist),
      h("div", { class: "fl-player-bar" }, h("span", null, clock(p.progress)), h("div", { class: "fl-player-track", role: "progressbar", "aria-valuenow": Math.round(pct * 100), "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Playback position" }, h("i", { style: { width: (pct * 100).toFixed(1) + "%" } })), h("span", null, clock(p.duration))),
      h("div", { class: "fl-player-ctl" }, ctl("shuffle", "Shuffle"), ctl("skip-back", "Previous"), h("button", { class: "fl-player-play", type: "button", "aria-label": st.playing ? "Pause" : "Play", onclick: () => { c.set(n.id, { playing: !st.playing }); c.emit(n, "toggle", { value: !st.playing }); } }, icon(st.playing ? "pause" : "play", 20)),
        ctl("skip-forward", "Next"), ctl("repeat", "Repeat"))));
};
R.AvatarStack = (n) => {
  const names = arr(n.props.names), max = clamp(n.props.max || 4, 1, 12), size = n.props.size || "sm";
  return h("div", { class: "fl-avatars" }, names.slice(0, max).map((nm) => R.Avatar({ props: { name: str(nm), size } })), names.length > max ? h("span", { class: `fl-avatar fl-avatar-more is-${size}` }, "+" + (names.length - max)) : null,
    n.props.label && h("span", { class: "fl-avatars-label" }, n.props.label));
};
R.ControlTile = (n, c) => {
  const p = n.props, st = c.state(n.id, { on: !!p.on });
  return h("button", { class: cx("fl-tile", st.on && "is-on", `fl-tone-${p.tone || "brand"}`), type: "button", "aria-pressed": String(st.on), onclick: () => { c.set(n.id, { on: !st.on }); c.emit(n, "toggle", { value: !st.on }); } },
    h("span", { class: "fl-tile-top" }, h("span", { class: "fl-tile-icon" }, icon(p.icon || "bolt", 18)), h("span", { class: "fl-tile-switch" })), h("span", { class: "fl-tile-title" }, p.title),
    h("span", { class: "fl-tile-value" }, st.on ? str(p.value || "On") : str(p.offValue || "Off")), p.detail && h("span", { class: "fl-tile-detail" }, p.detail));
};

// --- devices and mobile screens ----------------------------------------------------
const statusBar = (platform, time) => h("div", { class: "fl-device-status", "aria-hidden": "true" }, h("span", { class: "fl-device-time" }, time || "9:41"), platform === "ios" ? h("span", { class: "fl-device-island" }) : h("span", { class: "fl-device-camera" }),
  h("span", { class: "fl-device-icons" }, h("svg", { width: 17, height: 11, viewBox: "0 0 17 11" }, [0, 1, 2, 3].map((i) => h("rect", { x: i * 4.4, y: 8 - i * 2.4, width: 3, height: 3 + i * 2.4, rx: 0.8, style: "fill:currentColor" }))),
    h("svg", { width: 16, height: 11, viewBox: "0 0 16 11" }, h("path", { d: "M1 4a10 10 0 0 1 14 0M3.500 6.500a6.500 6.5 0 0 1 9 0M6 9a3 3 0 0 1 4 0", style: "fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round" })),
    h("svg", { width: 25, height: 12, viewBox: "0 0 25 12" }, h("rect", { x: 0.5, y: 0.5, width: 21, height: 11, rx: 3.2, style: "fill:none;stroke:currentColor;opacity:.4" }), h("rect", { x: 2, y: 2, width: 15, height: 8, rx: 1.8, style: "fill:currentColor" }), h("rect", { x: 23, y: 4, width: 1.5, height: 4, rx: 0.7, style: "fill:currentColor;opacity:.45" }))));
R.DeviceFrame = (n, c) => {
  const p = n.props, kind = p.kind || "phone", handheld = kind === "phone" || kind === "tablet", platform = p.platform || (handheld ? "ios" : "web"), name = THEMES[p.theme] ? p.theme : null;
  const screen = h("div", { class: "fl-device-screen", "data-fl-platform": platform, "data-fl-theme": name, "data-scheme": p.scheme === "light" || p.scheme === "dark" ? p.scheme : name ? THEMES[name] : null },
    handheld ? statusBar(platform, p.time) : null, h("div", { class: "fl-device-content" }, kids(n, c)), handheld ? h("div", { class: "fl-device-home", "aria-hidden": "true" }) : null);
  const style = { "--fl-device-w": p.width ? Number(p.width) + "px" : null, "--fl-device-h": p.height ? Number(p.height) + "px" : null, zoom: p.scale && Number(p.scale) !== 1 ? Number(p.scale) : null };
  if (kind === "browser" || kind === "window") {
    const frame = h("div", { class: `fl-device is-${kind}`, style }, h("div", { class: "fl-device-bar" }, h("span", { class: "fl-device-dots" }, h("i"), h("i"), h("i")),
      kind === "browser" ? h("span", { class: "fl-device-url" }, icon("lock", 11), str(p.url || "app.example.com")) : h("span", { class: "fl-device-title" }, str(p.title || ""))), screen);
    return p.caption ? h("figure", { class: "fl-device-fig", style: { width: "100%" } }, frame, h("figcaption", { class: "fl-device-caption" }, p.caption)) : frame;
  }
  const device = kind === "browser" || kind === "window" ? null : h("div", { class: `fl-device is-${kind} platform-${platform}`, style }, screen, kind === "laptop" ? h("div", { class: "fl-device-base", "aria-hidden": "true" }) : null);
  return p.caption ? h("figure", { class: "fl-device-fig" }, device, h("figcaption", { class: "fl-device-caption" }, p.caption)) : device;
};
R.Screen = (n, c) => {
  const p = n.props, tabs = arr(p.tabs), btn = (name) => h("button", { class: "fl-screen-btn", type: "button", "aria-label": name, onclick: () => c.emit(n, "action", { value: name }) }, icon(name, 21));
  return h("div", { class: cx("fl-screen", p.large !== false && "has-large", `tone-${p.tone || "plain"}`) },
    h("header", { class: "fl-screen-bar" }, p.leading ? btn(p.leading) : null, h("div", { class: "fl-screen-titles" }, h("div", { class: "fl-screen-title" }, p.title), p.subtitle && h("div", { class: "fl-screen-sub" }, p.subtitle)),
      h("div", { class: "fl-screen-trailing" }, arr(p.trailing).map((name) => btn(str(name))), p.avatar && R.Avatar({ props: { name: p.avatar, size: "sm" } }))),
    h("div", { class: "fl-screen-body" }, kids(n, c)),
    p.fab ? h("button", { class: cx("fl-fab", p.fab.label && "has-label"), type: "button", "aria-label": p.fab.label || "Add", onclick: () => c.emit(n, "action", { value: "fab" }) }, icon(p.fab.icon || "plus", 22), p.fab.label && h("span", null, p.fab.label)) : null,
    tabs.length ? h("nav", { class: "fl-tabbar", "aria-label": "Sections" }, tabs.map((t) => h("button", { class: cx("fl-tabbar-item", t.active && "is-active"), type: "button", "aria-current": t.active ? "page" : null, onclick: () => (t.route ? c.navigate(t.route) : c.emit(n, "navigate", { value: t.label })) },
      h("span", { class: "fl-tabbar-icon" }, icon(t.icon || "home", 22), t.badge ? h("i", { class: "fl-tabbar-badge" }, str(t.badge)) : null), h("span", { class: "fl-tabbar-label" }, t.label)))) : null);
};
export { oklch };
