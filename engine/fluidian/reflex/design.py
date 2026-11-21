"""Reflex design intelligence: themes, palettes, icons, motion, illustration."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional

from .. import colors as K
from . import text as T

HUES = {"ocean": 215, "sea": 200, "water": 205, "fluid": 212, "sky": 220, "ice": 200, "mint": 165, "forest": 150,
        "nature": 140, "eco": 140, "garden": 135, "health": 165, "medical": 195, "clinic": 195, "finance": 225,
        "fintech": 232, "bank": 222, "trust": 220, "corporate": 218, "enterprise": 224, "legal": 235, "luxury": 285,
        "royal": 275, "creative": 300, "playful": 330, "kids": 35, "candy": 335, "love": 352, "energy": 28,
        "sunset": 30, "fire": 18, "food": 32, "coffee": 48, "warm": 38, "gold": 85, "sun": 90, "earth": 62,
        "night": 255, "midnight": 258, "space": 268, "cyber": 185, "neon": 315, "retro": 35, "calm": 205, "zen": 172,
        "sport": 12, "alert": 8, "berry": 342, "lavender": 292, "coral": 24, "teal": 188, "indigo": 268,
        "emerald": 156, "rose": 356, "amber": 72, "slate": 232, "crimson": 14, "violet": 296, "plum": 322,
        "blue": 250, "green": 148, "red": 22, "orange": 50, "yellow": 95, "purple": 300, "pink": 345, "cyan": 200,
        "travel": 208, "music": 310, "education": 245, "school": 245, "security": 228, "developer": 262,
        "terminal": 150, "wellness": 168, "beauty": 345, "gaming": 290, "logistics": 40, "energy drink": 130}
_DARK = {"night", "midnight", "dark", "space", "cyber", "neon", "noir", "terminal", "cinema", "gaming", "stealth", "console"}
_VIVID = {"vivid", "playful", "neon", "energy", "bold", "loud", "kids", "candy", "sport", "gaming", "bright"}
_CALM = {"calm", "zen", "minimal", "muted", "corporate", "serious", "quiet", "soft", "neutral", "subtle", "legal"}
_ROUND = {"playful", "friendly", "soft", "round", "kids", "bubbly", "warm", "wellness", "candy"}
_SHARP = {"sharp", "brutal", "brutalist", "corporate", "terminal", "serious", "legal", "technical", "console", "precise"}

ICONS: Dict[str, str] = {
    "home": "home house dashboard overview start main", "inbox": "inbox tray empty messages received orders",
    "calendar": "calendar date schedule event meeting day due", "sparkles": "ai magic generate smart insight suggest assistant",
    "check": "check done complete success confirm approve save yes", "plus": "add new create plus more insert",
    "x": "close remove cancel dismiss no clear", "search": "search find lookup query explore",
    "settings": "settings preferences configure options gear admin", "user": "user profile account person me contact",
    "users": "users team people members group customers audience", "bell": "notification alert remind bell reminder",
    "chart": "chart analytics report statistics metrics graph bar", "trend-up": "growth increase up rising trend revenue gain",
    "trend-down": "decline decrease down falling loss churn drop", "clock": "time clock history recent pending wait duration",
    "mail": "email mail message envelope newsletter send inbox", "phone": "phone call telephone mobile contact support",
    "link": "link url chain connect integration attach", "lock": "lock secure password private security login",
    "shield": "shield protect safety trust privacy compliance guard", "alert": "warning alert error caution risk danger problem",
    "info": "info information about details note", "help": "help question support faq guide docs",
    "star": "star favorite rating featured important", "heart": "heart like love favorite health wellbeing",
    "file": "file document page invoice report contract pdf", "folder": "folder directory project collection files",
    "image": "image photo picture gallery media", "download": "download export save get pull",
    "upload": "upload import attach push share", "edit": "edit pencil write rename modify update",
    "trash": "delete trash remove discard bin", "copy": "copy duplicate clone clipboard",
    "send": "send submit publish deliver share paper plane", "mic": "microphone voice dictate speak record audio",
    "play": "play start run video launch", "bolt": "bolt fast automation trigger energy quick action zap",
    "globe": "globe world language web international locale", "card": "card payment billing credit checkout subscription",
    "cart": "cart shop store basket purchase buy order", "tag": "tag label price category discount",
    "filter": "filter refine funnel segment", "menu": "menu navigation hamburger list",
    "chevron-right": "next forward expand open", "chevron-down": "dropdown collapse expand more",
    "arrow-right": "arrow next continue go proceed", "arrow-left": "back previous return",
    "eye": "view preview visible watch show", "wand": "wand magic rewrite transform auto fix",
    "cpu": "model chip compute ai engine processor", "layers": "layers stack design system components",
    "grid": "grid layout tiles gallery apps", "list": "list rows items tasks todo",
    "message": "chat comment message conversation feedback reply", "flag": "flag report milestone priority goal",
    "refresh": "refresh reload sync retry update regenerate", "external": "external open new window launch",
    "moon": "dark night moon theme", "sun": "light day sun brightness theme", "droplet": "fluid water droplet color brand",
    "command": "command shortcut keyboard palette", "terminal": "terminal console cli code shell",
    "database": "database data storage records table", "key": "key api access credential secret token",
    "pin": "location map pin address place", "gift": "gift reward offer bonus referral",
    "truck": "shipping delivery truck logistics freight", "box": "box package product inventory archive",
    "palette": "palette colors theme design brand style", "volume": "volume sound speaker audio read aloud",
    "code": "code developer source snippet api", "branch": "branch version git workflow fork",
    "dollar": "money dollar price revenue finance cost", "logout": "logout sign out exit leave", "more": "more options ellipsis overflow",
}

_EMOJI = {"success": "✅", "done": "✅", "celebrate": "🎉", "launch": "🚀", "ship": "🚀", "fast": "⚡", "idea": "💡",
          "warning": "⚠️", "error": "⛔", "bug": "🐞", "money": "💰", "revenue": "📈", "growth": "📈", "decline": "📉",
          "calendar": "📅", "meeting": "📅", "time": "⏱️", "mail": "✉️", "message": "💬", "chat": "💬", "search": "🔎",
          "lock": "🔒", "security": "🛡️", "team": "👥", "user": "👤", "document": "📄", "folder": "📁", "idea2": "💡",
          "settings": "⚙️", "delete": "🗑️", "edit": "✏️", "love": "❤️", "star": "⭐", "home": "🏠", "travel": "✈️",
          "food": "🍽️", "coffee": "☕", "music": "🎵", "photo": "📷", "gift": "🎁", "shipping": "🚚", "data": "🗄️",
          "ai": "✨", "magic": "✨", "question": "❓", "welcome": "👋", "thanks": "🙏", "focus": "🎯", "goal": "🎯"}


def _hash(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def theme_from_prompt(prompt: str) -> Dict[str, Any]:
    """Derive brand intent (hue, mood, radius, density) from a description."""
    p = (prompt or "").lower()
    tokens = set(T.words(p))
    hexes = re.findall(r"#[0-9a-f]{6}\b|#[0-9a-f]{3}\b", p)
    hits = [(p.find(k), k) for k in HUES if re.search(r"\b%s\b" % re.escape(k), p)]
    hits.sort()
    chroma = 0.22 if tokens & _VIVID else (0.10 if tokens & _CALM else 0.16)
    dark = bool(tokens & _DARK)
    if hexes:
        brand = K.to_hex(K.parse_hex(hexes[0]))
        hue = K.rgb_to_oklch(K.parse_hex(brand))[2]
        basis = "the colour you specified"
    else:
        hue = float(HUES[hits[0][1]]) if hits else float(_hash(p or "fluidian") % 360)
        brand = K.oklch(0.58, chroma, hue)
        basis = ("“%s”" % hits[0][1]) if hits else "a hue derived from the description"
    accent_hue = float(HUES[hits[1][1]]) if len(hits) > 1 else (hue + 150) % 360
    accent = K.to_hex(K.parse_hex(hexes[1])) if len(hexes) > 1 else K.oklch(0.72, max(chroma, 0.13), accent_hue)
    radius = 18 if tokens & _ROUND else (4 if tokens & _SHARP else 12)
    font = "mono" if tokens & {"terminal", "developer", "console", "code"} else (
        "serif" if tokens & {"luxury", "editorial", "legal", "classic", "magazine"} else (
            "rounded" if tokens & _ROUND else "sans"))
    density = "compact" if tokens & {"dense", "compact", "data", "trading", "terminal", "console"} else (
        "spacious" if tokens & {"spacious", "airy", "luxury", "editorial", "calm", "zen"} else "comfortable")
    name = T.title_case(" ".join(T.keywords(prompt, 2)) or "Custom") + (" Night" if dark else "")
    return {"name": name, "brand": brand, "accent": accent, "dark": dark, "radius": radius, "font": font,
            "density": density,
            "rationale": "Built around %s with %s chroma, %s corners and a %s scheme." % (
                basis, "high" if chroma > 0.2 else ("low" if chroma < 0.12 else "balanced"),
                "soft" if radius > 14 else ("crisp" if radius < 8 else "moderate"), "dark" if dark else "light")}


FONT_STACKS = {
    "sans": "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    "serif": "ui-serif, 'Iowan Old Style', 'Palatino Linotype', Georgia, 'Times New Roman', serif",
    "mono": "'JetBrains Mono', ui-monospace, 'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace",
    "rounded": "ui-rounded, 'SF Pro Rounded', 'Nunito', 'Hiragino Maru Gothic ProN', Inter, system-ui, sans-serif",
}
DENSITY = {"compact": "0.85", "comfortable": "1", "spacious": "1.18"}


def expand_theme(intent: Dict[str, Any]) -> List[Dict[str, str]]:
    """Turn brand intent into the full, contrast-checked ``--fl-*`` token list."""
    brand = intent.get("brand") if K.is_hex(intent.get("brand")) else "#2f6bff"
    accent = intent.get("accent") if K.is_hex(intent.get("accent")) else ""
    try:
        radius = int(intent.get("radius", 12))
    except (TypeError, ValueError):
        radius = 12
    tokens = K.theme_tokens(brand, accent, bool(intent.get("dark")), max(0, min(28, radius)))
    tokens.append({"name": "--fl-font", "value": FONT_STACKS.get(str(intent.get("font")), FONT_STACKS["sans"])})
    tokens.append({"name": "--fl-density", "value": DENSITY.get(str(intent.get("density")), "1")})
    return tokens


def harmonies(seed: str) -> Dict[str, Any]:
    L, C, H = K.rgb_to_oklch(K.parse_hex(seed))
    ramp = K.ramp(seed)
    return {"ramp": [{"step": str(step), "value": value} for step, value in ramp.items()],
            "complementary": K.oklch(L, C, (H + 180) % 360),
            "analogous": [K.oklch(L, C, (H - 30) % 360), K.oklch(L, C, (H + 30) % 360)],
            "triadic": [K.oklch(L, C, (H + 120) % 360), K.oklch(L, C, (H + 240) % 360)],
            "neutral": K.oklch(0.55, 0.012, H)}


def heal_pairs(pairs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for pair in pairs:
        fg, bg = str(pair.get("fg", "")), str(pair.get("bg", ""))
        target = float(pair.get("target") or 4.5)
        if not (K.is_hex(fg) and K.is_hex(bg)):
            out.append({"name": str(pair.get("name", "")), "fg": fg, "bg": bg, "ratio": 0.0, "fixed": fg, "fixedRatio": 0.0,
                        "passes": False, "note": "Not a hex colour pair."})
            continue
        before = K.contrast(fg, bg)
        fixed, after, _ = K.heal_contrast(fg, bg, target)
        out.append({"name": str(pair.get("name", "")), "fg": fg, "bg": bg, "ratio": round(before, 2), "fixed": fixed,
                    "fixedRatio": round(after, 2), "passes": before >= target,
                    "note": "Already meets %.1f:1." % target if before >= target else
                            "Raised from %.2f:1 to %.2f:1 by shifting lightness; hue preserved." % (before, after)})
    return out


def match_icon(text: str, k: int = 3) -> List[Dict[str, Any]]:
    """Rank icons by overlap between the text and each icon's concept keywords."""
    ws = set(T.words(text)) - T.STOP
    stems = {w.rstrip("s") for w in ws} | ws
    scored = []
    for name, concepts in ICONS.items():
        cw = set(concepts.split()) | {name.replace("-", " ")} | set(name.split("-"))
        score = len(stems & cw) + (0.5 if any(c.startswith(w[:4]) for w in stems if len(w) > 3 for c in cw) else 0)
        if score:
            scored.append((score, name))
    scored.sort(key=lambda t: (-t[0], t[1]))
    top = scored[:k] or [(0.1, "sparkles")]
    best = top[0][0] or 1
    return [{"label": name, "value": name, "icon": name, "score": round(min(1.0, s / max(best, 2)), 2)} for s, name in top]


