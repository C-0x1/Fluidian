"""Mobile apps and cross-platform previews."""
from kit import *  # noqa: F401,F403

TABS = [("Home", "home"), ("Cards", "card"), ("Pay", "swap"), ("Insights", "pie"), ("Profile", "user")]


def tabbar(items, active=0):
    return [{"label": l, "icon": i, "active": k == active} for k, (l, i) in enumerate(items)]


def stage(title, subtitle, *devices, eyebrow="One scene · every platform", backdrop="mesh"):
    """A presentation stage: a heading with devices lined up beneath it."""
    return n("Landing", n("Band", row(*devices, justify="center", align="start", gap="xl", wrap=False), title=title, subtitle=subtitle, eyebrow=eyebrow, pad="sm", width="wide"), backdrop=backdrop)


def banking():
    tx = [{"title": "Verano Coffee", "detail": "Today · 08:14", "meta": "-$4.80", "icon": "coffee"}, {"title": "Salary · Arcwell Ltd", "detail": "Yesterday", "meta": "+$4,250.00", "icon": "briefcase", "tone": "success"},
          {"title": "Kestrel Energy", "detail": "Mon · Direct debit", "meta": "-$86.20", "icon": "bolt"}, {"title": "Oakline Market", "detail": "Sun · Groceries", "meta": "-$63.15", "icon": "shopping-bag"}]
    return n("Screen", art("card", hue=265, hue2=205, ratio="16:9", label="4821", rounded=True),
             grid(stat("Balance", "$12,480.55", delta="+2.1%", hint="this month"), stat("Spent", "$1,932", delta="-8%", trend="down", hint="vs October"), columns=2, minWidth=130, gap="sm"),
             row(btn("Send", "primary", icon="arrow-up"), btn("Request", "secondary", icon="arrow-down"), btn("Top up", "secondary", icon="plus"), gap="xs", wrap=False),
             card(n("List", items=tx, dense=False), title="Recent", padding="sm"),
             title="Good morning", subtitle="Mira Okafor", trailing=["bell"], avatar="Mira Okafor", tabs=tabbar(TABS), fab={"icon": "qr"})


@screen("mobile/banking", "Mobile and cross-platform", "Banking app · iOS and Android", theme="deep", height=1000,
        caption="One banking scene rendered with the iOS skin, the Android skin and a dark theme: no platform-specific code")
def mobile_banking(ctx):
    return stage("One scene. Native on every platform.", "The same Python function renders with a large-title iOS layout, a Material layout on Android and any theme you choose.",
                 phone(banking(), platform="ios", caption="iOS"), phone(banking(), platform="android", caption="Android"), phone(banking(), platform="ios", theme="midnight", caption="iOS · Midnight theme"))


def duo(build, third=None, **stage_args):
    devices = [phone(build(), platform="ios", caption="iOS"), phone(build(), platform="android", caption="Android")]
    if third:
        devices.append(third)
    return devices


def chips(labels, active=0):
    return row(*[n("Button", label=l, variant="primary" if i == active else "secondary", size="sm") for i, l in enumerate(labels)], gap="xs", wrap=False)


def fitness():
    return n("Screen", card(n("Rings", size=150, center="78%", items=[{"label": "Move", "value": 468, "max": 600, "display": "468 kcal"}, {"label": "Train", "value": 34, "max": 40, "display": "34 min"}, {"label": "Stand", "value": 9, "max": 12, "display": "9 h"}])),
             grid(stat("Heart rate", "62 bpm", delta="Resting", trend="flat"), stat("Sleep", "7h 42m", delta="+38m"), columns=2, minWidth=120, gap="sm"),
             card(chart("bar", [{"d": d[0], "min": v} for d, v in zip(DAYS, [32, 45, 12, 51, 38, 64, 22])], "d", "min", height=120, legend=False), title="Active minutes"),
             btn("Start a workout", "primary", size="lg", block=True, icon="play"),
             title="Today", subtitle="Thursday 19 November", avatar="Ana Lima", tabs=tabbar([("Today", "activity"), ("Train", "dumbbell"), ("Sleep", "moon"), ("You", "user")]))


@screen("mobile/fitness", "Mobile and cross-platform", "Fitness tracker · iOS and Android", theme="ember", height=1000,
        caption="A fitness tracker in the Ember theme on both platforms, with rings, stats and a weekly chart")
