"""Colour science used by the design capabilities.

Everything here is deterministic: sRGB/OKLCH conversion, WCAG contrast,
perceptual ramps and contrast repair.  The model proposes intent ("calm
fintech at night"); these functions guarantee the result is legible.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

RGB = Tuple[float, float, float]


def parse_hex(value: str) -> RGB:
    raw = (value or "").strip().lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    if len(raw) == 8:
        raw = raw[:6]
    if len(raw) != 6:
        raise ValueError("not a hex colour: %r" % value)
    try:
        return tuple(int(raw[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        raise ValueError("not a hex colour: %r" % value)


def to_hex(rgb: RGB) -> str:
    return "#" + "".join("%02x" % max(0, min(255, int(round(c * 255)))) for c in rgb)


def is_hex(value: object) -> bool:
    try:
        parse_hex(str(value))
        return isinstance(value, str) and value.strip().startswith("#")
    except ValueError:
        return False


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def luminance(rgb: RGB) -> float:
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = luminance(parse_hex(a)), luminance(parse_hex(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def rgb_to_oklch(rgb: RGB) -> Tuple[float, float, float]:
    r, g, b = (_lin(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(A, B), math.degrees(math.atan2(B, A)) % 360


def _oklch_to_rgb_raw(L: float, C: float, H: float) -> RGB:
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return r, g, bb


def oklch_to_rgb(L: float, C: float, H: float) -> RGB:
    """Convert to sRGB, reducing chroma until the colour is inside the gamut."""
    L = max(0.0, min(1.0, L))
    lo, hi = 0.0, max(0.0, C)
    best = _oklch_to_rgb_raw(L, 0.0, H)
    for _ in range(18):
        mid = (lo + hi) / 2
        cand = _oklch_to_rgb_raw(L, mid, H)
        if all(-0.0005 <= c <= 1.0005 for c in cand):
            best, lo = cand, mid
        else:
            hi = mid
    full = _oklch_to_rgb_raw(L, C, H)
    if all(-0.0005 <= c <= 1.0005 for c in full):
        best = full
    return tuple(max(0.0, min(1.0, _gam(max(0.0, c)))) for c in best)  # type: ignore[return-value]


def oklch(L: float, C: float, H: float) -> str:
    return to_hex(oklch_to_rgb(L, C, H))


RAMP_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
_RAMP_L = [0.975, 0.945, 0.895, 0.825, 0.735, 0.645, 0.565, 0.475, 0.395, 0.315, 0.235]
_RAMP_C = [0.12, 0.25, 0.45, 0.70, 0.92, 1.00, 0.98, 0.88, 0.74, 0.60, 0.46]


def ramp(seed: str) -> Dict[int, str]:
    """A perceptually even 11-step ramp through the seed's hue."""
    _, chroma, hue = rgb_to_oklch(parse_hex(seed))
    chroma = max(chroma, 0.02)
    return {step: oklch(l, chroma * c, hue) for step, l, c in zip(RAMP_STEPS, _RAMP_L, _RAMP_C)}


def heal_contrast(fg: str, bg: str, target: float = 4.5) -> Tuple[str, float, int]:
    """Move ``fg`` along its lightness axis until it reaches ``target`` against ``bg``.

    Returns ``(colour, ratio, steps)``; hue and chroma are preserved as far as
    the gamut allows, so the brand colour stays recognisable.
    """
    current = contrast(fg, bg)
    if current >= target:
        return to_hex(parse_hex(fg)), current, 0
    L, C, H = rgb_to_oklch(parse_hex(fg))
    darker_bg = luminance(parse_hex(bg)) < 0.4
    best, best_ratio, steps = fg, current, 0
    for i in range(1, 101):
        steps = i
        Lc = min(1.0, L + i * 0.01) if darker_bg else max(0.0, L - i * 0.01)
        cand = oklch(Lc, C, H)
        ratio = contrast(cand, bg)
        if ratio > best_ratio:
            best, best_ratio = cand, ratio
        if ratio >= target or Lc in (0.0, 1.0):
            break
    if best_ratio < target:
        extreme = "#ffffff" if darker_bg else "#000000"
        return extreme, contrast(extreme, bg), steps
    return best, best_ratio, steps


