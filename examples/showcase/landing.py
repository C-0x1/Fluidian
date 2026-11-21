"""Landing pages."""
from kit import *  # noqa: F401,F403

LOGOS = ["Arcwell", "Kestrel", "Oakline", "Lumina", "Northpass", "Halden", "Tessellate"]


def actions(primary, secondary=None, size="lg", icon=None):
    return row(btn(primary, "primary", size=size, icon=icon), btn(secondary, "secondary", size=size) if secondary else None, gap="sm")


@screen("landing/lumen", "Landing pages", "Lumen · AI workspace", theme="aurora", height=1760,
        caption="An AI product launch: glow backdrop, prompt composer and a bento of capabilities")
def lumen(ctx):
    chat = n("Chat", variant="flat", composer=False, messages=[
        {"from": "me", "text": "Summarise the Q3 board pack and flag anything that changed since June."},
        {"from": "ai", "tool": {"label": "Read 3 files", "detail": "board-pack-q3.pdf", "icon": "file"}, "rich": True,
         "text": "**Three things moved.** Net revenue retention rose to 118%, the EMEA launch slipped six weeks, and hiring is 9 heads behind plan.",
         "citations": ["Board pack p.4", "Hiring tracker"]}])
    return n("Landing",
             nav("Lumen", ["Product", "Agents", "Enterprise", "Pricing", "Changelog"], btn("Sign in", "ghost"), btn("Get Lumen", "primary"), logo="star", variant="pill"),
             n("Band",
               n("Hero", n("PromptBox", placeholder="Ask Lumen to draft, analyse or build something…", modes=["Ask", "Research", "Build"], hint="Lumen 4 · 1M context",
                           chips=["Draft a launch plan", "Analyse this spreadsheet", "Build a pricing page", "Explain this contract"]),
                 title="Think it. Lumen makes it real.", highlight="makes it real.", align="center", size="xl", tone="none", badge="Lumen 4: agents that finish the job", badgeTag="New",
                 subtitle="One workspace for research, writing and building. Lumen reads your files, plans the work and shows every step it takes."),
               n("LogoCloud", label="Trusted by product teams at", names=LOGOS), pad="md"),
             n("Band",
               n("Bento",
                 n("BentoCell", chat, span=4, rows=2, title="Answers with their sources", subtitle="Every claim links to the page it came from.", icon="message", tone="glow"),
                 n("BentoCell", n("BarList", ranked=True, items=[{"label": "Research", "value": 46, "display": "46%"}, {"label": "Writing", "value": 31, "display": "31%"}, {"label": "Analysis", "value": 23, "display": "23%"}]),
                   span=2, title="Knows how you work", subtitle="Routes each task to the right skill.", icon="route"),
                 n("BentoCell", n("Rings", size=132, center="92%", items=[{"label": "Grounded", "value": 92}, {"label": "Cited", "value": 88}, {"label": "Verified", "value": 74}]),
                   span=2, title="Checked before it ships", icon="shield"),
                 n("BentoCell", n("Terminal", title="agent · deploy", lines=["$ lumen run release-notes", {"text": "✓ read 42 merged pull requests", "kind": "ok"}, {"text": "✓ drafted notes in 3 languages", "kind": "ok"}, {"text": "→ waiting for your approval", "kind": "warn"}]),
                   span=3, title="Agents that ask before they act", subtitle="Approvals, budgets and a full audit trail.", icon="bot"),
                 n("BentoCell", n("Chart", kind="area", height=170, x="month", y=["hours"], legend=False, data=monthly(7, "hours", base=20, drift=9, noise=6)),
                   span=3, title="412 hours returned to the team", subtitle="Median across teams in their first quarter.", icon="trend-up"),
                 columns=6),
               title="One workspace for every kind of thinking", eyebrow="Capabilities", highlight="every kind of thinking", subtitle="Research, drafts, analysis and working software, with the reasoning in view."),
             n("Band", n("Metrics", variant="divided", items=[{"value": "1M", "label": "tokens of context"}, {"value": "38", "label": "connected tools"}, {"value": "4.9", "label": "average rating"}, {"value": "SOC 2", "label": "Type II audited"}]), pad="sm", tone="line"),
             n("Band", n("CTA", actions("Start for free", "Book a demo"), title="Put your busywork on autopilot", subtitle="Free for individuals. Team plans from $18 per seat."), pad="md"),
             footer("Lumen", [("Product", ["Workspace", "Agents", "Integrations", "Pricing"]), ("Company", ["About", "Careers", "Press"]), ("Resources", ["Docs", "Guides", "Status"]), ("Legal", ["Privacy", "Terms", "Security"])],
                    "© 2026 Lumen Labs. A fictional company for demonstration.", logo="star", tagline="The AI workspace that shows its work."),
             backdrop="glow")


def site_footer(brand, logo, tagline):
    return footer(brand, [("Product", ["Overview", "Pricing", "Changelog", "Roadmap"]), ("Developers", ["Documentation", "API reference", "Status"]), ("Company", ["About", "Careers", "Contact"])],
                  "© 2026 %s. A fictional company for demonstration." % brand, logo=logo, tagline=tagline)


@screen("landing/stackline", "Landing pages", "Stackline · developer cloud", theme="graphite", height=1820,
        caption="A developer platform in monochrome: grid backdrop, a product window and a code-first feature band")