def mobile_fitness(ctx):
    return stage("Rings on iOS. Rings on Android.", "Charts, rings and cards are the same components everywhere. Only the platform conventions around them change.", *duo(fitness), phone(fitness(), platform="android", theme="citrus", caption="Android · Citrus theme"))


def food():
    place = lambda name, meta, kind, hue, badge_=None: card(art(kind, hue=hue, ratio="21:9", seed=hue), between(stack(strong(name), muted(meta), gap="none"), badge(badge_ or "4.8 ★", "success" if badge_ else "neutral")), padding="sm")  # noqa: E731
    return n("Screen", n("Search", name="q", placeholder="Dishes, restaurants, cuisines"), chips(["For you", "Burgers", "Bowls", "Sushi", "Pizza"]),
             place("Verano Burger Bar", "Burgers · 20–30 min · $1.99 delivery", "burger", 35, "Free delivery"), place("Kiln Bowls", "Healthy · 15–25 min · $0.99 delivery", "dish", 140), place("Oakline Kitchen", "Mediterranean · 25–35 min", "dish", 20),
             title="Pico", subtitle="Deliver to Rua das Flores 28", trailing=["bell"], tabs=tabbar([("Home", "home"), ("Search", "search"), ("Orders", "receipt"), ("Account", "user")]), fab={"icon": "shopping-bag", "label": "2 · $24.80"})


@screen("mobile/food", "Mobile and cross-platform", "Food delivery · iOS and Android", theme="sunset", height=1000,
        caption="A food delivery app in the Sunset theme: generated dishes, quick filters and a floating basket")
def mobile_food(ctx):
    return stage("Dinner, on any phone.", "The floating basket is a circle on iOS and a tonal extended button on Android. You wrote one line for it.", *duo(food), phone(food(), platform="ios", theme="moss", caption="iOS · Moss theme"))


def trip():
    return n("Screen", art("coast", hue=215, hue2=30, ratio="16:9"),
             card(between(stack(muted("OPO · Porto", "xs"), strong("09:40", "xl"), gap="none"), n("Icon", name="plane", size=22, tone="brand"), stack(muted("LIS · Lisbon", "xs"), strong("10:35", "xl"), gap="none", align="end")),
                  between(stack(muted("Gate", "xs"), strong("B14"), gap="none"), stack(muted("Seat", "xs"), strong("12A"), gap="none"), stack(muted("Boarding", "xs"), strong("09:10"), gap="none"), art("qr", ratio="1:1", seed=4, width=64)), title="Flight VY 214", subtitle="Thursday 19 November"),
             card(n("Timeline", items=[{"title": "Check in at Casa do Rio", "time": "14:00", "tone": "brand", "icon": "bed"}, {"title": "Tile workshop in Alfama", "time": "16:30", "tone": "ai", "icon": "palette"}, {"title": "Dinner · Taberna Verano", "time": "20:00", "tone": "success", "icon": "utensils"}]), title="Today"),
             title="Lisbon", subtitle="4 nights · 19 – 23 November", leading="arrow-left", trailing=["share"], tabs=tabbar([("Trips", "map"), ("Explore", "compass"), ("Saved", "heart"), ("Profile", "user")]))


@screen("mobile/travel", "Mobile and cross-platform", "Travel companion · iOS and Android", theme="sky", height=1000,
        caption="A trip screen with a generated landscape, a boarding pass and the day's plan")
def mobile_travel(ctx):
    return stage("A boarding pass that fits every pocket.", "Landscape, QR code and timeline are drawn by the framework. No image files ship with this screen.", *duo(trip), phone(trip(), platform="ios", theme="gold", caption="iOS · Gold theme"))


def playing():
    return n("Screen", n("Player", title="Harbour Lights", artist="Marlowe Quartet · Low Tide", progress=74, duration=212, playing=True, variant="large", art={"kind": "cover", "hue": 265, "seed": 1, "label": "Low"}),
             n("Waveform", progress=0.35, height=40, seed=4, bars=48),
             card(n("List", dense=True, items=[{"title": "Undertow", "detail": "Marlowe Quartet", "meta": "4:10", "icon": "music"}, {"title": "Salt and Silver", "detail": "Marlowe Quartet", "meta": "2:58", "icon": "music"}, {"title": "Lantern", "detail": "Kiln", "meta": "5:02", "icon": "music"}]), title="Up next", padding="sm"),
             title="Now playing", large=False, leading="chevron-down", trailing=["more"], tabs=tabbar([("Home", "home"), ("Search", "search"), ("Library", "layers")], active=2))