def match_emoji(text: str, k: int = 3) -> List[Dict[str, Any]]:
    ws = [w.rstrip("s") for w in T.words(text)]
    out, seen = [], set()
    for w in ws:
        for key, emoji in _EMOJI.items():
            if (w == key.rstrip("2") or (len(w) > 4 and key.startswith(w[:5]))) and emoji not in seen:
                seen.add(emoji)
                out.append({"label": emoji, "value": emoji, "detail": key.rstrip("2"), "score": 0.8})
    return out[:k] or [{"label": "✨", "value": "✨", "detail": "default", "score": 0.3}]


TYPE_PAIRS = [
    {"mood": "product", "heading": FONT_STACKS["sans"], "body": FONT_STACKS["sans"], "scale": 1.2,
     "why": "One humanist sans at two weights keeps dense product UI calm and consistent."},
    {"mood": "editorial", "heading": FONT_STACKS["serif"], "body": FONT_STACKS["sans"], "scale": 1.333,
     "why": "A serif display face adds authority; a sans body keeps long text effortless."},
    {"mood": "technical", "heading": FONT_STACKS["mono"], "body": FONT_STACKS["sans"], "scale": 1.125,
     "why": "Monospaced headings signal precision; the tight scale suits data-heavy screens."},
    {"mood": "friendly", "heading": FONT_STACKS["rounded"], "body": FONT_STACKS["sans"], "scale": 1.25,
     "why": "Rounded display forms feel approachable without hurting body legibility."},
]