def stackline(ctx):
    deploys = [("checkout-api", "Production · main @ 8f3c2a1", "42s", "check-circle", "success", "Ready"), ("web", "Preview · feat/pricing @ 1b9e77d", "1m 08s", "check-circle", "success", "Ready"),
               ("workers", "Production · main @ c41d0f2", "Building", "refresh", "warning", "Building"), ("docs", "Preview · fix/typos @ 77aa0c3", "31s", "check-circle", "success", "Ready")]
    window = browser(n("Page", split(card(listing(deploys), title="Deployments", subtitle="Every push gets its own URL", padding="md"),
                                      stack(card(chart("area", monthly(31, "p95", base=180, drift=-6, noise=14, low=60), "month", "p95", height=150, legend=False), title="p95 latency · 84 ms", subtitle="Global, last 12 months"),
                                            n("Terminal", title="build · workers", cursor=False, lines=["$ stackline deploy --prod", {"text": "▲ uploading 214 files", "kind": "dim"}, {"text": "✓ compiled in 3.2s", "kind": "ok"}, {"text": "✓ 18 regions healthy", "kind": "ok"}])), ratio="3:2"),
                              title="", width="full"), url="stackline.dev/acme/overview", height=470)
    config = "# stackline.toml\n[build]\ncommand = \"npm run build\"\noutput  = \"dist\"\n\n[routes]\n\"/api/*\" = { fn = \"api\", regions = \"all\" }\n\"/*\"     = { static = true, cache = \"1y\" }\n\n[scale]\nmin = 0          # scale to zero\nmax = 500\n"
    return n("Landing",
             nav("Stackline", ["Platform", "Solutions", "Docs", "Pricing", "Customers"], btn("Log in", "ghost"), btn("Start deploying", "primary"), logo="tri"),
             n("Band", n("Hero", actions("Start deploying", "Read the docs"), title="Ship the idea, not the infrastructure.", highlight="not the infrastructure.", align="center", size="xl", tone="none",
                         badge="Edge functions are now generally available", badgeTag="GA", subtitle="Push to deploy. Stackline builds, previews and scales your app in 18 regions, then gets out of the way."),
               window, pad="md", width="default"),
             n("Band", n("LogoCloud", names=LOGOS + ["Quillon"], label="Deployed on Stackline", variant="grid"), pad="sm"),
             n("Band", split(code(config, "toml", title="stackline.toml", tone="dark"),
                             stack(feature("Preview every pull request", "Each branch gets a live URL with production data masked, so review happens on the real thing.", "eye", variant="row"),
                                   feature("Scale to zero, and to millions", "Functions start in under 40 ms and you only pay while a request is running.", "bolt", variant="row"),
                                   feature("Roll back in one click", "Every deployment is immutable. Promote any previous build instantly.", "undo", variant="row"), gap="lg"), ratio="1:1", gap="xl"),
               title="Infrastructure in twelve lines", eyebrow="Configuration", subtitle="One file describes builds, routing and scaling. Everything else is a default you can change later.", tone="line"),
             n("Band", n("Metrics", variant="cards", items=[{"value": "18", "label": "regions", "detail": "Requests served from the nearest one"}, {"value": "38 ms", "label": "cold start", "detail": "p50 across all runtimes"},
                                                        {"value": "99.99%", "label": "uptime", "detail": "Measured over the last 12 months"}, {"value": "4.1B", "label": "requests a day", "detail": "Across 62,000 projects"}]), pad="sm"),
             n("Band", n("CTA", actions("Deploy your first app", "Talk to an engineer"), title="From git push to global in 60 seconds", tone="soft", subtitle="Free for hobby projects. No credit card."), pad="md"),
             site_footer("Stackline", "tri", "The fastest path from code to production."), backdrop="grid")


MODELS = [("atlas-large", "Meridian", 482, "+12%", 265), ("quill-mini", "Quillon", 319, "+31%", 150), ("onyx-vision", "Onyx Labs", 240, "+4%", 20), ("ember-code", "Emberworks", 201, "+58%", 40),
          ("tidal-3", "Tidal AI", 164, "-3%", 200), ("sable-fast", "Sable", 122, "+9%", 320)]


@screen("landing/relay", "Landing pages", "Relay · model router", theme="abyss", height=1900,
        caption="An API gateway for models: headline stats, a ranked model list and a usage console in a browser frame")
def relay(ctx):
    ranked = n("BarList", ranked=True, items=[{"label": m, "detail": "by " + who, "value": tokens, "display": "%dB tokens" % tokens, "hue": hue} for m, who, tokens, _, hue in MODELS])
    providers = table([("provider", "Provider"), ("latency", "p50 latency"), ("price", "Price / 1M"), ("status", "Status", "badge")],
                      [{"provider": "Meridian", "latency": "312 ms", "price": "$2.40", "status": "Healthy"}, {"provider": "Quillon", "latency": "188 ms", "price": "$0.35", "status": "Healthy"},
                       {"provider": "Emberworks", "latency": "241 ms", "price": "$1.10", "status": "Healthy"}, {"provider": "Tidal AI", "latency": "904 ms", "price": "$1.90", "status": "Degraded"}], dense=True, sortable=False)
    console = browser(n("Page", kpis(("Requests", "18.4M", "+22%", "this week", "activity", 41), ("Spend", "$12,840", "-31%", "vs direct", "dollar", 42), ("Cache hits", "38%", "+6 pts", "this week", "bolt", 43), ("Failovers", "214", "0 errors", "served", "shield"), gap="sm"),
                        split(card(chart("area", [{"day": d, "atlas-large": a, "quill-mini": b, "ember-code": c} for d, a, b, c in zip(DAYS, series(51, 7, 40, 3, 6), series(52, 7, 26, 4, 5), series(53, 7, 12, 5, 4))], "day", ["atlas-large", "quill-mini", "ember-code"], height=190), title="Tokens by model"),
                              card(n("Progress", label="Monthly budget · $12,840 of $20,000", value=64), n("Progress", label="Team: Search · $4,120 of $5,000", value=82, tone="warning"), n("Progress", label="Team: Support · $1,960 of $6,000", value=33, tone="success"), title="Budgets"), ratio="2:1"),
                        title="", width="full"), url="relay.dev/console/usage", height=520)
    return n("Landing",
             nav("Relay", ["Models", "Routing", "Docs", "Pricing", "Rankings"], btn("Sign in", "ghost"), btn("Get an API key", "primary"), logo="arc"),
             n("Band", n("Hero", actions("Get an API key", "Browse 340 models"), title="One API for every model.", highlight="every model.", align="center", size="xl", tone="none",
                         subtitle="Route each request to the best model for price, speed or quality. Automatic failover, one invoice, no lock-in."),
               n("Metrics", items=[{"value": "340+", "label": "models"}, {"value": "60", "label": "providers"}, {"value": "9T", "label": "tokens a month"}, {"value": "2.1M", "label": "developers"}]),
               n("LogoCloud", names=LOGOS, label="Powering AI features at"), pad="md"),
             n("Band", split(card(ranked, title="Trending this week", subtitle="Share of tokens routed, all apps"),
                             stack(card(providers, title="Live provider health", subtitle="Requests move away from a slow provider within two seconds", padding="none"),
                                   n("Code", language="bash", tone="dark", title="Switch models by changing one string", source="curl https://api.relay.dev/v1/chat \\\n  -H \"Authorization: Bearer $RELAY_KEY\" \\\n  -d '{\"model\": \"auto:cheapest\", \"messages\": [...]}'")), ratio="1:1", gap="lg"),
               title="The models people use, ranked in the open", eyebrow="Rankings", subtitle="Usage data from real traffic, updated every hour.", tone="line"),
             n("Band", console, title="See every token, team and dollar", eyebrow="Console", subtitle="Budgets, caching and per-team keys without building any of it."),
             n("Band", n("CTA", actions("Create a free key", "Read the docs"), title="The future is multi-model. Build for it today.", subtitle="No markup on model prices. Pay only for what you route."), pad="md"),
             site_footer("Relay", "arc", "One API, every model, zero lock-in."), backdrop="dots")


