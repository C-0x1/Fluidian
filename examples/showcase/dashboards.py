"""Dashboards."""
from kit import *  # noqa: F401,F403


@screen("dash/finance", "Dashboards", "Northbank · wealth dashboard", theme="midnight", height=1180,
        caption="A wealth dashboard in the Midnight theme: allocation rings, a performance curve and holdings with trends")
def finance(ctx):
    holdings = [{"symbol": "NWD", "name": "Northwind Global", "price": "$184.20", "change": "+1.42%", "spark": series(3, 14, 100, 1.2, 4)},
                {"symbol": "KST", "name": "Kestrel Energy", "price": "$62.75", "change": "-0.80%", "spark": series(5, 14, 100, -0.6, 4)},
                {"symbol": "OAK", "name": "Oakline Health", "price": "$241.10", "change": "+2.96%", "spark": series(9, 14, 100, 2, 4)},
                {"symbol": "LMN", "name": "Lumina Semis", "price": "$97.34", "change": "+0.35%", "spark": series(11, 14, 100, 0.4, 5)},
                {"symbol": "HLD", "name": "Halden Rail", "price": "$38.02", "change": "-1.15%", "spark": series(13, 14, 100, -0.9, 3)}]
    activity = [{"title": "Dividend · Northwind Global", "detail": "Reinvested automatically", "meta": "+$184.20", "icon": "dollar", "tone": "success"},
                {"title": "Bought 12 × Oakline Health", "detail": "Limit order filled at $238.40", "meta": "-$2,860.80", "icon": "arrow-down", "tone": "brand"},
                {"title": "Monthly deposit", "detail": "From Northbank Current ·· 4821", "meta": "+$2,500.00", "icon": "wallet", "tone": "info"},
                {"title": "Rebalanced to target", "detail": "3 trades, $0 fees", "meta": "Auto", "icon": "swap", "tone": "ai"}]
    return shell("Northbank", [("Overview", "home", "Wealth"), ("Portfolio", "pie", "Wealth"), ("Activity", "activity", "Wealth"), ("Transfers", "swap", "Wealth"), ("Goals", "target", "Plan", "3"), ("Tax centre", "receipt", "Plan"), ("Research", "search", "Plan"), ("Settings", "settings", "Account")],
                 page("Good evening, Mira",
                      grid(stat("Net worth", "$482,910", delta="+4.8%", hint="this quarter", icon="wallet", spark=series(1, 16, 100, 2, 5)),
                           stat("Invested", "$391,400", delta="+$12,300", hint="deposits YTD", icon="trend-up", spark=series(2, 16, 100, 1.4, 3)),
                           stat("Cash", "$58,220", delta="4.35% APY", trend="flat", hint="high-yield", icon="bank"),
                           stat("Day change", "+$2,184", delta="+0.45%", hint="vs yesterday", icon="activity", spark=series(4, 16, 100, 0.5, 8)), columns=4),
                      split(card(n("Chart", kind="area", height=290, x="month", y=["portfolio", "benchmark"], data=[{"month": MONTHS[i], "portfolio": a, "benchmark": b} for i, (a, b) in enumerate(zip(series(21, 12, 360, 11, 9), series(22, 12, 360, 7, 6)))]),
                                 title="Performance", subtitle="Your portfolio against the global index, last 12 months"),
                            card(n("Rings", center="72%", items=[{"label": "Equities", "value": 72, "display": "72%"}, {"label": "Bonds", "value": 18, "max": 100, "display": "18%"}, {"label": "Cash", "value": 10, "display": "10%"}]),
                                 n("Insight", title="You are 4% above your equity target", tone="ai", body="Rebalancing would sell $19,300 of equities. No tax would be due inside your ISA.", bullets=[]),
                                 title="Allocation", subtitle="Target 68 / 22 / 10"), ratio="5:3"),
                      split(card(n("Ticker", items=holdings), title="Holdings", subtitle="Five largest positions"),
                            card(n("List", items=activity), title="Recent activity", subtitle="Last 30 days"), ratio="1:1"),
                      subtitle="Markets closed 0.4% higher. Your plan is on track for 2041.", width="wide"),
                 user={"name": "Mira Okafor", "role": "Private client"}, tagline="Wealth")


def heat(seed, rows, cols, top=9):
    flat = series(seed, rows * cols, top / 2, 0, top / 2, 0)
    return [[max(0, round(v)) for v in flat[r * cols:(r + 1) * cols]] for r in range(rows)]


@screen("dash/saas", "Dashboards", "Orbit · product analytics", theme="deep", height=1260,
        caption="Product analytics: activation, a conversion funnel, a retention heatmap and the pages people use most")
def saas(ctx):
    return shell("Orbit", [("Overview", "home", "Analytics"), ("Funnels", "filter", "Analytics"), ("Retention", "refresh", "Analytics"), ("Journeys", "route", "Analytics"), ("Segments", "users", "Data"), ("Events", "activity", "Data"), ("Alerts", "bell", "Data", "2"), ("Settings", "settings", "Workspace")],
                 page("Product overview",
                      between(n("Segmented", name="range", value="30 days", options=["7 days", "30 days", "Quarter", "Year"]), row(n("AvatarStack", names=PEOPLE[:5], label="5 viewing"), btn("Share", "secondary", icon="share"), btn("Ask Orbit", "ai"), gap="sm")),
                      kpis(("Weekly active users", "48,210", "+9.2%", "vs last week", "users", 101), ("Activation rate", "62.4%", "+3.1 pts", "day 1", "bolt", 102), ("Week-4 retention", "41.8%", "+1.4 pts", "cohort avg", "refresh", 103), ("Net revenue", "$284k", "+6.0%", "this month", "dollar", 104)),
                      split(card(chart("area", [{"week": "W%d" % (i + 1), "Signups": a, "Activated": b} for i, (a, b) in enumerate(zip(series(105, 12, 900, 60, 90), series(106, 12, 520, 46, 60)))], "week", ["Signups", "Activated"], height=270), title="Growth", subtitle="New signups and those who reached the activation event"),
                            card(n("Funnel", stages=[{"label": "Visited", "value": 48200}, {"label": "Signed up", "value": 9800}, {"label": "Activated", "value": 6100}, {"label": "Invited a teammate", "value": 2900}, {"label": "Subscribed", "value": 1420}]), title="Conversion funnel", subtitle="Last 30 days"), ratio="5:4"),
                      split(card(n("Heatmap", values=[[100, 68, 55, 48, 44, 41, 39, 38], [100, 71, 58, 50, 46, 43, 42, 0], [100, 66, 54, 49, 45, 43, 0, 0], [100, 73, 61, 53, 48, 0, 0, 0], [100, 75, 63, 56, 0, 0, 0, 0], [100, 78, 66, 0, 0, 0, 0, 0]], max_=100,
                                   rowLabels=["Oct 5", "Oct 12", "Oct 19", "Oct 26", "Nov 2", "Nov 9"], colLabels=["W0", "W1", "W2", "W3", "W4", "W5", "W6", "W7"]), title="Retention by cohort", subtitle="Share of each weekly cohort still active"),
                            card(n("BarList", ranked=True, items=[{"label": "/dashboard", "value": 182400, "detail": "avg 4m 12s"}, {"label": "/reports/new", "value": 96300, "detail": "avg 6m 40s"}, {"label": "/settings/team", "value": 51200, "detail": "avg 1m 05s"},
                                                                 {"label": "/integrations", "value": 38900, "detail": "avg 2m 31s"}, {"label": "/billing", "value": 12100, "detail": "avg 0m 48s"}]), title="Most used", subtitle="Page views"), ratio="5:4"),
                      subtitle="All platforms · updated 2 minutes ago", width="wide"),
                 user={"name": "Priya Nair", "role": "Product lead"}, tagline="Analytics")