def type_pair(mood: str) -> Dict[str, Any]:
    m = set(T.words(mood))
    if m & {"editorial", "luxury", "magazine", "classic", "legal", "story"}:
        return TYPE_PAIRS[1]
    if m & {"technical", "developer", "terminal", "data", "code", "console"}:
        return TYPE_PAIRS[2]
    if m & {"friendly", "playful", "kids", "soft", "warm", "consumer"}:
        return TYPE_PAIRS[3]
    return TYPE_PAIRS[0]


def choreograph(intent: str) -> Dict[str, Any]:
    """Motion tokens matched to the meaning of a transition."""
    s = (intent or "").lower()
    if re.search(r"\b(delete|remove|dismiss|close|exit|leave|archive)\b", s):
        kind, dur, ease, move = "exit", 140, "cubic-bezier(0.4, 0, 1, 1)", "fade + 4px down"
    elif re.search(r"\b(error|invalid|denied|fail)\b", s):
        kind, dur, ease, move = "attention", 320, "cubic-bezier(0.36, 0.07, 0.19, 0.97)", "6px horizontal shake, 3 cycles"
    elif re.search(r"\b(success|complete|saved|done|celebrate)\b", s):
        kind, dur, ease, move = "confirm", 260, "cubic-bezier(0.34, 1.56, 0.64, 1)", "scale 0.96 → 1 with overshoot"
    elif re.search(r"\b(navigate|page|route|screen|drill|detail)\b", s):
        kind, dur, ease, move = "transition", 240, "cubic-bezier(0.2, 0, 0, 1)", "shared-axis slide 16px + fade"
    elif re.search(r"\b(generate|compose|stream|ai|thinking)\b", s):
        kind, dur, ease, move = "generative", 420, "cubic-bezier(0.2, 0, 0, 1)", "staggered reveal, 40ms per element, blur 6px → 0"
    else:
        kind, dur, ease, move = "enter", 200, "cubic-bezier(0, 0, 0.2, 1)", "fade + 8px up"
    return {"kind": kind, "durationMs": dur, "easing": ease, "movement": move,
            "reducedMotion": "Opacity-only cross-fade, 120ms, no translation or scale.",
            "rationale": "%s motion should be %s so the change reads as cause and effect." % (
                kind.capitalize(), "quick and decelerating" if kind in ("enter", "transition") else "brief and unobtrusive")}