@screen("landing/halo", "Landing pages", "Halo · wearables", theme="ruby", height=1980,
        caption="A hardware launch in full-bleed promo tiles, with every product drawn procedurally")
def halo(ctx):
    links = lambda a="Learn more", b="Buy": row(btn(a, "primary"), btn(b, "secondary"), gap="sm")  # noqa: E731
    return n("Landing",
             nav("Halo", ["Glasses", "Audio", "Watch", "Home", "Accessories", "Support"], btn("Search", "ghost", icon="search"), btn("Bag", "ghost", icon="shopping-bag"), logo="ring"),
             n("Band", n("PromoTile", links(), title="Halo One", subtitle="See further. Glasses with an assistant built in.", eyebrow="New", art={"kind": "glasses", "hue": 250, "ratio": "21:9", "bare": True, "tone": "dark"}, tone="dark", size="lg"),
               grid(n("PromoTile", links(), title="Halo Air", subtitle="Sound that follows the room.", art={"kind": "headphones", "hue": 20, "ratio": "16:9", "bare": True}, tone="tint"),
                    n("PromoTile", links(), title="Halo Band 4", subtitle="Seven days. One charge.", art={"kind": "watch", "hue": 160, "ratio": "16:9", "bare": True}), columns=2, gap="md"),
               n("PromoTile", links("Get the app", "Learn more"), title="Everything, in one place.", highlight="in one place.", subtitle="The Halo app pairs every device in seconds and keeps them in step.", eyebrow="Halo app",
                 art={"kind": "phone", "hue": 265, "hue2": 330, "ratio": "4:3", "bare": True}, layout="split", align="start", size="sm"),
               grid(n("PromoTile", links("Shop speakers", "Compare"), title="Halo Home", subtitle="Fill every room.", art={"kind": "speaker", "hue": 250, "ratio": "16:9", "bare": True}, size="sm"),
                    n("PromoTile", links("Learn more", "Shop"), title="Halo Glow", subtitle="Light that winds down with you.", art={"kind": "lamp", "hue": 70, "ratio": "16:9", "bare": True, "tone": "dark"}, tone="dark", size="sm"), columns=2, gap="md"),
               pad="sm", width="wide"),
             footer("Halo", [("Shop", ["Glasses", "Audio", "Watch", "Home"]), ("Services", ["Halo Care", "Trade in", "Financing"]), ("About", ["Newsroom", "Careers", "Environment"]), ("Support", ["Manuals", "Repairs", "Contact"])],
                    "© 2026 Halo Devices. A fictional company for demonstration.", logo="ring", tagline="Technology that stays out of the way."))


def workout_screen():
    return n("Screen", card(n("Rings", size=150, center="78%", items=[{"label": "Move", "value": 468, "max": 600, "display": "468 kcal"}, {"label": "Train", "value": 34, "max": 40, "display": "34 min"}, {"label": "Stand", "value": 9, "max": 12, "display": "9 hrs"}])),
             grid(stat("Heart rate", "62 bpm", delta="Resting", trend="flat"), stat("Sleep", "7h 42m", delta="+38m"), columns=2, minWidth=120, gap="sm"),
             card(chart("bar", [{"d": d[0], "min": v} for d, v in zip(DAYS, [32, 45, 0, 51, 38, 64, 22])], "d", "min", height=130, legend=False), title="Active minutes"),
             title="Today", subtitle="Thursday 19 November", avatar="Ana Lima", tabs=[{"label": "Today", "icon": "activity", "active": True}, {"label": "Train", "icon": "dumbbell"}, {"label": "Sleep", "icon": "moon"}, {"label": "You", "icon": "user"}])


@screen("landing/pulse", "Landing pages", "Pulse · fitness app", theme="ember", height=1620,
        caption="A mobile app launch page: split hero with a live phone preview, feature tiles and testimonials")
def pulse(ctx):
    quotes = [("I stopped guessing. Pulse tells me when to push and when to rest.", "Jonas Weber", "Marathon runner"), ("The first tracker my whole family actually kept using.", "Priya Nair", "Parent of three"),
              ("Recovery scores changed how I train. Fewer injuries, better times.", "Tomás Rey", "Triathlete")]
    return n("Landing",
             nav("Pulse", ["Training", "Recovery", "Nutrition", "Coaches", "Pricing"], btn("Log in", "ghost"), btn("Start free trial", "primary"), logo="bolt", variant="pill"),
             n("Band", split(n("Hero", row(btn("Download for iOS", "primary", size="lg", icon="smartphone"), btn("Get it on Android", "secondary", size="lg", icon="smartphone"), gap="sm"),
                               n("AvatarStack", names=PEOPLE[:5], label="Joined by 2.4 million athletes", size="md"),
                               title="Train smarter. Recover on purpose.", highlight="Recover on purpose.", size="lg", tone="none", badge="Adaptive plans, rebuilt every morning", badgeTag="Pulse 3",
                               subtitle="Pulse reads your sleep, strain and heart rate, then rewrites today's plan so every session counts."),
                             row(phone(workout_screen(), platform="ios", theme="ember", scale=0.9, height=640), justify="center"), ratio="6:5", gap="xl"), pad="md", width="wide"),
             n("Band", grid(feature("Adaptive training plans", "Miss a session or sleep badly and your week reshapes itself around it.", "target"), feature("Recovery you can read", "One score from heart-rate variability, sleep and load, with the reasons behind it.", "heart-pulse", tone="danger"),
                            feature("A coach in your pocket", "Ask why a workout changed and get an answer grounded in your own data.", "sparkles", tone="ai"), columns=3, gap="lg"),
               title="Built around the body you have today", eyebrow="Why Pulse", highlight="you have today", tone="line"),
             n("Band", n("Metrics", variant="divided", items=[{"value": "2.4M", "label": "athletes"}, {"value": "31%", "label": "fewer missed sessions"}, {"value": "4.8", "label": "App Store rating"}, {"value": "190", "label": "countries"}]), pad="sm"),
             n("Band", grid(*[n("Testimonial", quote=q, author=a, role=r, rating=5) for q, a, r in quotes], columns=3, gap="lg"), pad="sm"),
             n("Band", n("CTA", actions("Start your free month", "See plans"), title="Your next personal best starts tonight", subtitle="Because recovery is where it happens. 30 days free, cancel anytime."), pad="md"),
             site_footer("Pulse", "bolt", "Training that listens to your body."), backdrop="glow")