@screen("mobile/music", "Mobile and cross-platform", "Music player · iOS and Android", theme="grape", height=1000,
        caption="A music player with generated cover art, transport controls and a waveform")
def mobile_music(ctx):
    return stage("Press play anywhere.", "Cover art is generated from a seed, so every album is unique and nothing needs licensing.", *duo(playing), phone(playing(), platform="android", theme="crimson", caption="Android · Crimson theme"))


def inbox():
    people = [("Ana Lima", "The payment sheet is ready for review", "09:41", "2"), ("Design team", "Kenji: pushed the new icons", "09:20", "5"), ("Jonas Weber", "Friday 09:30 works for me", "Yesterday", None), ("Priya Nair", "Sent you the retention chart", "Yesterday", None), ("Tomás Rey", "On my way, 6 stops left", "Tue", None), ("Lena Fischer", "Thanks! That fixed it", "Mon", None)]
    return n("Screen", n("Search", name="q", placeholder="Search"), n("AvatarStack", names=PEOPLE[:6], max_=6, size="lg"),
             card(n("List", items=[{"title": who, "detail": last, "meta": when, "avatar": who, **({"badge": count, "tone": "brand"} if count else {})} for who, last, when, count in people]), padding="sm"),
             title="Messages", trailing=["edit"], tabs=tabbar([("Chats", "message"), ("Calls", "phone"), ("People", "users"), ("Settings", "settings")]), fab={"icon": "pen"})


def conversation():
    return n("Screen", n("Chat", variant="flat", avatars=False, placeholder="Message", messages=[{"from": "system", "text": "Today"}, {"from": "them", "text": "The payment sheet is ready for review.", "time": "09:38"},
                                                                                               {"from": "me", "text": "Brilliant. Does it cover Apple and Google Pay?", "time": "09:39", "status": "read"}, {"from": "them", "text": "Both. Accessibility fixes land tomorrow.", "time": "09:40"},
                                                                                               {"from": "ai", "rich": True, "text": "**Suggested reply:** “Great — let's do the go or no-go on Friday at 09:30.”", "chips": ["Send", "Make it warmer"]}]),
             title="Ana Lima", subtitle="Online", large=False, leading="arrow-left", trailing=["phone", "video"])


@screen("mobile/chat", "Mobile and cross-platform", "Messaging · list and conversation", theme="mint", height=1000,
        caption="A messaging app: the inbox on iOS and a conversation on Android, with an AI-suggested reply inline")
def mobile_chat(ctx):
    return stage("Conversations, with a little help.", "The suggested reply comes from the AI kernel and works offline. The bubbles follow each platform's conventions.",
                 phone(inbox(), platform="ios", caption="iOS · inbox"), phone(conversation(), platform="android", caption="Android · conversation"), phone(conversation(), platform="ios", theme="midnight", caption="iOS · Midnight theme"))


def weather(variant="partly", temp="14°", place="Porto"):
    hours = [("Now", "partly", "14°"), ("15", "sun", "15°"), ("16", "sun", "15°"), ("17", "cloud", "13°"), ("18", "rain", "11°")]
    week = [("Friday", "Showers", "12° / 8°", "rain"), ("Saturday", "Sunny", "16° / 9°", "sun"), ("Sunday", "Partly cloudy", "15° / 10°", "sun-cloud"), ("Monday", "Windy", "13° / 7°", "wind"), ("Tuesday", "Rain", "11° / 6°", "rain")]
    return n("Screen", art("weather", variant=variant, hue=215, hue2=265, ratio="16:9"),
             stack(strong(temp, "xl"), muted("Partly cloudy · feels like 13°", "md"), gap="none", align="center"),
             card(grid(*[stack(muted(t, "xs"), art("weather", variant=v, hue=215, hue2=250, ratio="1:1"), strong(d), gap="xs", align="center") for t, v, d in hours], columns=5, minWidth=44, gap="xs"), padding="sm"),
             card(n("List", dense=True, items=[{"title": d, "detail": s, "meta": t, "icon": i} for d, s, t, i in week]), title="This week", padding="sm"),
             title=place, subtitle="Thursday 19 November", trailing=["search"], tabs=tabbar([("Today", "sun"), ("Radar", "map"), ("Places", "pin")]))