def on_colour(bg: str) -> str:
    """Readable text colour for a filled surface."""
    return "#ffffff" if contrast("#ffffff", bg) >= contrast("#0b1220", bg) else "#0b1220"


def mix(a: str, b: str, t: float) -> str:
    ra, rb = parse_hex(a), parse_hex(b)
    return to_hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))  # type: ignore[arg-type]


def theme_tokens(brand: str, accent: str = "", dark: bool = False, radius: int = 12,
                 neutral_chroma: float = 0.012, neutral_hue: Optional[float] = None, depth: Optional[float] = None,
                 ai: Optional[Tuple[str, str, str]] = None, mono: bool = False) -> List[Dict[str, str]]:
    """Derive the full ``--fl-*`` token set from a brand colour.

    ``neutral_hue`` and ``neutral_chroma`` tint the greys, ``depth`` sets the
    lightness of the page background, ``ai`` pins the three gradient stops and
    ``mono`` makes the brand a pure ink (black on light, white on dark).
    Text/surface pairs are verified against WCAG AA and repaired when needed.
    """
    _, chroma, hue = rgb_to_oklch(parse_hex(brand))
    scale = ramp(brand)
    accent = accent or oklch(0.72, max(chroma, 0.12), (hue + 150) % 360)
    nh = hue if neutral_hue is None else neutral_hue
    n = lambda l: oklch(max(0.0, min(1.0, l)), neutral_chroma, nh)  # noqa: E731 - tinted neutral
    if dark:
        base = 0.165 if depth is None else depth
        bg, surface, surface2, surface3 = n(base), n(base + 0.04), n(base + 0.08), n(base + 0.125)
        border, border2 = n(base + 0.145), n(base + 0.235)
        text, text2, text3 = n(0.96), n(0.78), n(0.62)
        primary, primary2 = scale[400], scale[300]
        soft, soft_text = mix(bg, scale[500], 0.22), scale[200]
    else:
        base = 0.985 if depth is None else depth
        bg, surface, surface2, surface3 = n(base), ("#ffffff" if depth is None else n(min(1.0, base + 0.022))), n(base - 0.013), n(base - 0.04)
        border, border2 = n(base - 0.07), n(base - 0.145)
        text, text2, text3 = n(0.21), n(0.42), n(0.56)
        primary, primary2 = scale[600], scale[700]
        soft, soft_text = scale[50], scale[700]
    if mono:
        primary, primary2 = (n(0.97), n(0.86)) if dark else (n(0.17), n(0.30))
        soft, soft_text = surface3, text
    primary = heal_contrast(primary, surface, 4.5)[0]
    text2 = heal_contrast(text2, surface, 4.5)[0]
    text3 = heal_contrast(text3, surface, 3.0)[0]
    soft_text = heal_contrast(soft_text, soft, 4.5)[0]
    status = {
        "success": oklch(0.62 if not dark else 0.76, 0.15, 155),
        "warning": oklch(0.70 if not dark else 0.82, 0.15, 75),
        "danger": oklch(0.60 if not dark else 0.72, 0.19, 25),
        "info": oklch(0.62 if not dark else 0.76, 0.13, 240),
    }
    if ai:
        ai_a, ai_b, ai_c = ai
    else:
        ai_a = oklch(0.66 if not dark else 0.74, 0.19, (hue + 40) % 360)
        ai_b = oklch(0.72 if not dark else 0.80, 0.14, (hue - 35) % 360)
        ai_c = oklch(0.76 if not dark else 0.82, 0.13, (hue - 85) % 360)
    tokens = [
        ("bg", bg), ("surface", surface), ("surface-2", surface2), ("surface-3", surface3),
        ("border", border), ("border-strong", border2),
        ("text", text), ("text-2", text2), ("text-3", text3),
        ("brand", primary), ("brand-2", primary2), ("brand-soft", soft), ("brand-text", soft_text),
        ("on-brand", on_colour(primary)),
        ("ai-a", ai_a), ("ai-b", ai_b), ("ai-c", ai_c),
        ("accent", accent),
        ("ai-soft", mix(surface, ai_a, 0.10 if not dark else 0.20)),
    ]
    for name, colour in status.items():
        fixed = heal_contrast(colour, surface, 3.0)[0]
        tokens.append((name, fixed))
        tokens.append((name + "-soft", mix(surface, fixed, 0.12 if not dark else 0.22)))
    tokens.append(("radius", "%dpx" % radius))
    tokens.append(("scheme", "dark" if dark else "light"))
    return [{"name": "--fl-" + k, "value": v} for k, v in tokens]