@screen("landing/northbank", "Landing pages", "Northbank · investing", theme="ocean", height=1900,
        caption="A financial services page: calm blues, account cards, a rate comparison and an FAQ")
def northbank(ctx):
    accounts = [("Brokerage", "Trade stocks, funds and bonds with $0 commissions.", "trend-up", ["No account minimum", "Fractional shares from $1", "Automatic rebalancing"]),
                ("Retirement", "Tax-advantaged accounts with a plan that adjusts as you do.", "target", ["Traditional and Roth", "Free rollover service", "Target-date portfolios"]),
                ("Cash management", "Earn 4.35% on idle cash, with instant transfers.", "bank", ["No monthly fees", "Insured up to $2M", "Free debit card"])]
    return n("Landing",
             nav("Northbank", ["Invest", "Retire", "Save", "Advice", "Learn"], btn("Log in", "ghost"), btn("Open an account", "primary"), logo="bars"),
             n("Band", n("Hero", actions("Open an account", "See how we invest"), title="Invest with a plan, not a hunch.", highlight="not a hunch.", align="center", size="xl", tone="none",
                         subtitle="Low-cost portfolios, human advisers when you want them and tools that show exactly where you stand."),
               n("Metrics", variant="cards", items=[{"value": "$0", "label": "commissions", "detail": "On stocks, funds and options"}, {"value": "4.35%", "label": "cash APY", "detail": "Variable, no minimum balance"},
                                                  {"value": "0.04%", "label": "average fund cost", "detail": "Across our core portfolios"}, {"value": "24/7", "label": "support", "detail": "Licensed professionals, not bots"}]), pad="md"),
             n("Band", grid(*[n("Feature", n("List", dense=True, divided=False, items=[{"title": p, "icon": "check", "tone": "success"} for p in points]), btn("Open %s" % name.lower(), "secondary"), title=name, body=body, icon=icon) for name, body, icon, points in accounts], columns=3, gap="lg"),
               title="An account for every goal", eyebrow="Accounts", subtitle="Open one in about five minutes. Move money in whenever you are ready.", tone="soft"),
             n("Band", n("Comparison", label="What you pay", plans=[{"name": "Northbank", "price": "Core", "featured": True}, {"name": "Typical broker"}, {"name": "Typical adviser"}],
                         rows=[{"label": "Stock and fund trades", "values": ["$0", "$0–$6.95", "Included"]}, {"label": "Advisory fee", "values": ["0.25%", "—", "1.00%"]}, {"label": "Account minimum", "values": ["$0", "$0", "$250,000"]},
                               {"label": "Automatic rebalancing", "values": [True, False, True]}, {"label": "Tax-loss harvesting", "values": [True, False, True]}, {"label": "Human adviser on request", "values": [True, False, True]}]),
               title="Costs, in the open", eyebrow="Pricing", subtitle="Fees compound just like returns. Ours are designed to stay out of the way.", width="narrow"),
             n("Band", n("FAQ", items=[{"q": "Is my money protected?", "a": "Securities are protected up to $500,000 by investor protection schemes and cash is swept to partner banks insured up to $2 million."},
                                       {"q": "How long does it take to open an account?", "a": "About five minutes. You will need an ID and your bank details."}, {"q": "Can I transfer an existing account?", "a": "Yes. Transfers are free and usually complete within a week."},
                                       {"q": "What does advice cost?", "a": "Managed portfolios cost 0.25% a year. Sessions with an adviser are included above $100,000."}]), title="Questions, answered", width="narrow", tone="line"),
             n("Band", n("CTA", actions("Open an account", "Talk to an adviser"), title="Start with $1. Grow from there.", tone="brand", subtitle="Investing involves risk, including loss of principal. This page is a design demonstration, not an offer."), pad="md"),
             site_footer("Northbank", "bars", "Investing with a plan since 1994."), backdrop="glow")


@screen("landing/canvasly", "Landing pages", "Canvasly · design tool", theme="candy", height=1800,
        caption="A playful design-tool launch: pastel palette, input modes and a wall of short testimonials")