def illustrate(prompt: str, width: int = 640, height: int = 360, brand: str = "") -> str:
    """Procedural abstract illustration as an SVG data URI, seeded by the prompt."""
    seed = _hash(prompt or "fluidian")
    intent = theme_from_prompt(prompt)
    base = brand if K.is_hex(brand) else intent["brand"]
    L, C, H = K.rgb_to_oklch(K.parse_hex(base))
    stops = [K.oklch(0.93, 0.05, H), K.oklch(0.86, 0.09, (H + 40) % 360)]
    shapes = []
    for i in range(6):
        h = _hash("%s|%d" % (prompt, i))
        cx, cy = 60 + h % (width - 120), 40 + (h >> 8) % (height - 80)
        r = 40 + (h >> 16) % 110
        colour = K.oklch(0.62 + (i % 3) * 0.1, 0.16, (H + i * 47 + seed % 30) % 360)
        shapes.append('<circle cx="%d" cy="%d" r="%d" fill="%s" opacity="%.2f"/>' % (cx, cy, r, colour, 0.28 + (i % 3) * 0.12))
    wave = "M0 %d C %d %d, %d %d, %d %d L %d %d L 0 %d Z" % (
        height * 2 // 3, width // 4, height // 2 + seed % 40, width * 3 // 4, height * 5 // 6 - seed % 50, width,
        height * 2 // 3, width, height, height)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">'
           '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/>'
           '<stop offset="1" stop-color="%s"/></linearGradient><filter id="b"><feGaussianBlur stdDeviation="18"/></filter></defs>'
           '<rect width="100%%" height="100%%" fill="url(#g)"/><g filter="url(#b)">%s</g>'
           '<path d="%s" fill="%s" opacity="0.35"/></svg>') % (
        width, height, width, height, stops[0], stops[1], "".join(shapes), wave, K.oklch(0.5, 0.14, (H + 20) % 360))
    from urllib.parse import quote
    return "data:image/svg+xml;utf8," + quote(svg, safe="/:=,;'()")