@screen("mobile/weather", "Mobile and cross-platform", "Weather · iOS and Android", theme="abyss", height=1000,
        caption="A weather app whose icons and skies are all generated artwork")
def mobile_weather(ctx):
    return stage("Forecasts without a single image file.", "Sun, cloud, rain and moon are drawn by the Art component and recoloured by the theme.", phone(weather(), platform="ios", caption="iOS"), phone(weather("rain", "11°", "Bergen"), platform="android", caption="Android"),
                 phone(weather("moon", "9°", "Oslo"), platform="ios", theme="midnight", caption="iOS · Midnight theme"))


def habits():
    return n("Screen", card(between(stack(strong("23-day streak", "lg"), muted("Your best is 31 days"), gap="none"), n("Rings", size=76, legend=False, center="4/5", items=[{"label": "Today", "value": 4, "max": 5}])),
                            n("Heatmap", values=[[3, 4, 4, 5, 2, 0, 4], [5, 5, 3, 4, 4, 1, 3], [4, 5, 5, 5, 3, 2, 5], [5, 4, 5, 4, 0, 0, 0]], max_=5, tone="success", shape="round")),
             card(n("Checkbox", name="h1", label="Read for 20 minutes", checked=True, help="Done at 07:40"), n("Checkbox", name="h2", label="Walk 8,000 steps", checked=True, help="9,412 today"), n("Checkbox", name="h3", label="No phone after 22:00", help="Reminder at 21:45"),
                  n("Checkbox", name="h4", label="Practise Portuguese", checked=True, help="Lesson 42"), n("Checkbox", name="h5", label="Stretch", checked=True), title="Today", padding="sm"),
             n("Insight", title="You skip reading on Fridays", tone="ai", body="Try moving it to lunchtime: you have kept every midday habit this month.", bullets=[]),
             title="Habits", avatar="Sofia Marin", tabs=tabbar([("Today", "check-circle"), ("Stats", "chart"), ("Goals", "target")]), fab={"icon": "plus"})


@screen("mobile/habits", "Mobile and cross-platform", "Habit tracker · iOS and Android", theme="citrus", height=1000,
        caption="A habit tracker with a streak heatmap, a checklist and a nudge from the AI kernel")
def mobile_habits(ctx):
    return stage("Small habits, native feel.", "Checkboxes, heatmaps and the AI insight are identical components. The frame, type and navigation follow the platform.", *duo(habits), phone(habits(), platform="ios", theme="rose", caption="iOS · Rose theme"))


def smart_home():
    tile = lambda t, i, on, v, tone="brand": n("ControlTile", title=t, icon=i, on=on, value=v, tone=tone)  # noqa: E731
    return n("Screen", chips(["Evening", "Movie", "Away", "Morning"]), card(row(n("Gauge", value=21.5, max_=30, display="21.5°", label="Living room", detail="Heating to 22°", tone="warning", size=150), justify="center"), padding="sm"),
             grid(tile("Lights", "bulb", True, "70% · warm", "warning"), tile("Front door", "lock", True, "Locked", "success"), tile("Speakers", "speaker", True, "Low Tide"), tile("Heating", "flame", False, "Eco"), columns=2, minWidth=130, gap="sm"),
             title="Home", subtitle="Everything is locked", avatar="Mira Okafor", tabs=tabbar([("Home", "home"), ("Rooms", "grid"), ("Energy", "bolt"), ("More", "more")]))


@screen("mobile/home", "Mobile and cross-platform", "Smart home · iOS and Android", theme="lagoon", height=1000,
        caption="Smart-home controls: toggle tiles, a thermostat gauge and scene shortcuts on both platforms")
def mobile_home(ctx):
    return stage("One home, every handset.", "Toggle tiles keep their state in the runtime, so they respond instantly without a round trip.", *duo(smart_home), phone(smart_home(), platform="android", theme="forest", caption="Android · Forest theme"))