def canvasly(ctx):
    quotes = [("Went from a napkin sketch to a clickable prototype before lunch.", "Sofia Marin", "Product designer"), ("Our PM now ships first drafts. I polish instead of starting from zero.", "Kenji Sato", "Design lead"),
              ("The component suggestions match our design system better than our interns do.", "Lena Fischer", "Head of design"), ("I paste a screenshot of a competitor and get an editable layout back.", "Omar Haddad", "Founder"),
              ("Handoff is a link now. Engineers read the tokens directly.", "Idris Bello", "Frontend engineer"), ("It finally made wireframing fun again.", "Ana Lima", "UX researcher")]
    return n("Landing",
             nav("Canvasly", ["Features", "Templates", "Teams", "Pricing"], btn("Sign in", "ghost"), btn("Try it free", "primary"), logo="grid", variant="pill"),
             n("Band", n("Hero", n("PromptBox", placeholder="A habit tracker with a weekly streak view and a friendly empty state…", modes=["Text", "Wireframe", "Screenshot", "Spec"], button="Generate",
                                   chips=["Mobile banking home", "Admin table with filters", "Onboarding in three steps"]),
                         title="Design at the speed of thought.", highlight="speed of thought.", align="center", size="xl", tone="none", badge="Now with live design-system sync", badgeTag="New",
                         subtitle="Describe a screen, drop in a sketch or paste a screenshot. Canvasly returns editable layouts that use your own components."), pad="md"),
             n("Band", n("Bento", n("BentoCell", art("ui", variant="dashboard", ratio="16:9"), span=3, title="From prompt to layout", subtitle="Full screens with real hierarchy, not lorem ipsum boxes.", icon="wand", padding="md"),
                         n("BentoCell", art("ui", variant="mobile", ratio="16:9", seed=4), span=3, title="Responsive by default", subtitle="Every frame adapts from phone to desktop.", icon="smartphone"),
                         n("BentoCell", row(*[n("Avatar", name=p, size="lg") for p in PEOPLE[:6]], gap="xs"), span=2, title="Multiplayer", subtitle="Design together, comment in place.", icon="users", tone="soft"),
                         n("BentoCell", art("blocks", ratio="21:9"), span=2, title="Your system, respected", subtitle="Tokens and components stay in sync.", icon="palette", tone="glow"),
                         n("BentoCell", code("<Button tone=\"brand\" size=\"lg\">\n  Continue\n</Button>", "jsx"), span=2, title="Handoff that compiles", subtitle="Copy code that matches the canvas.", icon="code"), columns=6),
               title="Everything between idea and handoff", eyebrow="Features"),
             n("Band", grid(*[n("Testimonial", quote=q, author=a, role=r, variant="compact") for q, a, r in quotes], columns=3, gap="md"), title="Designers are talking", eyebrow="Wall of love", tone="soft"),
             n("Band", n("CTA", actions("Start designing free", "Watch the 2-minute demo"), title="Your next screen is one sentence away", subtitle="Free for three projects. No credit card."), pad="md"),
             site_footer("Canvasly", "grid", "Design at the speed of thought."), backdrop="mesh")


@screen("landing/brightbuild", "Landing pages", "Brightbuild · app builder", theme="sunset", height=1760,
        caption="An AI app builder: warm gradient mesh, a prompt-first hero and a gallery of starting points")
def brightbuild(ctx):
    templates = [("SaaS dashboard", "Auth, billing and charts", "dashboard", 1), ("Launch page", "Hero, pricing and waitlist", "landing", 2), ("Mobile storefront", "Catalogue, cart and checkout", "mobile", 3),
                 ("Internal tool", "Tables, filters and roles", "dashboard", 6), ("Portfolio", "Projects, about and contact", "landing", 8), ("Booking app", "Calendar, reminders, payments", "mobile", 9)]
    return n("Landing",
             nav("Brightbuild", ["Templates", "Showcase", "Enterprise", "Pricing", "Docs"], btn("Sign in", "ghost"), btn("Start building", "primary"), logo="star", variant="pill"),
             n("Band", n("Hero", n("PromptBox", placeholder="An app where my climbing gym can post routes and members can log sends…", modes=["Plan", "Build"], hint="Deploys to your own domain",
                                   chips=["Website", "Web app", "Mobile app", "Internal tool", "Prototype"]),
                         title="Describe it. Ship it by lunch.", highlight="Ship it by lunch.", align="center", size="xl", tone="none",
                         subtitle="Brightbuild turns a paragraph into a working product: database, sign-in, payments and a place to host it."),
               n("LogoCloud", names=LOGOS, label="Teams building on Brightbuild"), pad="md"),
             n("Band", grid(*[card(art("ui", variant=v, seed=s, ratio="16:9"), between(stack(strong(t), muted(d), gap="none"), btn("Use", "secondary", size="sm")), padding="sm") for t, d, v, s in templates], columns=3, gap="lg"),
               title="Start from something real", eyebrow="Templates", subtitle="Each one is a complete, editable app. Remix it with a sentence."),
             n("Band", grid(feature("Describe", "Say what you need in plain language. Attach a sketch if you have one.", number="01", variant="tile"), feature("Refine", "Point at anything and ask for a change. Every edit is a reviewable diff.", number="02", variant="tile"),
                            feature("Ship", "One click publishes to a global edge network with a database included.", number="03", variant="tile"), columns=3, gap="lg"), title="Three steps, no boilerplate", eyebrow="How it works", tone="line"),
             n("Band", n("CTA", actions("Build something now", "See what others made"), title="Stop waiting for a free sprint", subtitle="Your first three apps are free. Export the code whenever you like."), pad="md"),
             site_footer("Brightbuild", "star", "From a paragraph to a product."), backdrop="mesh")


@screen("landing/hearth", "Landing pages", "Hearth · open-source agent", theme="terminal", height=1900,
        caption="An open-source project page in the Terminal theme: monospace type, an install block and numbered features")
def hearth(ctx):
    features = [("Runs on your machine", "Your files and keys never leave it."), ("Does the work", "Opens apps, edits files, sends the email."), ("Remembers", "Learns your projects and preferences."),
                ("Talks where you are", "Chat, terminal, voice or a webhook."), ("Any model", "Bring a local model or any API."), ("Auditable", "Every action logged and replayable.")]
    downloads = [("macOS", "13 or later · Apple silicon and Intel", "laptop"), ("Windows", "10 or later · x64 and ARM", "monitor"), ("Linux", "deb, rpm and AppImage", "terminal")]
    return n("Landing",
             nav("hearth", ["docs", "skills", "community", "blog"], btn("★ 48.2k", "secondary"), btn("install", "primary"), logo="hex", tag="v2.4"),
             n("Band", split(n("Hero", actions("Install Hearth", "Read the docs"), title="Your computer, with initiative.", highlight="initiative.", size="lg", tone="none", badge="2.4 adds scheduled tasks", badgeTag="release",
                               subtitle="Hearth is an open-source agent that lives on your machine and gets real work done: no cloud required, no data leaves."),
                             n("Terminal", tabs=["one-liner", "npm", "from source"], lines=["$ curl -fsSL https://hearth.example/install.sh | sh", {"text": "→ detected linux x86_64", "kind": "dim"}, {"text": "✓ installed hearth 2.4.0 to ~/.hearth/bin", "kind": "ok"}, "",
                                                                                           "$ hearth \"tidy my downloads and file the invoices\"", {"text": "● reading 214 files", "kind": "dim"}, {"text": "● moved 31 invoices to ~/Documents/Invoices/2026", "kind": "dim"},
                                                                                           {"text": "✓ done in 12s · 3 actions need your approval", "kind": "ok"}]), ratio="1:1", gap="xl"), pad="md", width="wide"),
             n("Band", grid(*[n("Feature", row(btn("Download", "primary", icon="download"), btn("Checksums", "ghost"), gap="xs"), title=name, body=detail, icon=icon) for name, detail, icon in downloads], columns=3, gap="lg"),
               title="Download", eyebrow="// get started", align="start", pad="sm", tone="line"),
             n("Band", grid(*[feature(t, b, number="#%d" % (i + 1), variant="tile") for i, (t, b) in enumerate(features)], columns=3, gap="md"), title="What it does", eyebrow="// features", align="start", pad="sm"),
             n("Band", split(n("FAQ", items=[{"q": "Is it really free?", "a": "Yes. Hearth is MIT licensed. You pay only for the model you connect, or nothing if you run one locally."},
                                             {"q": "What can it access?", "a": "Only the folders and apps you grant. Destructive actions always ask first."}, {"q": "Which models work?", "a": "Any model with a chat API, plus local models through the bundled runner."}]),
                             card(n("Metrics", variant="plain", align="start", items=[{"value": "48.2k", "label": "stars"}, {"value": "1,140", "label": "contributors"}]), n("AvatarStack", names=PEOPLE, max_=7, label="and 1,133 more"), title="Built in the open"), ratio="3:2", gap="xl"),
               title="FAQ", eyebrow="// questions", align="start", pad="sm", tone="line"),
             site_footer("hearth", "hex", "An agent that lives where your work does."), backdrop="grid")


