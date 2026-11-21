"""Building blocks shared by the showcase screens."""
from fluidian import Node

SCREENS = []
_ALIAS = {"from_": "from", "as_": "as", "to_": "to", "max_": "max", "min_": "min", "format_": "format", "open_": "open", "id_": None}


def screen(route, group, title, theme="iris", height=900, caption="", width=1440):
    """Register a showcase screen. `height` is the capture height used for the documentation shots."""
    def register(build):
        SCREENS.append({"route": "/" + route.strip("/"), "slug": route.strip("/").replace("/", "-"), "group": group, "title": title, "theme": theme,
                        "height": height, "width": width, "caption": caption or title, "build": build})
        return build
    return register


def n(component, /, *children, **props):
    """A node of any component type: positional children, keyword props."""
    node = Node(component)
    ident = props.pop("id_", None)
    if ident:
        node.id(ident)
    for key, value in props.items():
        if value is not None:
            node.prop(_ALIAS.get(key, key), value)
    return node.add(*[c for c in children if c is not None])


def text(content, **p):
    return n("Text", content=content, **p)


def muted(content, size="sm", **p):
    return n("Text", content=content, tone="muted", size=size, **p)


def strong(content, size="md", **p):
    return n("Text", content=content, weight="bold", size=size, **p)


def heading(content, level=2, **p):
    return n("Heading", text=content, level=level, **p)


def btn(label, variant="secondary", **p):
    return n("Button", label=label, variant=variant, **p)


def badge(label, tone="neutral", **p):
    return n("Badge", label=label, tone=tone, **p)


def row(*c, **p):
    return n("Row", *c, **p)


def stack(*c, **p):
    return n("Stack", *c, **p)


def grid(*c, **p):
    return n("Grid", *c, **p)


def split(*c, **p):
    return n("Split", *c, **p)


def card(*c, **p):
    return n("Card", *c, **p)


def art(kind, **p):
    return n("Art", kind=kind, **p)


def stat(label, value, **p):
    return n("Stat", label=label, value=value, **p)


def spacer(size="md"):
    return n("Spacer", size=size)


def between(*c, **p):
    return n("Row", *c, justify="between", **p)


def nav(brand, links, *actions, **p):
    return n("NavBar", *actions, brand=brand, links=[{"label": l, "href": "#"} for l in links], **p)


def footer(brand, columns, note, **p):
    return n("Footer", brand=brand, columns=[{"title": t, "links": ls} for t, ls in columns], note=note, **p)


def shell(brand, items, *children, active=0, user=None, tagline=None, **p):
    """An app frame. `items` is a list of (label, icon) or (label, icon, section) or (label, icon, section, badge)."""
    navs = []
    for i, it in enumerate(items):
        entry = {"label": it[0], "icon": it[1], "route": "#", "active": i == active}
        if len(it) > 2 and it[2]:
            entry["section"] = it[2]
        if len(it) > 3 and it[3]:
            entry["badge"] = it[3]
        navs.append(entry)
    return n("Shell", *children, brand=brand, nav=navs, user=user, tagline=tagline, **p)


def page(title, *children, **p):
    return n("Page", *children, title=title, **p)


def phone(*children, platform="ios", **p):
    return n("DeviceFrame", *children, kind="phone", platform=platform, **p)


def series(seed, count=12, base=100.0, drift=4.0, noise=10.0, low=None):
    """A deterministic pseudo-random walk for charts and sparklines."""
    x, out, value = (seed * 2654435761) % 4294967296, [], float(base)
    for _ in range(count):
        x = (1103515245 * x + 12345) % 2147483648
        value += drift + (x / 2147483648 - 0.5) * 2 * noise
        if low is not None:
            value = max(low, value)
        out.append(round(value, 2))
    return out


def noise(seed, count):
    """Deterministic independent values between -1 and 1."""
    x, out = (seed * 2654435761 + 97) % 2147483648, []
    for _ in range(count):
        x = (1103515245 * x + 12345) % 2147483648
        out.append(x / 1073741824 - 1)
    return out


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PEOPLE = ["Mira Okafor", "Jonas Weber", "Ana Lima", "Kenji Sato", "Priya Nair", "Tomás Rey", "Lena Fischer", "Omar Haddad", "Sofia Marin", "Idris Bello"]
COMPANIES = ["Arcwell", "Kestrel", "Oakline", "Lumina", "Northpass", "Halden", "Tessellate", "Quillon", "Verano", "Brightside"]


def monthly(seed, key="value", count=12, **kw):
    return [{"month": MONTHS[i % 12], key: v} for i, v in enumerate(series(seed, count, **kw))]


def kpis(*items, columns=4, **p):
    """Stats from (label, value, delta, hint, icon[, spark seed]) tuples."""
    cells = []
    for it in items:
        extra = {}
        if len(it) > 5 and it[5] is not None:
            extra["spark"] = series(it[5], 16, 100, 1.5 if not str(it[2]).startswith("-") else -1.5, 6)
        cells.append(stat(it[0], it[1], delta=it[2] if len(it) > 2 else None, hint=it[3] if len(it) > 3 else None, icon=it[4] if len(it) > 4 else None, **extra))
    return grid(*cells, columns=columns, **p)


def table(columns, rows, **p):
    """A table from (key, label[, format[, align]]) column tuples."""
    cols = []
    for c in columns:
        col = {"key": c[0], "label": c[1]}
        if len(c) > 2 and c[2]:
            col["format"] = c[2]
        if len(c) > 3 and c[3]:
            col["align"] = c[3]
        cols.append(col)
    return n("Table", columns=cols, rows=rows, **p)


def chart(kind, data, x, y, **p):
    return n("Chart", kind=kind, data=data, x=x, y=y if isinstance(y, list) else [y], **p)


def listing(items, **p):
    """A list from (title, detail, meta[, icon[, tone[, badge]]]) tuples."""
    out = []
    for it in items:
        row_ = {"title": it[0], "detail": it[1] if len(it) > 1 else None, "meta": it[2] if len(it) > 2 else None}
        if len(it) > 3 and it[3]:
            row_["avatar" if " " in it[3] and it[3][0].isupper() else "icon"] = it[3]
        if len(it) > 4 and it[4]:
            row_["tone"] = it[4]
        if len(it) > 5 and it[5]:
            row_["badge"] = it[5]
        out.append({k: v for k, v in row_.items() if v is not None})
    return n("List", items=out, **p)


def feature(title, body, icon=None, **p):
    return n("Feature", title=title, body=body, icon=icon, **p)


def field(label, name, value=None, **p):
    return n("Input", name=name, label=label, value=value, **p)


def browser(*children, url="app.example.com", **p):
    return n("DeviceFrame", *children, kind="browser", url=url, **p)


def code(source, language="python", **p):
    return n("Code", source=source, language=language, **p)


def tabs(*pairs, **p):
    return n("Tabs", *[n("Tab", *([c] if not isinstance(c, (list, tuple)) else c), label=label) for label, c in pairs], **p)