def shop():
    item = lambda nm, pr, kind, hue: n("ProductCard", name=nm, price=pr, art={"kind": kind, "hue": hue, "ratio": "1:1"}).on("add", "@toast 'Added' success")  # noqa: E731
    return n("Screen", n("Search", name="q", placeholder="Search Maison Olea"), n("PromoTile", title="The autumn ritual", subtitle="Four formulas, one calm routine", art={"kind": "bottle", "hue": 300, "ratio": "16:9", "bare": True}, size="sm", tone="tint"),
             grid(item("Night Serum", "$64", "bottle", 300), item("Cloud Cream", "$48", "jar", 30), item("Cleanser", "$32", "tube", 150), item("Ember Candle", "$38", "candle", 55), columns=2, minWidth=130, gap="sm"),
             title="Shop", trailing=["heart"], tabs=tabbar([("Shop", "store"), ("Rituals", "sparkles"), ("Bag", "shopping-bag"), ("You", "user")]))


@screen("mobile/shop", "Mobile and cross-platform", "Storefront · iOS and Android", theme="ruby", height=1000,
        caption="The Maison Olea storefront on phones: the same product cards as the website, reflowed")
def mobile_shop(ctx):
    return stage("Your storefront, already mobile.", "These are the product cards from the desktop storefront. Inside a phone frame they reflow on their own.", *duo(shop), phone(shop(), platform="ios", theme="rose", caption="iOS · Rose theme"))


def overview():
    return n("Page", grid(stat("Revenue", "$284k", delta="+6.0%", spark=series(401, 12, 100, 2, 5)), stat("Active users", "48,210", delta="+9.2%", spark=series(402, 12, 100, 2, 6)), stat("Retention", "41.8%", delta="+1.4 pts"), columns=3),
             card(chart("area", [{"week": "W%d" % (i + 1), "Signups": v} for i, v in enumerate(series(403, 10, 900, 60, 90))], "week", "Signups", height=170, legend=False), title="Growth"),
             card(n("BarList", items=[{"label": "/dashboard", "value": 182}, {"label": "/reports", "value": 96}, {"label": "/settings", "value": 51}]), title="Most used"), title="Overview", subtitle="Last 30 days")


@screen("mobile/platforms", "Mobile and cross-platform", "One scene on phone, tablet and web", theme="emerald", height=1930,
        caption="The same dashboard scene in a phone, a tablet and a browser: layout adapts to the frame, not just the window")
def platforms(ctx):
    return n("Landing", n("Band", row(phone(overview(), platform="ios", caption="Phone · iOS", height=640), n("DeviceFrame", overview(), kind="tablet", platform="android", caption="Tablet · Android", width=520, height=640), justify="center", align="start", gap="xl", wrap=False),
                          browser(overview(), url="app.orbit.example/overview", caption="Browser · web"),
                          title="Write the scene once. It lands everywhere.", subtitle="Container queries make every component respond to the space it is given: three columns in a browser, two on a tablet, one on a phone.", eyebrow="Cross-platform", pad="sm", width="wide"), backdrop="glow")


def themed(theme, platform):
    return phone(n("Screen", stat("Balance", "$12,480.55", delta="+2.1%", hint="this month", spark=series(410, 12, 100, 2, 5)), card(n("Rings", size=96, center="72%", items=[{"label": "Saved", "value": 72}, {"label": "Budget", "value": 54}])),
                   row(btn("Send", "primary", icon="arrow-up"), btn("Request", "secondary", icon="arrow-down"), gap="xs", wrap=False), n("Progress", label="Holiday fund", value=64),
                   title="Wallet", tabs=tabbar([("Home", "home"), ("Pay", "swap"), ("You", "user")])), platform=platform, theme=theme, caption=theme.capitalize(), scale=0.78, height=640)


@screen("mobile/themes", "Mobile and cross-platform", "One screen, eight themes", theme="paper", height=1260,
        caption="One wallet screen in eight of the twenty-seven built-in themes, alternating the iOS and Android skins")