@screen("landing/mnemo", "Landing pages", "Mnemo · memory for AI", theme="grape", height=1880,
        caption="An infrastructure product: tabbed code in the hero, a three-step explainer and a benchmark chart")
def mnemo(ctx):
    py = "from mnemo import Memory\n\nmemory = Memory(api_key=KEY)\nmemory.add(\"Prefers aisle seats and vegetarian meals\", user=\"u_481\")\n\ncontext = memory.search(\"book a flight to Lisbon\", user=\"u_481\")\n# → [\"Prefers aisle seats and vegetarian meals\"]\n"
    js = "import { Memory } from \"mnemo\";\n\nconst memory = new Memory({ apiKey: KEY });\nawait memory.add(\"Prefers aisle seats and vegetarian meals\", { user: \"u_481\" });\n\nconst context = await memory.search(\"book a flight to Lisbon\", { user: \"u_481\" });\n"
    bench = [{"system": "Full context", "accuracy": 71}, {"system": "Vector search", "accuracy": 64}, {"system": "Summaries", "accuracy": 58}, {"system": "Mnemo", "accuracy": 89}]
    return n("Landing",
             nav("Mnemo", ["Developers", "Use cases", "Research", "Pricing"], btn("★ 31.6k", "ghost"), btn("Get started", "primary"), logo="half", variant="pill"),
             n("Band", split(n("Hero", actions("Get an API key", "Read the paper"), title="AI that remembers.", highlight="remembers.", size="xl", tone="none", badge="New retrieval algorithm: 26% more accurate", badgeTag="Research",
                               subtitle="A memory layer for assistants and agents. Store what matters, retrieve it in milliseconds and cut token spend by 80%."),
                             stack(tabs(("Python", code(py, "python", tone="dark", title="memory.py")), ("Node.js", code(js, "javascript", tone="dark", title="memory.js")), variant="pill"),
                                   n("Metrics", variant="cards", items=[{"value": "150k+", "label": "developers"}, {"value": "41 ms", "label": "p50 retrieval"}])), ratio="1:1", gap="xl"), pad="md", width="wide"),
             n("Band", n("LogoCloud", names=LOGOS + ["Verano", "Brightside"], label="In production at"), pad="sm"),
             n("Band", grid(feature("Add", "Send conversations or facts. Mnemo extracts what is worth keeping.", number="01"), feature("Learn", "Memories are merged, updated and expired as people change their minds.", number="02"),
                            feature("Retrieve", "Ask a question and get the few memories that matter, ranked.", number="03"), columns=3, gap="lg"), title="How it works", eyebrow="Three calls", tone="line"),
             n("Band", split(card(chart("bar", bench, "system", "accuracy", height=260, legend=False, format="percent"), title="Long-conversation recall", subtitle="Accuracy on a 600-turn benchmark; higher is better"),
                             stack(feature("Governed", "Per-user isolation, retention rules and audit logs.", "shield", variant="row"), feature("Portable", "Runs in your cloud or ours. Export everything, anytime.", "box", variant="row"),
                                   feature("Inspectable", "See why a memory was stored and when it was last used.", "eye", variant="row"), gap="lg"), ratio="3:2", gap="xl"), title="Measured, not promised", eyebrow="Benchmarks"),
             n("Band", n("CTA", actions("Start free", "Book a demo"), title="Give your agents a past", subtitle="10,000 memories free every month."), pad="md"),
             site_footer("Mnemo", "half", "The memory layer for AI."), backdrop="aurora")


@screen("landing/orbit", "Landing pages", "Orbit · product analytics", theme="iris", height=1960,
        caption="A SaaS landing page with the product on show: a dashboard in a browser frame, feature tiles and plans")