_STATUS_TONE = [("success", r"\b(paid|active|success|succeeded|complete|completed|done|approved|healthy|online|delivered|resolved|passed|won|live|verified)\b"),
                ("warning", r"\b(pending|review|waiting|in progress|processing|trial|scheduled|at risk|expiring|partial|draft)\b"),
                ("danger", r"\b(failed|overdue|error|rejected|blocked|cancelled|canceled|churned|critical|offline|expired|lost|declined)\b"),
                ("info", r"\b(new|info|open|invited|queued|beta|preview|updated)\b")]


def semantic_tone(label: str) -> str:
    s = (label or "").lower()
    for tone, pattern in _STATUS_TONE:
        if re.search(pattern, s):
            return tone
    return "neutral"


def nearest_token(value: str, tokens: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    tokens = tokens or K.theme_tokens("#2f6bff")
    if not K.is_hex(value):
        return {"token": "", "distance": 1.0}
    L, C, H = K.rgb_to_oklch(K.parse_hex(value))
    best, dist = "", 9.0
    for t in tokens:
        if not K.is_hex(t["value"]):
            continue
        l2, c2, h2 = K.rgb_to_oklch(K.parse_hex(t["value"]))
        dh = min(abs(H - h2), 360 - abs(H - h2)) / 180.0
        d = ((L - l2) ** 2 + (C - c2) ** 2 + (dh * min(C, c2) * 2) ** 2) ** 0.5
        if d < dist:
            best, dist = t["name"], d
    return {"token": best, "distance": round(dist, 3)}