def mobile_themes(ctx):
    names = ["deep", "neon", "tangerine", "emerald", "candy", "abyss", "ruby", "lagoon"]
    return n("Landing", n("Band", row(*[themed(t, "ios" if i % 2 == 0 else "android") for i, t in enumerate(names[:4])], justify="center", gap="lg", wrap=False), row(*[themed(t, "ios" if i % 2 else "android") for i, t in enumerate(names[4:])], justify="center", gap="lg", wrap=False),
                          title="Twenty-seven themes. Zero redesign.", subtitle="Each theme is a set of design tokens generated in OKLCH and checked for contrast. Switching one is a single prop.", eyebrow="Theming", pad="sm", width="wide"))


def onboard(step):
    pages = [("Money that explains itself", "See where every dollar went, in plain language.", {"kind": "orbs", "hue": 265}), ("Stay ahead of bills", "Get a nudge before anything is due.", {"kind": "rings", "hue": 190}), ("Private by design", "Your data is processed on your device first.", {"kind": "facets", "hue": 150, "seed": 3})]
    title, body, spec = pages[step]
    return n("Screen", art(ratio="1:1", **spec), stack(heading(title, 1), muted(body, "lg"), gap="sm"), n("Steps", current=step, items=[{"title": ""}, {"title": ""}, {"title": ""}]),
             stack(btn("Continue" if step < 2 else "Get started", "primary", size="lg", block=True), btn("Skip", "ghost", block=True) if step < 2 else btn("I already have an account", "ghost", block=True), gap="xs"), title="", large=False)


@screen("mobile/onboarding", "Mobile and cross-platform", "Onboarding flow", theme="tangerine", height=1000,
        caption="A three-step onboarding flow with generated illustrations")
def mobile_onboarding(ctx):
    return stage("A first run worth finishing.", "Three screens, three generated illustrations and one Steps component. The whole flow is 14 lines of Python.", phone(onboard(0), platform="ios", caption="Step 1"), phone(onboard(1), platform="ios", caption="Step 2"), phone(onboard(2), platform="android", caption="Step 3 · Android"))


def signin():
    return n("Screen", art("mesh", ratio="21:9"), stack(heading("Welcome back", 1), muted("Sign in to Northbank", "md"), gap="xs"), field("Email", "email", "mira@arcwell.example", kind="email", icon="mail"), field("Password", "password", "••••••••••", kind="password", icon="lock"),
             btn("Sign in", "primary", size="lg", block=True), n("Divider", label="or"), btn("Use a passkey", "secondary", size="lg", block=True, icon="fingerprint"), btn("Continue with single sign-on", "secondary", size="lg", block=True, icon="key"), title="", large=False)


def otp():
    return n("Screen", stack(n("Icon", name="smartphone", size=40, tone="brand"), heading("Check your phone", 1), muted("We sent a 6-digit code to the number ending in 0134.", "md"), gap="sm"), n("PinInput", name="code", value="4821", length=6),
             btn("Verify", "primary", size="lg", block=True), row(muted("Didn't get it?"), n("Link", label="Resend in 0:24", href="#"), gap="xs", justify="center"), n("Callout", title="Never share this code", body="Northbank will never ask for it by phone or email.", tone="warning"), title="Verify", large=False, leading="arrow-left")


def passkey():
    return n("Screen", stack(n("Icon", name="fingerprint", size=56, tone="success"), heading("Passkey created", 1), muted("Next time, sign in with your face or fingerprint. No password to remember or steal.", "md"), gap="sm", align="center"),
             card(n("List", dense=True, items=[{"title": "This iPhone", "detail": "Added just now", "icon": "smartphone", "tone": "success"}, {"title": "MacBook Pro", "detail": "Added 12 Oct", "icon": "laptop"}]), title="Your passkeys", padding="sm"),
             btn("Continue to your account", "primary", size="lg", block=True), title="", large=False)


@screen("mobile/auth", "Mobile and cross-platform", "Sign-in, verification and passkeys", theme="ocean", height=1000,
        caption="Authentication screens: sign-in, a one-time code and passkey confirmation")
def mobile_auth(ctx):
    return stage("Sign-in that respects the platform.", "Inputs are filled and rounded on iOS and tonal pills on Android. The PinInput moves focus digit by digit.", phone(signin(), platform="ios", caption="Sign in · iOS"), phone(otp(), platform="android", caption="Verify · Android"), phone(passkey(), platform="ios", caption="Passkey · iOS"))