def orbit(ctx):
    product = browser(n("Page", kpis(("Weekly active users", "48,210", "+9.2%", "vs last week", "users", 61), ("Activation", "62.4%", "+3.1 pts", "day 1", "bolt", 62), ("Retention", "41.8%", "+1.4 pts", "week 4", "refresh", 63), ("MRR", "$284k", "+6.0%", "this month", "dollar", 64), gap="sm"),
                        split(card(chart("area", [{"week": "W%d" % (i + 1), "signups": a, "activated": b} for i, (a, b) in enumerate(zip(series(71, 10, 900, 60, 80), series(72, 10, 520, 44, 60)))], "week", ["signups", "activated"], height=210), title="Signups and activation"),
                              card(n("Funnel", stages=[{"label": "Visited", "value": 48200}, {"label": "Signed up", "value": 9800}, {"label": "Activated", "value": 6100}, {"label": "Subscribed", "value": 1420}]), title="Funnel · last 30 days"), ratio="3:2"),
                        title="", width="full"), url="app.orbit.example/overview", height=540)
    return n("Landing",
             nav("Orbit", ["Product", "Solutions", "Customers", "Pricing", "Docs"], btn("Sign in", "ghost"), btn("Start free", "primary"), logo="orb"),
             n("Band", n("Hero", actions("Start free", "Book a demo"), title="Know what your users do next.", highlight="do next.", align="center", size="xl", tone="none", badge="Ask questions in plain English", badgeTag="New",
                         subtitle="Product analytics that answers the question you were about to ask. Funnels, retention and revenue in one place."), product, pad="md"),
             n("Band", n("LogoCloud", names=LOGOS, label="4,000 product teams measure with Orbit"), pad="sm"),
             n("Band", grid(feature("Answers, not dashboards", "Type a question and get a chart with the method shown.", "sparkles", tone="ai"), feature("Retention you can act on", "See which first-week actions predict a customer who stays.", "refresh"),
                            feature("Warehouse native", "Query your own data in place. Nothing is copied out.", "database", tone="info"), feature("Privacy built in", "Automatic redaction and regional storage by default.", "lock", tone="success"),
                            feature("Alerts that explain", "Anomalies arrive with the segments that caused them.", "bell", tone="warning"), feature("SDKs for everything", "Fourteen languages and every major framework.", "code"), columns=3, gap="lg"),
               title="Built for the questions you actually have", eyebrow="Features", tone="soft"),
             n("Band", grid(n("PricingCard", plan="Starter", price="$0", period="up to 1M events", description="For side projects and early products.", features=["Core reports", "3 seats", "Community support"], cta="Start free"),
                            n("PricingCard", plan="Growth", price="$249", period="per month", description="For teams that ship every week.", features=["Unlimited reports", "Ask Orbit", "Warehouse sync", "Unlimited seats"], cta="Start 14-day trial", featured=True, badge="Most popular"),
                            n("PricingCard", plan="Enterprise", price="Custom", period="annual", description="For regulated and high-volume products.", features=["SSO and SCIM", "Regional storage", "Dedicated support"], cta="Talk to sales"), columns=3, gap="lg"),
               title="Simple pricing", eyebrow="Plans", width="default"),
             site_footer("Orbit", "orb", "Know what your users do next."), backdrop="glow")


@screen("landing/atelier", "Landing pages", "Atelier Nord · studio", theme="gold", height=1900,
        caption="A studio portfolio in the Gold theme: serif display type on near-black, with generative cover art")
def atelier(ctx):
    work = [("Verano", "Identity and packaging", {"kind": "cover", "hue": 30, "seed": 3}), ("Kestrel", "Digital product", {"kind": "facets", "hue": 200, "seed": 5}), ("Oakline", "Campaign", {"kind": "cover", "hue": 150, "seed": 1}),
            ("Lumina", "Brand film", {"kind": "orbit", "hue": 270}), ("Halden", "Editorial", {"kind": "topo", "hue": 80, "seed": 2, "tone": "dark"}), ("Quillon", "Type design", {"kind": "poster", "hue": 60, "label": "Qu", "variant": "serif"})]
    return n("Landing",
             nav("Atelier Nord", ["Work", "Studio", "Journal", "Contact"], btn("Start a project", "primary"), logo="diamond"),
             n("Band", n("Hero", actions("See selected work", "Start a project"), title="We make brands impossible to ignore.", highlight="impossible to ignore.", size="xl", tone="none", eyebrow="Independent design studio · Oslo",
                         subtitle="Identity, product and film for companies that would rather be remembered than be safe."), pad="md", width="default", align="start"),
             n("Band", grid(*[stack(art(ratio="4:3", **spec), between(strong(name, size="lg"), muted(kind)), gap="sm") for name, kind, spec in work], columns=3, gap="lg"), title="Selected work", eyebrow="2024 — 2026", align="start", pad="sm", width="wide"),
             n("Band", split(stack(heading("Services", 2), muted("A small team, senior on every project.", "md")),
                             n("List", items=[{"title": "Brand identity", "detail": "Strategy, naming, visual systems", "meta": "01"}, {"title": "Digital product", "detail": "Research, interface, design systems", "meta": "02"},
                                              {"title": "Motion and film", "detail": "Launch films, title sequences, 3D", "meta": "03"}, {"title": "Editorial", "detail": "Books, annual reports, type", "meta": "04"}]), ratio="1:2", gap="xl"), pad="sm", tone="line"),
             n("Band", n("Testimonial", quote="They asked the question nobody inside the company dared to. The rebrand paid for itself in a quarter.", author="Lena Fischer", role="Chief executive", company="Verano", variant="large"), pad="sm"),
             n("Band", n("CTA", actions("hello@ateliernord.example"), title="Have something worth making?", tone="plain", align="start", subtitle="We take on six projects a year. The next opening is February."), pad="sm", align="start"),
             site_footer("Atelier Nord", "diamond", "Independent since 2011."))


@screen("landing/voyage", "Landing pages", "Voyage · travel", theme="sky", height=1820,
        caption="A travel booking page: a generated landscape hero with a search card and destination tiles")
def voyage(ctx):
    places = [("Lofoten, Norway", "Fjords and midnight sun", "from $840", {"kind": "peaks", "hue": 220}), ("Merzouga, Morocco", "Dunes at first light", "from $690", {"kind": "dunes", "hue": 35}),
              ("Kyoto, Japan", "Temples in maple season", "from $1,120", {"kind": "forest", "hue": 20}), ("Lisbon, Portugal", "Tiles, trams and Atlantic air", "from $520", {"kind": "city", "hue": 300})]
    search = card(grid(field("Where", "where", "Lisbon, Portugal", icon="pin"), field("When", "when", "12 – 19 March", icon="calendar"), field("Guests", "guests", "2 adults", icon="users"), stack(spacer("sm"), btn("Search stays", "primary", size="lg", block=True)), columns=4, gap="sm"), elevated=True)
    return n("Landing",
             nav("Voyage", ["Stays", "Flights", "Trips", "Guides"], btn("Sign in", "ghost"), btn("Plan a trip", "primary"), logo="wave"),
             n("Band", n("PromoTile", title="Go somewhere that changes you.", highlight="changes you.", subtitle="Hand-picked stays and slow itineraries in 120 countries.", art={"kind": "coast", "hue": 215, "hue2": 30, "ratio": "21:9"}, layout="overlay", size="lg"),
               search, pad="sm", width="wide"),
             n("Band", grid(*[card(art(ratio="4:3", **spec), between(stack(strong(name), muted(detail), gap="none"), badge(price, "brand")), padding="sm") for name, detail, price, spec in places], columns=4, gap="md"),
               title="This season's favourites", eyebrow="Destinations", align="start", pad="sm", width="wide"),
             n("Band", grid(feature("Plans that flex", "Free changes on every booking until 48 hours before you leave.", "refresh"), feature("A planner that listens", "Tell Voyage the trip you want and get a day-by-day itinerary.", "sparkles", tone="ai"),
                            feature("Local, vetted hosts", "Every stay is visited by someone on our team.", "home", tone="success"), columns=3, gap="lg"), pad="sm", tone="line"),
             n("Band", n("CTA", actions("Plan my trip", "Browse guides"), title="Where to next?", subtitle="Tell us the feeling you are after. We will handle the rest."), pad="md"),
             site_footer("Voyage", "wave", "Travel slowly, remember more."))