# --- theme presets -----------------------------------------------------------
# Every preset is a seed for theme_tokens plus a type pairing.  `tools/build_tokens.py`
# turns this table into runtime/themes.css; the `Theme` component applies a preset to
# any subtree, and `fluidian tokens` exports one for other platforms.
FONTS = {
    "sans": 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    "grotesk": '"Space Grotesk", Inter, ui-sans-serif, system-ui, sans-serif',
    "serif": '"Instrument Serif", "Iowan Old Style", "Palatino Linotype", Georgia, serif',
    "mono": '"JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace',
}
# display face → (weight, letter-spacing, size scale, style of accented words)
DISPLAY = {"sans": ("680", "-0.035em", "1", "normal"), "grotesk": ("600", "-0.035em", "1", "normal"),
           "serif": ("400", "-0.02em", "1.16", "italic"), "mono": ("600", "-0.04em", "0.9", "normal")}

# Fluidian's own colours, the Deep Blue palette: the logo, the wordmark and the default theme come from these.
# They are the identity of the framework only. Applications choose any preset below, or their own.
BRAND = {"blue": "#0000ff", "navy": "#000c66", "sky": "#7ec8e3", "midnight": "#050a30", "white": "#ffffff"}

THEMES: Dict[str, Dict[str, object]] = {
    "deep": dict(label="Deep Blue", brand=BRAND["blue"], accent=BRAND["sky"], radius=14, neutral_hue=268, neutral_chroma=0.012,
                 ai=(BRAND["blue"], "#3d7bff", BRAND["sky"])),
    "iris": dict(label="Iris", brand="#7b3bff", accent="#ff3a7c", radius=14, neutral_hue=292, neutral_chroma=0.010, ai=("#7b3bff", "#ff3a7c", "#ffb23e")),
    "midnight": dict(label="Midnight", brand="#4f8cff", accent="#22d3ee", dark=True, radius=14, depth=0.155, neutral_hue=262, neutral_chroma=0.022,
                     ai=("#818cf8", "#38bdf8", "#2dd4bf")),
    "aurora": dict(label="Aurora", brand="#a78bfa", accent="#34d399", dark=True, radius=18, depth=0.15, neutral_hue=285, neutral_chroma=0.02,
                   ai=("#c084fc", "#60a5fa", "#34d399"), display="grotesk"),
    "sunset": dict(label="Sunset", brand="#ee5a2a", accent="#ff3d81", radius=16, neutral_hue=55, neutral_chroma=0.012, ai=("#ff7a45", "#ff3d81", "#ffb347"),
                   display="grotesk"),
    "ember": dict(label="Ember", brand="#ff7a45", accent="#ffc145", dark=True, radius=16, depth=0.15, neutral_hue=45, neutral_chroma=0.012,
                  ai=("#ff7a45", "#ff4d6d", "#ffc145"), display="grotesk"),
    "ocean": dict(label="Ocean", brand="#0b7fd1", accent="#14b8a6", radius=12, neutral_hue=235, neutral_chroma=0.014, ai=("#0ea5e9", "#22d3ee", "#34d399")),
    "forest": dict(label="Forest", brand="#1f7a4f", accent="#d97706", radius=10, depth=0.972, neutral_hue=95, neutral_chroma=0.016,
                   ai=("#1f9d63", "#84cc16", "#eab308"), display="serif"),
    "moss": dict(label="Moss", brand="#a3e635", accent="#facc15", dark=True, radius=14, depth=0.16, neutral_hue=145, neutral_chroma=0.022,
                 ai=("#a3e635", "#34d399", "#22d3ee"), display="grotesk"),
    "rose": dict(label="Rose", brand="#e11d74", accent="#7c3aed", radius=18, neutral_hue=350, neutral_chroma=0.012, ai=("#f43f8e", "#a855f7", "#fb923c")),
    "grape": dict(label="Grape", brand="#c084fc", accent="#f472b6", dark=True, radius=18, depth=0.15, neutral_hue=305, neutral_chroma=0.035,
                  ai=("#c084fc", "#f472b6", "#818cf8"), display="grotesk"),
    "citrus": dict(label="Citrus", brand="#5c9a0f", accent="#f59e0b", radius=16, depth=0.982, neutral_hue=110, neutral_chroma=0.014,
                   ai=("#84cc16", "#facc15", "#fb923c"), display="grotesk"),
    "sand": dict(label="Sand", brand="#2a2118", accent="#c2410c", radius=4, depth=0.955, neutral_hue=80, neutral_chroma=0.02, mono=True,
                 ai=("#c2410c", "#d97706", "#a16207"), display="serif"),
    "graphite": dict(label="Graphite", brand="#fafafa", accent="#7dd3fc", dark=True, radius=8, depth=0.13, neutral_hue=260, neutral_chroma=0.004, mono=True,
                     ai=("#f4f4f5", "#a1a1aa", "#7dd3fc")),
    "paper": dict(label="Paper", brand="#111111", accent="#2563eb", radius=8, neutral_hue=260, neutral_chroma=0.003, mono=True,
                  ai=("#111827", "#6b7280", "#2563eb")),
    "terminal": dict(label="Terminal", brand="#39ff88", accent="#ffd166", dark=True, radius=3, depth=0.09, neutral_hue=150, neutral_chroma=0.01,
                     ai=("#39ff88", "#22d3ee", "#ffd166"), display="mono", body="mono"),
    "crimson": dict(label="Crimson", brand="#ff3b5c", accent="#ffb020", dark=True, radius=4, depth=0.1, neutral_hue=15, neutral_chroma=0.01,
                    ai=("#ff3b5c", "#ff7a45", "#ffb020"), display="mono"),
    "candy": dict(label="Candy", brand="#7c5cff", accent="#ff7ac6", radius=22, depth=0.978, neutral_hue=295, neutral_chroma=0.02,
                  ai=("#7c5cff", "#ff7ac6", "#ffc46b"), display="grotesk"),
    "mint": dict(label="Mint", brand="#0d9f92", accent="#f472b6", radius=18, neutral_hue=180, neutral_chroma=0.012, ai=("#14b8a6", "#38bdf8", "#a3e635")),
    "gold": dict(label="Gold", brand="#d4af6a", accent="#e8d5a8", dark=True, radius=4, depth=0.12, neutral_hue=75, neutral_chroma=0.008,
                 ai=("#d4af6a", "#f1dca7", "#a67c37"), display="serif"),
    "sky": dict(label="Sky", brand="#0c8ce9", accent="#6366f1", radius=16, depth=0.984, neutral_hue=230, neutral_chroma=0.016, ai=("#38bdf8", "#818cf8", "#f0abfc")),
    "abyss": dict(label="Abyss", brand="#3355ff", accent=BRAND["sky"], dark=True, radius=14, depth=0.17, neutral_hue=270, neutral_chroma=0.075,
                  ai=("#3d5cff", BRAND["sky"], "#b6f0ff")),
    "emerald": dict(label="Emerald", brand="#00a862", accent="#ffc21a", radius=16, depth=0.984, neutral_hue=160, neutral_chroma=0.014,
                    ai=("#00c978", "#00d4c8", "#c6f432"), display="grotesk"),
    "neon": dict(label="Neon", brand="#ff2bd6", accent="#00f0ff", dark=True, radius=12, depth=0.085, neutral_hue=300, neutral_chroma=0.006,
                 ai=("#ff2bd6", "#7a5cff", "#00f0ff"), display="grotesk"),
    "ruby": dict(label="Ruby", brand="#e0142f", accent="#ff9f1c", radius=10, neutral_hue=20, neutral_chroma=0.010, ai=("#ff2d46", "#ff7a1a", "#ffc531")),
    "lagoon": dict(label="Lagoon", brand="#14e0c3", accent="#ffd23f", dark=True, radius=18, depth=0.16, neutral_hue=205, neutral_chroma=0.045,
                   ai=("#14e0c3", "#38a8ff", "#ffd23f"), display="grotesk"),
    "tangerine": dict(label="Tangerine", brand="#ff6a00", accent="#7a2bff", radius=20, depth=0.985, neutral_hue=60, neutral_chroma=0.012,
                      ai=("#ff6a00", "#ff2d7a", "#ffc400"), display="grotesk"),
}
DEFAULT_THEME = "deep"
DEFAULT_DARK = dict(brand="#3355ff", accent=BRAND["sky"], dark=True, radius=14, depth=0.17, neutral_hue=270, neutral_chroma=0.075, ai=("#3d5cff", BRAND["sky"], "#b6f0ff"))