def candles(seed, count=44, start=412.0):
    out, price, rand = [], start, noise(seed, count * 4)
    for i in range(count):
        o = price
        c = round(o + rand[i * 4] * 3.4 + 0.36, 2)
        hi, lo = round(max(o, c) + abs(rand[i * 4 + 1]) * 3, 2), round(min(o, c) - abs(rand[i * 4 + 2]) * 3, 2)
        out.append({"t": "%02d:%02d" % (9 + (i * 10 + 30) // 60, (i * 10 + 30) % 60), "o": round(o, 2), "h": hi, "l": lo, "c": c, "v": round(30 + abs(rand[i * 4 + 3]) * 60)})
        price = c
    return out


@screen("dash/trading", "Dashboards", "Vector · trading terminal", theme="crimson", height=1100,
        caption="A trading terminal in the Crimson theme: candlesticks with volume, an order book and open positions")
def trading(ctx):
    book = [{"side": "Ask", "price": 428.60, "size": 1240, "total": "531k"}, {"side": "Ask", "price": 428.45, "size": 860, "total": "368k"}, {"side": "Ask", "price": 428.30, "size": 2110, "total": "904k"},
            {"side": "Bid", "price": 428.10, "size": 1980, "total": "848k"}, {"side": "Bid", "price": 427.95, "size": 1420, "total": "608k"}, {"side": "Bid", "price": 427.80, "size": 3050, "total": "1.3M"}]
    positions = [{"symbol": "NWD", "side": "Long", "qty": 400, "entry": 412.30, "mark": 428.12, "pnl": "+$6,328", "status": "Open"}, {"symbol": "KST", "side": "Short", "qty": 900, "entry": 63.40, "mark": 62.75, "pnl": "+$585", "status": "Open"},
                 {"symbol": "LMN", "side": "Long", "qty": 1200, "entry": 98.10, "mark": 97.34, "pnl": "−$912", "status": "Open"}]
    watch = [{"symbol": s, "name": nm, "price": p, "change": c, "spark": series(i + 120, 14, 100, 1 if c.startswith("+") else -1, 4)} for i, (s, nm, p, c) in enumerate(
        [("NWD", "Northwind", "428.12", "+3.84%"), ("OAK", "Oakline", "241.10", "+2.96%"), ("KST", "Kestrel", "62.75", "-0.80%"), ("LMN", "Lumina", "97.34", "-0.77%"), ("HLD", "Halden", "38.02", "-1.15%"), ("QLN", "Quillon", "154.60", "+0.42%")])]
    return shell("VECTOR", [("Trade", "activity", "Markets"), ("Markets", "globe", "Markets"), ("Screener", "filter", "Markets"), ("Orders", "list", "Account", "3"), ("Positions", "layers", "Account"), ("History", "clock", "Account"), ("Alerts", "bell", "Account")],
                 page("",
                      between(row(heading("NWD · Northwind Global", 1), badge("NASDAQ", "neutral"), badge("Market open", "success", dot=True), gap="sm"), row(strong("428.12", "xl"), badge("+15.82 (3.84%)", "success", icon="trend-up"), gap="sm")),
                      split(stack(card(between(n("Segmented", name="tf", value="10m", options=["1m", "10m", "1h", "1D", "1W"]), row(badge("O 412.30", "neutral"), badge("H 431.05", "neutral"), badge("L 410.80", "neutral"), badge("Vol 18.4M", "neutral"), gap="xs")),
                                       n("Candles", data=candles(9), height=390, format="number"), padding="md"),
                                  card(table([("symbol", "Symbol"), ("side", "Side", "badge"), ("qty", "Qty", "number", "end"), ("entry", "Entry", "number", "end"), ("mark", "Mark", "number", "end"), ("pnl", "Unrealised P&L", None, "end")], positions, dense=True, sortable=False), title="Positions", padding="none")),
                            stack(card(table([("side", "Side", "badge"), ("price", "Price", "number", "end"), ("size", "Size", "number", "end"), ("total", "Total", None, "end")], book, dense=True, sortable=False), title="Order book", subtitle="Spread 0.20", padding="none"),
                                  card(n("Segmented", name="side", value="Buy", options=["Buy", "Sell"]), grid(field("Quantity", "qty", "100"), field("Limit price", "limit", "428.10"), columns=2, gap="sm"),
                                       between(muted("Estimated cost"), strong("$42,810.00")), btn("Place buy order", "primary", block=True), title="Order ticket"),
                                  card(n("Ticker", items=watch[:4]), title="Watchlist")), ratio="9:4"),
                      width="full"), tagline="Pro terminal", user={"name": "Omar Haddad", "role": "Margin account"})


@screen("dash/health", "Dashboards", "Pulse · health dashboard", theme="ember", height=1160,
        caption="Health and training in the Ember theme: activity rings, heart-rate zones, sleep stages and a readiness gauge")
def health(ctx):
    return shell("Pulse", [("Today", "activity", "Body"), ("Training", "dumbbell", "Body"), ("Sleep", "moon", "Body"), ("Nutrition", "utensils", "Body"), ("Trends", "trend-up", "Insights"), ("Coach", "sparkles", "Insights"), ("Devices", "watch", "Account")],
                 page("Good morning, Ana",
                      grid(card(n("Rings", size=176, center="78%", items=[{"label": "Move", "value": 468, "max": 600, "display": "468 kcal"}, {"label": "Train", "value": 34, "max": 40, "display": "34 min"}, {"label": "Stand", "value": 9, "max": 12, "display": "9 h"}]), title="Activity"),
                           card(row(n("Gauge", value=84, label="Readiness", detail="Primed for intensity", tone="success", size=170), justify="center"), title="Recovery"),
                           card(n("Insight", title="Push today, protect tomorrow", tone="ai", body="Heart-rate variability is 12% above your baseline and you slept 7h 42m. A threshold run fits well.", bullets=["Suggested: 6 × 4 min at zone 4", "Fuel 60 g of carbohydrate beforehand", "Tomorrow: easy 30 min or rest"]),
                                row(btn("Start workout", "primary", icon="play"), btn("Why this plan?", "ghost"), gap="sm"), title="Coach"), columns=3),
                      split(card(chart("line", [{"t": "%02d:00" % h, "bpm": v} for h, v in zip(range(0, 24, 2), [52, 50, 49, 54, 72, 88, 132, 96, 84, 78, 70, 58])], "t", "bpm", height=230, legend=False, annotations=[{"x": "12:00", "label": "Run · 148 max", "tone": "danger"}]), title="Heart rate", subtitle="Resting 52 bpm · today"),
                            card(chart("bar", [{"night": d, "Deep": a, "REM": b, "Light": c} for d, a, b, c in zip(DAYS, [1.4, 1.1, 1.6, 1.2, 1.5, 1.9, 1.7], [1.8, 1.5, 2.0, 1.6, 1.9, 2.2, 2.1], [3.9, 3.6, 4.1, 3.4, 4.3, 4.4, 4.0])], "night", ["Deep", "REM", "Light"], height=230, stacked=True, format="number"), title="Sleep stages", subtitle="Hours per night"), ratio="1:1"),
                      grid(stat("Steps", "9,412", delta="+1,204", hint="vs average", icon="activity", spark=series(131, 14, 100, 1, 9)), stat("VO₂ max", "47.2", delta="+0.6", hint="this month", icon="heart-pulse", spark=series(132, 14, 100, 0.6, 2)),
                           stat("Weekly load", "412", delta="Optimal", trend="flat", hint="range 380–460", icon="flame"), stat("Hydration", "1.9 L", delta="-0.4 L", hint="to goal", icon="droplet"), columns=4),
                      subtitle="Thursday 19 November · you are 78% of the way to today's goals", width="wide"),
                 user={"name": "Ana Lima", "role": "Half-marathon in 23 days"}, tagline="Health")


@screen("dash/home", "Dashboards", "Hearthstone · smart home", theme="grape", height=1100,
        caption="A smart-home panel in the Grape theme: device tiles, a thermostat gauge, energy use and scenes")
def home(ctx):
    tile = lambda t, i, on=False, **p: n("ControlTile", title=t, icon=i, on=on, **p)  # noqa: E731
    return shell("Hearthstone", [("Home", "home", "House"), ("Rooms", "grid", "House"), ("Climate", "thermometer", "House"), ("Security", "shield", "House", "1"), ("Energy", "bolt", "Insights"), ("Automations", "wand", "Insights"), ("Settings", "settings", "Account")],
                 page("Welcome home",
                      row(*[n("Button", label=l, icon=i, variant="primary" if a else "secondary") for l, i, a in [("Evening", "moon", True), ("Movie night", "tv", False), ("Away", "lock", False), ("Good morning", "sunrise", False), ("Dinner", "utensils", False)]], gap="xs"),
                      split(stack(grid(tile("Living room lights", "bulb", True, value="70% · warm", detail="4 lamps"), tile("Kitchen lights", "bulb", True, value="100%", detail="6 spots", tone="warning"), tile("Front door", "lock", True, value="Locked", detail="Since 18:42", tone="success"),
                                       tile("Speakers", "speaker", True, value="Low Tide · 30%", detail="Living room", tone="ai"), tile("Heating", "flame", False, offValue="Eco · 18°", detail="Schedule at 21:00"), tile("Robot vacuum", "bot", False, offValue="Docked", detail="Cleaned 12:10"),
                                       tile("Bedroom blinds", "sidebar", False, offValue="Open", detail="Closes at sunset"), tile("Garage", "door", False, offValue="Closed", detail="Opened twice today"), columns=4, gap="sm"),
                                  card(chart("area", [{"h": "%02d:00" % h, "Solar": a, "Grid": b} for h, a, b in zip(range(6, 22, 2), [0.1, 0.9, 2.4, 3.1, 2.8, 1.2, 0.2, 0], [0.9, 0.4, 0.1, 0, 0.1, 0.6, 1.8, 2.2])], "h", ["Solar", "Grid"], height=210, format="number"), title="Energy today", subtitle="kW · solar covered 71% of use")),
                            stack(card(row(n("Gauge", value=21.5, max_=30, display="21.5°", label="Living room", detail="Heating to 22°", tone="warning", size=190), justify="center"),
                                       between(btn("", "secondary", icon="minus"), strong("Target 22°"), btn("", "secondary", icon="plus")), title="Climate"),
                                  card(listing([("Front door camera", "Motion at 18:42 · Mira arrived", "2m ago", "camera", "success"), ("Window sensor", "Bedroom window open", "38m ago", "alert", "warning"), ("Smoke alarms", "All 4 tested this month", "OK", "shield", "info")]), title="Security")), ratio="5:2"),
                      subtitle="21.5° inside · 9° outside · everything is locked", width="wide"),
                 user={"name": "Mira Okafor", "role": "Owner"}, tagline="Smart home")


@screen("dash/devops", "Dashboards", "Stackline · observability", theme="lagoon", height=1180,
        caption="An observability console in the Lagoon theme, teal on deep blue-green: latency and error rates, service health, an incident timeline and live logs")
def devops(ctx):
    services = [{"service": "checkout-api", "region": "18 regions", "p95": "84 ms", "errors": "0.02%", "deploys": "4 today", "status": "Healthy"}, {"service": "search", "region": "12 regions", "p95": "142 ms", "errors": "0.08%", "deploys": "1 today", "status": "Healthy"},
                {"service": "payments-worker", "region": "3 regions", "p95": "910 ms", "errors": "1.84%", "deploys": "2 today", "status": "Degraded"}, {"service": "image-resize", "region": "18 regions", "p95": "61 ms", "errors": "0.00%", "deploys": "—", "status": "Healthy"},
                {"service": "auth", "region": "18 regions", "p95": "38 ms", "errors": "0.01%", "deploys": "—", "status": "Healthy"}]
    return shell("Stackline", [("Overview", "home", "Observe"), ("Services", "server", "Observe"), ("Logs", "terminal", "Observe"), ("Traces", "route", "Observe"), ("Incidents", "alert", "Respond", "1"), ("On call", "phone", "Respond"), ("Deployments", "rocket", "Ship")],
                 page("Production",
                      n("Banner", text="payments-worker is degraded in eu-west: p95 latency is 11× normal. Incident #482 opened 6 minutes ago.", tone="warning", icon="alert"),
                      kpis(("Requests / s", "48.2k", "+6%", "vs 1h ago", "activity", 141), ("p95 latency", "84 ms", "-9 ms", "vs 1h ago", "clock", 142), ("Error rate", "0.21%", "+0.17 pts", "vs 1h ago", "alert", 143), ("Apdex", "0.97", "-0.01", "target 0.95", "gauge", 144)),
                      split(card(chart("line", [{"t": "%02d:%02d" % (14 + i // 6, (i % 6) * 10), "p50": a, "p95": b, "p99": c} for i, (a, b, c) in enumerate(zip(series(145, 12, 30, 0.3, 3, 20), series(146, 12, 80, 1, 9, 50), series(147, 12, 150, 9, 30, 90)))], "t", ["p50", "p95", "p99"], height=250, points=False), title="Latency", subtitle="Milliseconds, all services"),
                            card(n("Timeline", items=[{"title": "Alert fired: error rate above 1%", "time": "14:52", "tone": "danger", "icon": "alert"}, {"title": "Lena acknowledged the page", "time": "14:53", "tone": "info", "icon": "user"},
                                                      {"title": "Suspect: deploy c41d0f2 to payments-worker", "time": "14:55", "tone": "ai", "icon": "sparkles", "detail": "Latency rose 40 seconds after rollout"}, {"title": "Rollback started", "time": "14:58", "tone": "warning", "icon": "undo"}]),
                                 row(btn("Open incident", "primary"), btn("Roll back now", "danger"), gap="sm"), title="Incident #482", subtitle="payments-worker · eu-west"), ratio="5:3"),
                      split(card(table([("service", "Service"), ("region", "Regions"), ("p95", "p95", None, "end"), ("errors", "Errors", None, "end"), ("deploys", "Deploys"), ("status", "Status", "badge")], services, dense=True), title="Services", padding="none"),
                            n("Terminal", title="logs · payments-worker · eu-west", cursor=False, lines=[{"text": "14:57:02 INFO  charge accepted id=ch_8f3c latency=212ms", "kind": "dim"}, {"text": "14:57:03 WARN  upstream slow provider=cardnet latency=4120ms", "kind": "warn"},
                                                                                                         {"text": "14:57:03 ERROR timeout waiting for cardnet (attempt 3/3)", "kind": "err"}, {"text": "14:57:04 INFO  circuit breaker open for cardnet (30s)", "kind": "dim"}, {"text": "14:57:05 INFO  failover to provider=payline ok", "kind": "ok"},
                                                                                                         {"text": "14:57:06 INFO  charge accepted id=ch_8f3d latency=188ms", "kind": "dim"}]), ratio="5:3"),
                      subtitle="62 services · 18 regions · last deploy 4 minutes ago", width="wide"),
                 user={"name": "Lena Fischer", "role": "On call"}, tagline="acme / production")


@screen("dash/llm", "Dashboards", "Relay · LLM gateway console", theme="abyss", height=1200,
        caption="An LLM gateway console: token spend by model, cache savings, budgets per team and the latest requests")
def llm(ctx):
    reqs = [{"time": "15:02:41", "model": "atlas-large", "team": "Search", "tokens": "4,120", "latency": "1.8 s", "cost": "$0.0198", "route": "Cached"}, {"time": "15:02:40", "model": "quill-mini", "team": "Support", "tokens": "812", "latency": "0.4 s", "cost": "$0.0003", "route": "Reflex"},
            {"time": "15:02:38", "model": "ember-code", "team": "Platform", "tokens": "9,640", "latency": "3.1 s", "cost": "$0.0212", "route": "Primary"}, {"time": "15:02:37", "model": "atlas-large", "team": "Search", "tokens": "2,205", "latency": "2.2 s", "cost": "$0.0106", "route": "Failover"},
            {"time": "15:02:35", "model": "onyx-vision", "team": "Growth", "tokens": "1,930", "latency": "1.1 s", "cost": "$0.0058", "route": "Primary"}]
    return shell("Relay", [("Usage", "chart", "Console"), ("Requests", "list", "Console"), ("Models", "cpu", "Console"), ("Routing", "route", "Console"), ("Budgets", "wallet", "Govern"), ("Keys", "key", "Govern"), ("Guardrails", "shield", "Govern"), ("Evaluations", "target", "Govern")],
                 page("Usage",
                      kpis(("Requests", "18.4M", "+22%", "this week", "activity", 151), ("Tokens", "41.2B", "+18%", "this week", "layers", 152), ("Spend", "$12,840", "-31%", "vs list price", "dollar", 153), ("Median latency", "0.9 s", "-0.2 s", "vs last week", "clock", 154)),
                      split(card(chart("bar", [{"day": d, "atlas-large": a, "quill-mini": b, "ember-code": c, "other": e} for d, a, b, c, e in zip(DAYS, series(155, 7, 900, 30, 120, 300), series(156, 7, 420, 30, 80, 100), series(157, 7, 260, 40, 60, 60), series(158, 7, 120, 5, 40, 30))], "day", ["atlas-large", "quill-mini", "ember-code", "other"], height=270, stacked=True, format="currency"), title="Spend by model", subtitle="US dollars per day"),
                            stack(card(row(n("Rings", size=132, center="38%", legend=False, items=[{"label": "Cache", "value": 38}, {"label": "Reflex", "value": 21}]),
                                           stack(n("KeyValue", items=[{"key": "Served from cache", "value": "38% · saved $5,120"}, {"key": "Answered offline by Reflex", "value": "21% · saved $2,870"}, {"key": "Automatic failovers", "value": "214 · 0 user-facing errors"}]), gap="sm"), gap="lg", wrap=False), title="Savings this week"),
                                  card(n("Progress", label="Search · $4,120 of $5,000", value=82, tone="warning"), n("Progress", label="Support · $1,960 of $6,000", value=33, tone="success"), n("Progress", label="Platform · $5,480 of $7,000", value=78), n("Progress", label="Growth · $1,280 of $2,000", value=64), title="Team budgets")), ratio="5:4"),
                      card(table([("time", "Time"), ("model", "Model"), ("team", "Team"), ("tokens", "Tokens", None, "end"), ("latency", "Latency", None, "end"), ("cost", "Cost", None, "end"), ("route", "Route", "badge")], reqs, dense=True, sortable=False), title="Live requests", subtitle="Streaming · sampled 1 in 2,000", padding="none"),
                      subtitle="acme · production keys · 19 November", width="wide"),
                 user={"name": "Idris Bello", "role": "Platform"}, tagline="Console")


@screen("dash/crm", "Dashboards", "Northpass · sales pipeline", theme="ocean", height=1180,
        caption="A sales workspace: a pipeline board with deal values, a forecast with a confidence band and a leaderboard")
def crm(ctx):
    deal = lambda t, v, who, *tags: {"title": t, "detail": v, "tags": list(tags), "assignee": who}  # noqa: E731
    board = n("Board", columns=[{"title": "Qualified · $184k", "cards": [deal("Arcwell renewal", "$62,000 · closes 12 Dec", PEOPLE[1], "Renewal"), deal("Kestrel pilot", "$38,000 · closes 20 Dec", PEOPLE[2], "New"), deal("Verano expansion", "$84,000 · closes Jan", PEOPLE[4], "Upsell")]},
                                {"title": "Proposal · $241k", "cards": [deal("Oakline platform", "$126,000 · closes 5 Dec", PEOPLE[0], "New", "Champion"), deal("Halden analytics", "$115,000 · closes 18 Dec", PEOPLE[3], "New")]},
                                {"title": "Negotiation · $310k", "cards": [deal("Lumina enterprise", "$210,000 · legal review", PEOPLE[5], "Enterprise", "At risk"), deal("Quillon seats", "$100,000 · procurement", PEOPLE[1], "Upsell")]},
                                {"title": "Won this month · $392k", "cards": [deal("Tessellate", "$148,000 · signed 14 Nov", PEOPLE[0], "New"), deal("Brightside", "$244,000 · signed 6 Nov", PEOPLE[3], "Enterprise")]}])
    forecast = chart("line", [{"month": m, "Bookings": v} for m, v in zip(MONTHS[5:11], [410, 438, 402, 465, 498, 392])], "month", "Bookings", height=230, legend=False, format="currency",
                     forecast=[{"x": "Dec", "value": 540, "low": 470, "high": 610}, {"x": "Jan", "value": 575, "low": 480, "high": 670}])
    return shell("Northpass", [("Pipeline", "layers", "Sell"), ("Accounts", "building", "Sell"), ("Contacts", "users", "Sell"), ("Inbox", "mail", "Sell", "7"), ("Forecast", "trend-up", "Plan"), ("Reports", "chart", "Plan"), ("Playbooks", "book", "Plan")],
                 page("Pipeline",
                      kpis(("Open pipeline", "$735k", "+12%", "vs last month", "layers", 161), ("Won this month", "$392k", "71% of quota", "11 days left", "award", 162), ("Win rate", "34%", "+4 pts", "trailing 90 days", "target", 163), ("Average cycle", "41 days", "-6 days", "vs last quarter", "clock", 164)),
                      card(board, padding="sm"),
                      split(card(forecast, n("Insight", title="December is likely to land at $540k", tone="ai", body="Two deals carry 58% of the forecast. Lumina is at risk: no reply from legal in 9 days.", bullets=[]), title="Forecast", subtitle="Bookings in $k, with an 80% band"),
                            card(n("BarList", ranked=True, format="currency", items=[{"label": PEOPLE[0], "value": 392000, "detail": "4 deals"}, {"label": PEOPLE[3], "value": 359000, "detail": "3 deals"}, {"label": PEOPLE[1], "value": 262000, "detail": "5 deals"}, {"label": PEOPLE[5], "value": 210000, "detail": "1 deal"}, {"label": PEOPLE[2], "value": 138000, "detail": "2 deals"}]), title="Leaderboard", subtitle="Closed and committed, this quarter"), ratio="5:4"),
                      subtitle="Q4 · team quota $1.65M · 71% attained", width="wide"),
                 user={"name": "Mira Okafor", "role": "Sales director"}, tagline="CRM")


@screen("dash/projects", "Dashboards", "Cadence · project tracker", theme="emerald", height=1160,
        caption="A project tracker in black and white: a roadmap, a burndown, workload by person and what is due this week")
def projects(ctx):
    roadmap = n("Roadmap", label="Workstream", today=5.4, columns=["Oct 6", "Oct 20", "Nov 3", "Nov 17", "Dec 1", "Dec 15", "Dec 29", "Jan 12"],
                rows=[{"label": "Checkout redesign", "avatar": PEOPLE[2], "bars": [{"start": 0, "end": 3.2, "label": "Research and design", "tone": "info", "progress": 100}, {"start": 3.2, "end": 6.4, "label": "Build", "tone": "brand", "progress": 68}]},
                      {"label": "Mobile app 3.0", "avatar": PEOPLE[3], "bars": [{"start": 1, "end": 5, "label": "Beta", "tone": "success", "progress": 90}, {"start": 5, "end": 7.5, "label": "Store review and launch", "tone": "warning", "progress": 10}]},
                      {"label": "Billing migration", "avatar": PEOPLE[5], "bars": [{"start": 2.4, "end": 5.8, "label": "Dual-write and backfill", "tone": "danger", "progress": 52}]},
                      {"label": "Design system", "avatar": PEOPLE[6], "bars": [{"start": 0.5, "end": 2.8, "label": "Tokens", "tone": "ai", "progress": 100}, {"start": 3, "end": 8, "label": "Components and docs", "tone": "ai", "progress": 44}]},
                      {"label": "SOC 2 audit", "avatar": PEOPLE[7], "bars": [{"start": 4, "end": 7, "label": "Evidence collection", "tone": "neutral", "progress": 30}]}])
    return shell("Cadence", [("Home", "home", "Work"), ("My tasks", "check-circle", "Work", "8"), ("Roadmap", "map", "Work"), ("Sprints", "refresh", "Work"), ("Docs", "file", "Team"), ("People", "users", "Team"), ("Reports", "chart", "Team")],
                 page("Q4 roadmap",
                      between(row(n("AvatarStack", names=PEOPLE[:7], max_=5, label="12 contributors"), badge("Sprint 23 · day 6 of 10", "info"), gap="md"), row(btn("Filter", "secondary", icon="filter"), btn("New task", "primary", icon="plus"), gap="sm")),
                      card(roadmap),
                      grid(card(chart("line", [{"day": "D%d" % (i + 1), "Remaining": r, "Ideal": d} for i, (r, d) in enumerate(zip([84, 80, 77, 70, 61, 58, 49, 40, 33, 24], [84, 75, 66, 57, 48, 39, 30, 21, 12, 3]))], "day", ["Remaining", "Ideal"], height=210, points=False, format="number"), title="Burndown", subtitle="Story points · sprint 23"),
                           card(n("BarList", items=[{"label": PEOPLE[2], "value": 34, "display": "34 pts", "detail": "Over capacity", "color": "var(--fl-danger)"}, {"label": PEOPLE[3], "value": 26, "display": "26 pts"}, {"label": PEOPLE[5], "value": 22, "display": "22 pts"}, {"label": PEOPLE[6], "value": 17, "display": "17 pts"}, {"label": PEOPLE[7], "value": 9, "display": "9 pts", "detail": "Has room"}]), title="Workload", subtitle="Assigned this sprint"),
                           card(listing([("Payment sheet: Apple and Google Pay", "Checkout redesign · Ana", "Fri", "circle", None, "In progress"), ("Backfill invoices 2019–2021", "Billing migration · Tomás", "Fri", "circle", None, "Blocked"), ("Accessibility audit fixes", "Mobile app 3.0 · Kenji", "Mon", "circle", None, "Review"), ("Publish button guidelines", "Design system · Lena", "Tue", "check-circle", "success", "Done")]), title="Due this week"), columns=3),
                      subtitle="Five workstreams · 68% of scope delivered", width="wide"),
                 user={"name": "Jonas Weber", "role": "Programme lead"}, tagline="Product")


@screen("dash/music", "Dashboards", "Tide · music streaming", theme="neon", height=1100,
        caption="A music app: generated album covers, a now-playing bar with a waveform and personal listening stats")
def music(ctx):
    albums = [("Low Tide", "Marlowe Quartet", 265, 1), ("Paper Planets", "Ines & The Orbit", 20, 2), ("Slow Glass", "Kiln", 190, 3), ("Night Bus Home", "Verano Club", 330, 4), ("Field Notes", "Oakline", 140, 5), ("Static Bloom", "Lumina", 55, 6)]
    queue = [("Harbour Lights", "Marlowe Quartet · 3:32", "Playing", "music", "brand"), ("Undertow", "Marlowe Quartet · 4:10", "4:10", "music"), ("Salt and Silver", "Marlowe Quartet · 2:58", "2:58", "music"), ("Lantern", "Kiln · 5:02", "5:02", "music"), ("Paper Planets", "Ines & The Orbit · 3:47", "3:47", "music")]
    return shell("Tide", [("Home", "home", "Listen"), ("Search", "search", "Listen"), ("Radio", "volume", "Listen"), ("Liked songs", "heart", "Library"), ("Albums", "layers", "Library"), ("Artists", "users", "Library"), ("Podcasts", "mic", "Library")],
                 page("Good evening",
                      split(stack(n("PromoTile", row(btn("Play", "primary", icon="play"), btn("Save", "secondary", icon="heart"), gap="sm"), title="Low Tide", subtitle="Marlowe Quartet · new album · 11 tracks", eyebrow="Made for a rainy Thursday", art={"kind": "waves", "hue": 265, "hue2": 200, "ratio": "21:9", "tone": "dark"}, layout="overlay", size="sm", align="start"),
                                  n("Heading", text="Jump back in", level=2),
                                  grid(*[stack(art("cover", hue=hue, seed=seed, ratio="1:1", label=title.split()[0]), stack(strong(title), muted(artist), gap="none"), gap="sm") for title, artist, hue, seed in albums], columns=6, gap="md")),
                            stack(card(n("Player", title="Harbour Lights", artist="Marlowe Quartet · Low Tide", progress=74, duration=212, playing=True, variant="large", art={"kind": "cover", "hue": 265, "seed": 1, "label": "Low"}), n("Waveform", progress=0.35, height=44, seed=4)),
                                  card(listing(queue, dense=True), title="Up next")), ratio="5:2"),
                      grid(stat("Minutes this week", "1,284", delta="+18%", icon="clock", spark=series(171, 14, 100, 1, 9)), stat("Top genre", "Modern jazz", delta="41%", trend="flat", icon="music"), stat("New artists", "12", delta="+5", icon="users"), stat("Listening streak", "36 days", delta="Best yet", icon="flame"), columns=4),
                      width="wide"),
                 user={"name": "Kenji Sato", "role": "Premium"}, tagline="Music")


@screen("dash/learning", "Dashboards", "Kindle Academy · learning", theme="candy", height=1120,
        caption="A learning platform in the Candy theme: course progress, a study streak, the week's schedule and a leaderboard")
def learning(ctx):
    course = lambda t, sub, pct, kind, hue: card(art(kind, hue=hue, ratio="21:9"), stack(strong(t), muted(sub), gap="none"), n("Progress", value=pct, label="%d%% complete" % pct, showValue=False), row(btn("Continue", "primary", size="sm"), btn("Syllabus", "ghost", size="sm"), gap="xs"), padding="sm")  # noqa: E731
    return shell("Kindle Academy", [("Dashboard", "home", "Learn"), ("My courses", "book", "Learn"), ("Schedule", "calendar", "Learn"), ("Assignments", "edit", "Learn", "3"), ("Community", "users", "More"), ("Certificates", "award", "More"), ("Tutor", "sparkles", "More")],
                 page("Welcome back, Sofia",
                      grid(course("Statistics for product teams", "Module 6 of 9 · Confidence intervals", 64, "dots", 280), course("Interface design fundamentals", "Module 3 of 8 · Type and hierarchy", 38, "blocks", 330), course("SQL from zero", "Module 8 of 10 · Window functions", 82, "grid", 200), columns=3),
                      split(card(n("Schedule", from_=9, to_=15, now="11:20", items=[{"start": "09:30", "end": "10:30", "title": "Live: confidence intervals", "detail": "Dr. Nair", "tone": "brand"}, {"start": "11:00", "end": "12:00", "title": "Study group", "detail": "Room 4", "tone": "success"},
                                                                                 {"start": "13:00", "end": "14:30", "title": "Design critique", "detail": "Bring your wireframes", "tone": "ai"}]), title="Today", subtitle="Thursday 19 November"),
                            stack(card(n("Heatmap", values=heat(181, 5, 14, 6), tone="success", rowLabels=["Mon", "Tue", "Wed", "Thu", "Fri"], shape="round"), between(strong("23-day streak"), muted("Best: 31 days")), title="Study streak", subtitle="Minutes per day, last 14 weeks"),
                                  card(n("Insight", title="You are ready for the module 6 quiz", tone="ai", body="You answered 9 of the last 10 practice questions correctly. Review margin of error once more.", bullets=[]), row(btn("Start quiz", "primary"), btn("Practice 5 more", "secondary"), gap="sm"), title="Tutor")), ratio="1:1"),
                      card(n("BarList", ranked=True, items=[{"label": "Kenji Sato", "value": 4820, "display": "4,820 XP"}, {"label": "Sofia Marin (you)", "value": 4610, "display": "4,610 XP", "color": "var(--fl-accent)"}, {"label": "Idris Bello", "value": 4190, "display": "4,190 XP"}, {"label": "Lena Fischer", "value": 3760, "display": "3,760 XP"}]), title="Cohort leaderboard", subtitle="This month"),
                      subtitle="You are two lessons ahead of your plan", width="wide"),
                 user={"name": "Sofia Marin", "role": "Cohort 12"}, tagline="Learning")


@screen("dash/logistics", "Dashboards", "Halden · fleet and logistics", theme="tangerine", height=1140,
        caption="Fleet operations: live routes on the generated map, on-time performance and shipments that need attention")
def logistics(ctx):
    ships = [{"id": "HL-48213", "route": "Porto → Madrid", "driver": "Tomás Rey", "eta": "14:20", "load": "82%", "status": "On time"}, {"id": "HL-48214", "route": "Lyon → Milan", "driver": "Lena Fischer", "eta": "16:05", "load": "64%", "status": "Delayed"},
             {"id": "HL-48215", "route": "Hamburg → Prague", "driver": "Omar Haddad", "eta": "15:40", "load": "91%", "status": "On time"}, {"id": "HL-48216", "route": "Vienna → Zagreb", "driver": "Idris Bello", "eta": "13:55", "load": "77%", "status": "Delivered"},
             {"id": "HL-48217", "route": "Antwerp → Paris", "driver": "Priya Nair", "eta": "17:30", "load": "58%", "status": "Blocked"}]
    live = n("MapView", kind="city", height=430, seed=3, routes=[{"points": [[8, 82], [24, 68], [41, 60], [58, 44], [74, 38], [90, 20]]}, {"points": [[14, 20], [30, 34], [46, 30], [60, 62], [82, 74]], "tone": "success"}, {"points": [[52, 88], [56, 70], [70, 58]], "tone": "warning", "dashed": True}],
             pins=[{"x": 58, "y": 44, "label": "HL-48213 · 62 km/h", "pulse": True, "size": 8}, {"x": 60, "y": 62, "label": "HL-48215", "tone": "success", "pulse": True}, {"x": 56, "y": 70, "label": "HL-48214 · stopped 18 min", "tone": "warning", "pulse": True}, {"x": 90, "y": 20, "label": "Madrid hub", "tone": "neutral"}])
    return shell("Halden", [("Live map", "map", "Operations"), ("Shipments", "truck", "Operations", "214"), ("Drivers", "users", "Operations"), ("Vehicles", "car", "Operations"), ("Routes", "route", "Planning"), ("Warehouses", "building", "Planning"), ("Reports", "chart", "Planning")],
                 page("Fleet today",
                      kpis(("Active vehicles", "184", "of 212", "86% utilised", "truck", 191), ("On-time rate", "94.2%", "+1.8 pts", "vs last week", "clock", 192), ("Deliveries", "1,482", "+6%", "by 13:00", "box", 193), ("Fuel per 100 km", "27.4 L", "-1.1 L", "eco-routing on", "droplet", 194)),
                      split(card(live, padding="none"),
                            stack(card(row(n("Gauge", value=94.2, display="94%", label="On time", detail="Target 92%", tone="success", size=160), justify="center"), title="Service level"),
                                  n("Insight", title="Reroute HL-48214 via the A7", tone="ai", body="An accident near Chambéry adds 52 minutes. The A7 saves 31 of them and keeps the delivery window.", bullets=[]),
                                  card(listing([("Tyre pressure low", "Vehicle 118 · rear left", "Now", "alert", "warning"), ("Driver hours", "Priya Nair reaches the limit at 16:10", "2h", "clock", "danger"), ("Dock 4 free", "Madrid hub", "5m", "check", "success")], dense=True), title="Alerts")), ratio="2:1"),
                      card(table([("id", "Shipment"), ("route", "Route"), ("driver", "Driver"), ("eta", "ETA"), ("load", "Load", None, "end"), ("status", "Status", "badge")], ships, dense=True), title="Shipments in motion", padding="none"),
                      subtitle="212 vehicles · 9 countries · weather clear", width="wide"),
                 user={"name": "Omar Haddad", "role": "Dispatcher"}, tagline="Fleet")


@screen("dash/clinic", "Dashboards", "Oakline · clinic operations", theme="mint", height=1180,
        caption="A clinic day view in the Mint theme: appointments across rooms, a waiting list and capacity at a glance")
def clinic(ctx):
    appts = [{"start": "08:30", "end": "09:15", "title": "A. Lima · follow-up", "tone": "brand", "lane": 0}, {"start": "09:30", "end": "10:30", "title": "K. Sato · physiotherapy", "tone": "success", "lane": 1}, {"start": "09:00", "end": "09:40", "title": "P. Nair · bloods", "tone": "info", "lane": 2},
             {"start": "10:00", "end": "11:00", "title": "T. Rey · consultation", "tone": "brand", "lane": 0}, {"start": "11:00", "end": "11:45", "title": "L. Fischer · imaging", "tone": "warning", "lane": 2}, {"start": "11:30", "end": "12:30", "title": "O. Haddad · review", "tone": "brand", "lane": 0},
             {"start": "10:45", "end": "12:00", "title": "S. Marin · rehabilitation", "tone": "success", "lane": 1}, {"start": "13:00", "end": "13:45", "title": "I. Bello · vaccination", "tone": "info", "lane": 2}, {"start": "13:15", "end": "14:15", "title": "M. Okafor · annual check", "tone": "brand", "lane": 0}]
    return shell("Oakline Health", [("Today", "calendar", "Clinic"), ("Patients", "users", "Clinic"), ("Appointments", "clock", "Clinic"), ("Messages", "message", "Clinic", "5"), ("Lab results", "activity", "Clinical"), ("Prescriptions", "pill", "Clinical"), ("Billing", "receipt", "Admin")],
                 page("Thursday clinic",
                      kpis(("Appointments", "42", "6 remaining", "before lunch", "calendar"), ("Average wait", "8 min", "-3 min", "vs last week", "clock", 201), ("Rooms in use", "5 of 7", "71%", "utilisation", "building"), ("No-shows", "2", "4.8%", "below target", "x-circle")),
                      split(card(n("Schedule", from_=8, to_=15, now="10:20", lanes=["Dr. Weber · Room 1", "Physio · Room 3", "Nurse station"], items=appts, rowHeight=58), title="Schedule", subtitle="Three rooms · tap an appointment to open the record"),
                            stack(card(listing([("Ana Lima", "Arrived 08:22 · follow-up", "Now", "Ana Lima", None, "In room"), ("Priya Nair", "Arrived 08:51 · bloods", "4 min", "Priya Nair", None, "Waiting"), ("Kenji Sato", "Checked in online", "12 min", "Kenji Sato", None, "Waiting"), ("Tomás Rey", "Running late · called", "—", "Tomás Rey", None, "Delayed")]), title="Waiting room"),
                                  card(row(n("Gauge", value=71, display="71%", label="Capacity", detail="5 of 7 rooms", size=150), n("Gauge", value=92, display="92%", label="Satisfaction", detail="Last 30 days", tone="success", size=150), justify="center", gap="lg"), title="At a glance"),
                                  n("Insight", title="Move the 11:30 review to Room 2", tone="ai", body="Dr. Weber is running 14 minutes behind. Room 2 is free and avoids delaying three later patients.", bullets=[])), ratio="5:3"),
                      subtitle="19 November · Dr. Weber, two nurses and one physiotherapist on shift", width="wide"),
                 user={"name": "Jonas Weber", "role": "Physician"}, tagline="Clinic")


@screen("dash/energy", "Dashboards", "Solstice · solar and energy", theme="citrus", height=1120,
        caption="A home energy dashboard in the Citrus theme: production against use, battery state and panel output")
def energy(ctx):
    hours = list(range(5, 22))
    day = [{"h": "%02d:00" % h, "Solar": round(max(0, 4.2 - abs(13 - h) ** 1.7 * 0.16), 2), "Use": u} for h, u in zip(hours, [0.4, 0.5, 1.2, 1.6, 0.9, 0.7, 0.6, 0.8, 1.1, 0.7, 0.6, 0.9, 1.8, 2.6, 2.2, 1.4, 0.8])]
    return shell("Solstice", [("Overview", "home", "Energy"), ("Production", "sun", "Energy"), ("Battery", "battery", "Energy"), ("Consumption", "plug", "Energy"), ("Savings", "dollar", "Insights"), ("Forecast", "sun-cloud", "Insights"), ("System", "settings", "Insights")],
                 page("Your home is running on sunshine",
                      kpis(("Produced today", "24.8 kWh", "+12%", "vs forecast", "sun", 211), ("Used today", "16.1 kWh", "-8%", "vs average", "plug", 212), ("Exported", "6.2 kWh", "+$1.86", "feed-in", "arrow-up"), ("Self-powered", "87%", "+9 pts", "this week", "leaf", 214)),
                      split(card(chart("area", day, "h", ["Solar", "Use"], height=280, format="number"), title="Production and use", subtitle="Kilowatts through the day"),
                            stack(card(row(n("Gauge", value=82, display="82%", label="Battery", detail="Full by 15:10", tone="success", size=180), justify="center"), n("KeyValue", columns=2, items=[{"key": "Stored", "value": "11.1 kWh"}, {"key": "Backup time", "value": "14 hours"}]), title="Storage"),
                                  n("Insight", title="Run the dishwasher before 16:00", tone="ai", body="Clouds arrive at 16:30. Shifting two appliances keeps you off the grid tonight and saves about $0.90.", bullets=[])), ratio="5:3"),
                      split(card(n("Heatmap", values=heat(215, 4, 12, 10), tone="warning", shape="square", rowLabels=["A", "B", "C", "D"]), between(muted("48 panels · darker is higher output"), badge("Panel C7 is 22% low", "warning", icon="alert")), title="Array output"),
                            card(chart("bar", [{"month": m, "Saved": v} for m, v in zip(MONTHS[:11], [38, 52, 81, 104, 132, 148, 156, 141, 112, 78, 49])], "month", "Saved", height=200, legend=False, format="currency"), title="Savings this year", subtitle="$1,091 so far"), ratio="1:1"),
                      subtitle="Clear skies until 16:30 · 8.4 kW array · 13.5 kWh battery", width="wide"),
                 user={"name": "Lena Fischer", "role": "Home"}, tagline="Energy")


@screen("dash/social", "Dashboards", "Bloom · creator analytics", theme="rose", height=1160,
        caption="Creator analytics in the Rose theme: audience growth, the best time to post and top content with generated thumbnails")
def social(ctx):
    posts = [("Studio tour: how I light a small room", "Video · 2 days ago", "184k views", {"kind": "orbs", "hue": 340}), ("Five colour palettes for autumn", "Carousel · 4 days ago", "96k views", {"kind": "blocks", "hue": 20}), ("Sketching the coast in ten minutes", "Reel · 1 week ago", "241k views", {"kind": "coast", "hue": 330, "hue2": 30})]
    return shell("Bloom", [("Overview", "home", "Insights"), ("Content", "image", "Insights"), ("Audience", "users", "Insights"), ("Schedule", "calendar", "Publish"), ("Inbox", "message", "Publish", "24"), ("Earnings", "dollar", "Grow"), ("Brand deals", "briefcase", "Grow")],
                 page("Your week",
                      kpis(("Followers", "128,400", "+3,210", "this week", "users", 221), ("Reach", "1.84M", "+22%", "vs last week", "eye", 222), ("Engagement", "6.8%", "+0.9 pts", "likes, saves, shares", "heart", 223), ("Earnings", "$4,260", "+$640", "this month", "dollar", 224)),
                      split(card(chart("area", [{"day": "%d Nov" % d, "Followers": v} for d, v in zip(range(6, 20), series(225, 14, 118000, 760, 400))], "day", "Followers", height=250, legend=False, baseline="auto"), title="Audience growth", subtitle="Followers across all platforms"),
                            card(n("Heatmap", values=heat(226, 7, 12, 10), rowLabels=DAYS, colLabels=["6", "", "10", "", "14", "", "18", "", "22", "", "2", ""], tone="brand"), n("Insight", title="Post on Sunday at 18:00", tone="ai", body="Your audience is 2.4× more active then than at your usual Tuesday slot.", bullets=[]), title="When your audience is online"), ratio="5:4"),
                      grid(*[card(art(ratio="16:9", **spec), stack(strong(t), between(muted(d), badge(v, "brand")), gap="xs"), padding="sm") for t, d, v, spec in posts], columns=3),
                      subtitle="12 – 19 November · all platforms", width="wide"),
                 user={"name": "Sofia Marin", "role": "Creator"}, tagline="Creator studio")


@screen("dash/support", "Dashboards", "Harbor · support desk", theme="sky", height=1160,
        caption="A support desk in the Sky theme: queue health, a live conversation and a reply drafted by the assistant")
def support(ctx):
    queue = [("Refund not received after 10 days", "Kenji Sato · Billing · waited 2h 14m", "Urgent", "Kenji Sato", None, "Overdue"), ("Cannot add a second workspace", "Priya Nair · Account · waited 38m", "High", "Priya Nair", None, "Open"),
             ("Export to CSV drops accents", "Tomás Rey · Bug · waited 21m", "Normal", "Tomás Rey", None, "Open"), ("How do I change the invoice address?", "Lena Fischer · Billing · waited 9m", "Low", "Lena Fischer", None, "New"), ("Feature request: dark mode schedule", "Idris Bello · Feedback · waited 4m", "Low", "Idris Bello", None, "New")]
    convo = n("Chat", title="Kenji Sato", subtitle="Pro plan · customer since 2023 · 3 previous tickets", status="online", actions=["phone", "more"], placeholder="Reply to Kenji…", messages=[
        {"from": "them", "text": "Hi, I cancelled on the 8th and was told I'd get a refund in 5 working days. It's been ten. Can you check?", "time": "13:02"},
        {"from": "system", "text": "Ana Lima joined the conversation"},
        {"from": "me", "text": "Hi Kenji, I'm sorry about the wait. I'm looking at the payment record now.", "time": "13:04", "status": "read"},
        {"from": "ai", "tool": {"label": "Looked up refund", "detail": "re_48213", "icon": "search"}, "rich": True, "text": "The refund of **$249.00** was issued on 9 Nov but bounced: the card ending 4821 expired in October. It can be re-issued to a new card or by bank transfer.",
         "chips": ["Use this reply", "Offer bank transfer", "Add a $25 credit"]}])
    return shell("Harbor", [("Inbox", "inbox", "Support", "18"), ("Mine", "user", "Support", "5"), ("Unassigned", "users", "Support", "7"), ("Overdue", "clock", "Support", "2"), ("Knowledge base", "book", "Resources"), ("Macros", "bolt", "Resources"), ("Reports", "chart", "Resources")],
                 page("Support",
                      kpis(("Open tickets", "64", "-11", "since Monday", "inbox", 231), ("First response", "6m 20s", "-1m 05s", "median today", "clock", 232), ("Resolved by AI", "41%", "+6 pts", "this week", "sparkles", 233), ("Satisfaction", "96%", "+1 pt", "last 30 days", "smile", 234)),
                      split(card(listing(queue), title="Queue", subtitle="Sorted by urgency and wait"),
                            convo,
                            stack(card(n("KeyValue", items=[{"key": "Plan", "value": "Pro · $249 / year"}, {"key": "Lifetime value", "value": "$747"}, {"key": "Sentiment", "value": "Frustrated, polite"}, {"key": "SLA", "value": "Breached by 14 min"}]), title="Customer"),
                                  card(n("Gauge", value=92, display="92%", label="SLA attainment", detail="Target 90%", tone="success", size=150), title="Today")), ratio="4:5:3", gap="md"),
                      subtitle="18 conversations waiting · 6 agents online", width="full"),
                 user={"name": "Ana Lima", "role": "Support lead"}, tagline="Support")