@screen("landing/fluidian", "Landing pages", "Fluidian · framework home page", theme="deep", height=2060,
        caption="Fluidian's own home page, built with Fluidian: code beside its result, the numbers and the ideas behind it")
def fluidian_home(ctx):
    sample = "from fluidian import App, ui\n\napp = App(\"Tasks\")\n\n@app.view\ndef view(ctx):\n    return ui.page(\"Tasks\",\n        ui.state().prop(\"values\", {\"todos\": [], \"draft\": \"\"}),\n        ui.input(\"draft\").prop(\"bind\", \"draft\").ai(\"input.ghost\"),\n        ui.button(\"Add\").on(\"click\", \"@push todos draft; draft = ''\"),\n        ui.each(\"todos\", ui.text(\"{{ item }}\")))\n\napp.run()\n"
    result = browser(n("Page", n("Input", name="draft", placeholder="What needs doing?", value="Book the venue for the offsite"), row(btn("Add", "primary"), badge("AI · ghost text", "ai", icon="sparkles"), gap="sm"),
                       n("List", items=[{"title": "Send the Q3 board pack", "icon": "check", "tone": "success"}, {"title": "Review Ana's pull request", "icon": "circle"}, {"title": "Renew the domain", "icon": "circle"}]), title="Tasks", width="narrow"), url="localhost:8787", height=330)
    return n("Landing",
             nav("Fluidian", ["Why Fluidian", "Capabilities", "Components", "SDKs", "Docs"], btn("GitHub", "ghost", icon="branch"), btn("Get started", "primary"), logo="fluidian", tag="1.2"),
             n("Band", n("Hero", actions("Get started", "Open the gallery"), title="The UI framework where AI is a primitive.", highlight="AI is a primitive.", align="center", size="xl", tone="none", badge="185 capabilities · 14 languages · works offline", badgeTag="1.2",
                         subtitle="Describe your interface in the language you already use. Fluidian renders it everywhere and wires intelligence into every component."),
               split(code(sample, "python", title="app.py", tone="dark"), result, ratio="1:1", gap="lg"), pad="md"),
             n("Band", n("Metrics", variant="cards", items=[{"value": "185", "label": "AI capabilities", "detail": "Each with an offline implementation"}, {"value": "123", "label": "components", "detail": "From buttons to storefronts"},
                                                        {"value": "14", "label": "languages", "detail": "One protocol, identical output"}, {"value": "20", "label": "themes", "detail": "Generated in OKLCH, contrast-checked"}]), pad="sm"),
             n("Band", n("Bento",
                         n("BentoCell", n("AgentTimeline", steps=[{"title": "Policy and consent", "status": "done", "duration": "0.2 ms"}, {"title": "Redact personal data", "status": "done", "duration": "0.6 ms"}, {"title": "Route: Reflex or model", "status": "done", "duration": "0.1 ms"},
                                                                 {"title": "Validate and repair output", "status": "running"}]), span=2, rows=2, title="A kernel, not a wrapper", subtitle="Fifteen stages guard every AI call: redaction, budgets, grounding, repair.", icon="cpu"),
                         n("BentoCell", n("LogoCloud", names=["Python", "TypeScript", "Go", "Rust", "Java", "Kotlin", "C#", "C++", "Ruby", "PHP", "Dart", "Elixir", "Lua", "JavaScript"], variant="row"), span=4, title="Write it once, in any of 14 languages", subtitle="`fluidian convert` ports an app between them and proves the result is identical.", icon="swap"),
                         n("BentoCell", row(phone(n("Screen", stat("Balance", "$12,480"), title="Wallet", tabs=[{"label": "Home", "icon": "home", "active": True}, {"label": "Pay", "icon": "swap"}]), platform="ios", scale=0.5, height=420),
                                            phone(n("Screen", stat("Balance", "$12,480"), title="Wallet", tabs=[{"label": "Home", "icon": "home", "active": True}, {"label": "Pay", "icon": "swap"}]), platform="android", scale=0.5, height=420), justify="center", gap="md"),
                           span=2, title="iOS, Android, web", subtitle="One scene, native conventions.", icon="smartphone", tone="soft"),
                         n("BentoCell", n("Insight", title="Revenue is rising", tone="ai", body="Up 47.7% over twelve months, with an unusual spike in August.", bullets=["Works with no API key", "Same output shape as the model"]), span=2, title="Offline by design", subtitle="Every capability has a deterministic twin.", icon="shield", tone="glow"),
                         columns=6), title="Four ideas you will not find together anywhere else", eyebrow="Why Fluidian", highlight="anywhere else", tone="soft"),
             n("Band", n("CTA", n("Code", source="./fluidian gallery", language="bash", tone="dark", title="Try it in ten seconds"), title="No build step. No pip install. Just Python 3.", subtitle="Unzip, run one command and open the gallery."), pad="md"),
             footer("Fluidian", [("Learn", ["Getting started", "Concepts", "AI kernel", "Theming"]), ("Reference", ["Capabilities", "Components", "Protocol", "CLI"]), ("Project", ["Roadmap", "Contributing", "Security", "License"])],
                    "© 2026 The Fluidian Authors. Apache-2.0.", logo="orb", tagline="AI-native interfaces in the language you already use."), backdrop="beams")