_SHADOWS = {
    False: ("0 1px 2px rgba(16, 24, 40, 0.05)",
            "0 1px 2px rgba(16, 24, 40, 0.04), 0 8px 22px -10px rgba(16, 24, 40, 0.14)",
            "0 4px 10px rgba(16, 24, 40, 0.05), 0 28px 56px -18px rgba(16, 24, 40, 0.24)"),
    True: ("0 1px 2px rgba(0, 0, 0, 0.4)",
           "0 2px 4px rgba(0, 0, 0, 0.3), 0 12px 28px -10px rgba(0, 0, 0, 0.6)",
           "0 28px 64px -14px rgba(0, 0, 0, 0.8)"),
}


def preset_tokens(spec: Dict[str, object]) -> List[Dict[str, str]]:
    """The complete token list for a preset: colours plus type, depth and gradient stops."""
    keys = ("accent", "dark", "radius", "neutral_chroma", "neutral_hue", "depth", "ai", "mono")
    tokens = theme_tokens(str(spec["brand"]), **{k: spec[k] for k in keys if k in spec})  # type: ignore[arg-type]
    dark = bool(spec.get("dark"))
    display, body = str(spec.get("display") or "sans"), str(spec.get("body") or "sans")
    weight, tracking, scale, accent_style = DISPLAY[display]
    extra = [("font", FONTS[body]), ("font-display", FONTS[display]), ("display-weight", weight), ("display-tracking", tracking),
             ("display-scale", scale), ("display-accent", accent_style),
             ("shadow-1", _SHADOWS[dark][0]), ("shadow-2", _SHADOWS[dark][1]), ("shadow-3", _SHADOWS[dark][2]),
             ("inset", "inset 0 1px 0 rgba(255, 255, 255, %s)" % ("0.06" if dark else "0.8"))]
    return tokens + [{"name": "--fl-" + k, "value": v} for k, v in extra]


def theme_names() -> List[str]:
    return list(THEMES)


def theme_css(selector: str, spec: Dict[str, object]) -> str:
    tokens = preset_tokens(spec)
    scheme = next(t["value"] for t in tokens if t["name"] == "--fl-scheme")
    body = "\n".join("  %s: %s;" % (t["name"], t["value"]) for t in tokens if t["name"] != "--fl-scheme")
    return "%s {\n%s\n  color-scheme: %s;\n}\n" % (selector, body, scheme)
