"""Application modules: the screens every product needs."""
from kit import *  # noqa: F401,F403

APP_NAV = [("Home", "home", "Workspace"), ("Inbox", "inbox", "Workspace", "12"), ("Projects", "layers", "Workspace"), ("Calendar", "calendar", "Workspace"), ("Files", "folder", "Library"), ("People", "users", "Library"), ("Settings", "settings", "Admin")]


def app(active, *children, brand="Cadence", **p):
    return shell(brand, APP_NAV, *children, active=active, user={"name": "Mira Okafor", "role": "Admin"}, **p)


@screen("module/auth", "Application modules", "Sign-in", theme="aurora", height=900,
        caption="A split sign-in screen: generated artwork and a testimonial on one side, the form on the other")
def auth(ctx):
    form = stack(row(n("Icon", name="sparkles", size=22, tone="ai"), strong("Lumen", "lg"), gap="xs"), stack(heading("Welcome back", 1), muted("Sign in to your workspace", "md"), gap="xs"),
                 n("Form", field("Work email", "email", "mira@arcwell.example", kind="email", icon="mail"), field("Password", "password", "••••••••••••", kind="password", icon="lock"),
                   between(n("Checkbox", name="remember", label="Keep me signed in", checked=True), n("Link", label="Forgot password?", href="#")), btn("Sign in", "primary", size="lg", block=True), name="signin"),
                 n("Divider", label="or continue with"), grid(btn("Passkey", "secondary", size="lg", icon="fingerprint"), btn("Single sign-on", "secondary", size="lg", icon="key"), columns=2, gap="sm"),
                 row(muted("New to Lumen?", "md"), n("Link", label="Create an account", href="#"), gap="xs", justify="center"), gap="lg")
    side = n("PromoTile", n("Testimonial", quote="We replaced four tools with one workspace. The team stopped asking where things live.", author="Lena Fischer", role="Chief of staff", company="Verano", variant="compact"),
             title="Think it. Lumen makes it real.", highlight="makes it real.", art={"kind": "orbit", "ratio": "3:4"}, layout="overlay", size="xl", align="start")
    return n("Landing", n("Band", split(n("Band", form, width="narrow", pad="md", align="start"), side, ratio="1:1", gap="xl"), pad="sm", width="wide", align="start"), backdrop="glow")


@screen("module/onboarding", "Application modules", "Setup wizard", theme="sunset", height=1000,
        caption="A setup wizard with progress, plan choices and suggestions written by the AI kernel")
def onboarding(ctx):
    return n("Landing", nav("Brightbuild", [], muted("Step 2 of 4", "md"), btn("Save and exit", "ghost"), logo="star"),
             n("Band", n("Steps", current=1, items=[{"title": "Account", "detail": "Done"}, {"title": "Workspace", "detail": "Name and goals"}, {"title": "Team", "detail": "Invite people"}, {"title": "Launch", "detail": "First project"}]),
               split(card(field("Workspace name", "name", "Arcwell Product"), n("TextArea", name="goal", label="What are you building?", rows=3, value="A customer portal where clients can track orders, download invoices and message support."),
                          n("RadioGroup", name="size", label="Team size", layout="cards", value="2–10", options=[{"label": "Just me", "value": "1", "detail": "Solo"}, {"label": "2–10", "value": "2–10", "detail": "Small team"}, {"label": "11–50", "value": "11–50", "detail": "Growing"}, {"label": "50+", "value": "50+", "detail": "Organisation"}]),
                          n("TagInput", name="stack", label="What do you already use?", value=["PostgreSQL", "Stripe"], suggestions=["Slack", "GitHub", "Figma", "HubSpot"]),
                          between(btn("Back", "ghost", icon="arrow-left"), btn("Continue", "primary", size="lg")), title="Tell us about your workspace", subtitle="We use this to set up sensible defaults. You can change everything later."),
                     stack(n("Insight", title="Suggested starting point: Customer portal", tone="ai", body="Based on your description we would scaffold sign-in, an orders table, invoices and a support inbox.", bullets=["3 pages and 2 database tables", "Stripe invoices connected", "Roles: customer, agent, admin"]),
                           card(art("ui", variant="dashboard", ratio="16:9", seed=2), between(stack(strong("Customer portal"), muted("Recommended template"), gap="none"), badge("92% match", "success")), padding="sm"),
                           n("Callout", title="Nothing is created yet", body="You will review the plan on the last step before anything is built.", tone="info")), ratio="5:3", gap="xl"), pad="sm", align="start"), backdrop="mesh")


@screen("module/settings", "Application modules", "Settings", theme="deep", height=1160,
        caption="Account settings: profile, preferences, security, a plan card and a danger zone")
def settings(ctx):
    return app(6, page("Settings",
                       n("Tabs", n("Tab", split(stack(card(row(n("Avatar", name="Mira Okafor", size="lg"), stack(strong("Mira Okafor"), muted("mira@arcwell.example"), gap="none"), btn("Change photo", "secondary", size="sm"), gap="md"),
                                                          grid(field("Full name", "name", "Mira Okafor"), field("Role", "role", "Finance lead"), columns=2), field("Email", "email", "mira@arcwell.example", kind="email"), n("Select", name="tz", label="Time zone", value="Europe/Lisbon (UTC+0)", options=["Europe/Lisbon (UTC+0)", "Europe/Berlin (UTC+1)", "America/New_York (UTC−5)"]), title="Profile"),
                                                     card(n("Toggle", name="digest", label="Weekly summary email", checked=True, help="Mondays at 08:00"), n("Toggle", name="mentions", label="Notify me about mentions", checked=True), n("Toggle", name="ai", label="AI suggestions while typing", checked=True, help="Ghost text and format healing"),
                                                          n("Segmented", name="theme", label="Appearance", value="System", options=["Light", "Dark", "System"]), n("Segmented", name="density", label="Density", value="Comfortable", options=["Compact", "Comfortable", "Spacious"]), title="Preferences")),
                                               stack(card(between(stack(strong("Team plan", "lg"), muted("12 of 20 seats · renews 1 January"), gap="none"), badge("Active", "success", dot=True)), n("Progress", label="Seats", value=60), n("Progress", label="AI credits · 41,200 of 100,000", value=41, tone="ai"), row(btn("Manage plan", "secondary"), btn("View invoices", "ghost"), gap="sm"), title="Plan"),
                                                     card(n("List", items=[{"title": "Password", "detail": "Changed 4 months ago", "meta": "Update", "icon": "lock"}, {"title": "Two-step verification", "detail": "Authenticator app", "badge": "On", "tone": "success", "icon": "shield"}, {"title": "Passkeys", "detail": "2 devices", "meta": "Manage", "icon": "fingerprint"}, {"title": "Active sessions", "detail": "3 devices", "meta": "Review", "icon": "monitor"}]), title="Security"),
                                                     card(muted("Deleting the workspace removes every project, file and member. This cannot be undone.", "md"), row(btn("Export data", "secondary", icon="download"), btn("Delete workspace", "danger"), gap="sm"), title="Danger zone", tone="danger")), ratio="5:4", gap="lg"), label="Account"),
                         n("Tab", muted("Team settings"), label="Team", badge="12"), n("Tab", muted("Billing"), label="Billing"), n("Tab", muted("Integrations"), label="Integrations"), n("Tab", muted("API keys"), label="API keys")),
                       subtitle="Manage your account and workspace", width="wide"))


MAIL = [("Ana Lima", "Payment sheet ready for review", "Both wallets are wired up. Accessibility fixes land tomorrow…", "09:41", True), ("Kestrel Energy", "Your November statement", "Your bill of $86.20 will be collected on 24 November…", "08:15", True),
        ("Jonas Weber", "Re: Go or no-go on Friday", "09:30 works. I will bring the review notes…", "Yesterday", False), ("Priya Nair", "Retention chart for the board pack", "Attached is the cohort view you asked for…", "Yesterday", False),
        ("Halden Rail", "Booking confirmed: Porto → Lisbon", "Your seat is 12A in coach 3…", "Tue", False), ("Lena Fischer", "Thanks for the intro", "We spoke this morning and it went well…", "Mon", False)]


@screen("module/inbox", "Application modules", "Mail client", theme="iris", height=1040,
        caption="A three-pane mail client with an AI summary and a drafted reply above the thread")
def inbox(ctx):
    listing_ = card(n("Search", name="q", placeholder="Search mail", kbd="/"), n("Segmented", name="filter", value="All", options=["All", "Unread", "Flagged"]),
                    n("List", items=[{"title": who, "detail": subject + " — " + preview, "meta": when, "avatar": who, **({"badge": "New", "tone": "brand"} if unread else {})} for who, subject, preview, when, unread in MAIL]), padding="sm")
    thread = card(between(stack(heading("Payment sheet ready for review", 2), row(n("Avatar", name="Ana Lima", size="sm"), muted("Ana Lima to you, Jonas, Kenji · 09:41"), gap="xs"), gap="xs"), row(btn("", "ghost", icon="archive"), btn("", "ghost", icon="trash"), btn("", "ghost", icon="more"), gap="xs")),
                  n("Insight", title="Summary", tone="ai", body="Ana finished Apple Pay and Google Pay. She needs a decision on Friday about shipping before the holiday freeze; the open risk is accessibility.", bullets=["Asks you: confirm the Friday 09:30 review", "Attachment: payment-sheet-v4.fig"]),
                  n("Markdown", source="Hi all,\n\nBoth wallets are wired up and passing in the sandbox. The remaining work is the accessibility pass, which Kenji expects to finish on Wednesday.\n\nCould we hold the **go or no-go on Friday at 09:30**? If we miss the freeze, the next window is 12 January.\n\nAna"),
                  card(n("TextArea", name="reply", rows=3, value="Thanks Ana — great progress. Friday 09:30 works for me. Could you add the test results to the invite?"), between(row(badge("Drafted by AI", "ai", icon="sparkles"), n("Suggestions", items=[{"label": "Shorter"}, {"label": "Warmer"}, {"label": "Decline politely"}]), gap="sm"), btn("Send", "primary", icon="send")), padding="sm"))
    return app(1, page("", split(listing_, thread, ratio="2:3", gap="lg"), width="full"))


@screen("module/calendar", "Application modules", "Calendar", theme="sky", height=1080,
        caption="A month calendar with an agenda and scheduling suggestions from the AI kernel")
def calendar(ctx):
    events = [{"day": 3, "label": "Board prep", "tone": "brand"}, {"day": 5, "label": "Design critique", "tone": "ai"}, {"day": 10, "label": "Sprint review", "tone": "success"}, {"day": 12, "label": "Launch", "tone": "danger"}, {"day": 12, "label": "Team dinner", "tone": "warning"},
              {"day": 17, "label": "1:1 Jonas", "tone": "brand"}, {"day": 19, "label": "Checkout sync", "tone": "brand"}, {"day": 19, "label": "Dentist", "tone": "neutral"}, {"day": 19, "label": "Go / no-go prep", "tone": "ai"}, {"day": 20, "label": "Go / no-go", "tone": "danger"}, {"day": 24, "label": "Offsite", "tone": "success"}, {"day": 25, "label": "Offsite", "tone": "success"}, {"day": 27, "label": "Payroll", "tone": "warning"}]
    return app(3, page("Calendar",
                       between(row(n("Segmented", name="view", value="Month", options=["Day", "Week", "Month"]), btn("Today", "secondary"), gap="sm"), row(n("AvatarStack", names=PEOPLE[:4], label="Team calendars"), btn("New event", "primary", icon="plus"), gap="sm")),
                       split(card(n("Calendar", month="2026-11", events=events, today=19, selected=19)),
                             stack(card(n("Schedule", from_=9, to_=17, now="11:20", rowHeight=40, items=[{"start": "09:30", "end": "10:15", "title": "Checkout sync", "tone": "brand"}, {"start": "11:00", "end": "12:00", "title": "Go / no-go prep", "tone": "ai"}, {"start": "14:00", "end": "14:45", "title": "Dentist", "tone": "neutral"}, {"start": "15:30", "end": "16:30", "title": "Focus: board pack", "tone": "success"}]), title="Thursday 19", subtitle="4 events"),
                                   n("Insight", title="Move focus time to 13:00", tone="ai", body="Your dentist appointment splits the afternoon. A 13:00 block gives you 60 uninterrupted minutes.", bullets=[]),
                                   card(n("Suggestions", variant="list", title="Find a time with Jonas and Ana", items=[{"label": "Fri 20 · 14:00–14:30", "detail": "All free", "icon": "check"}, {"label": "Mon 23 · 10:00–10:30", "detail": "All free", "icon": "check"}, {"label": "Mon 23 · 16:00–16:30", "detail": "Ana tentative", "icon": "clock"}]))), ratio="2:1", gap="lg"),
                       subtitle="November 2026", width="wide"))


@screen("module/files", "Application modules", "File manager", theme="grape", height=1060,
        caption="A file manager with generated thumbnails, a details panel and search by meaning rather than filename")
def files(ctx):
    items = [("Q3 board pack.pdf", "PDF · 4.2 MB", {"kind": "ui", "variant": "landing", "seed": 4}), ("Brand refresh", "Folder · 48 items", {"kind": "blocks", "seed": 2}), ("Checkout flows.fig", "Design · 18 MB", {"kind": "ui", "variant": "mobile", "seed": 6}), ("Launch film.mp4", "Video · 212 MB", {"kind": "orbit"}),
             ("Retention cohort.csv", "Table · 86 KB", {"kind": "ui", "variant": "dashboard", "seed": 9}), ("Offsite photos", "Folder · 126 items", {"kind": "peaks", "hue": 280}), ("Pricing model.xlsx", "Sheet · 1.1 MB", {"kind": "grid"}), ("Voice memo 14.m4a", "Audio · 6 MB", {"kind": "waves"})]
    return app(4, page("Files",
                       between(n("Search", name="q", value="the deck with the churn chart from last quarter", kbd="/"), row(n("Segmented", name="view", value="Grid", options=["Grid", "List"]), btn("Upload", "primary", icon="upload"), gap="sm")),
                       n("Banner", text="Showing files that match the meaning of your search. “Q3 board pack.pdf” mentions churn on page 7.", tone="ai", icon="sparkles"),
                       split(grid(*[card(art(ratio="4:3", **spec), stack(strong(name), muted(meta), gap="none"), padding="sm") for name, meta, spec in items], columns=4, gap="md"),
                             card(art("ui", variant="landing", seed=4, ratio="4:3"), stack(strong("Q3 board pack.pdf", "lg"), muted("PDF · 42 pages · 4.2 MB"), gap="none"),
                                  n("KeyValue", items=[{"key": "Owner", "value": "Priya Nair"}, {"key": "Modified", "value": "12 November, 16:20"}, {"key": "Shared with", "value": "Leadership (8 people)"}]),
                                  n("Insight", title="What is inside", tone="ai", body="Quarterly results: revenue up 18%, churn down to 3.1%, hiring nine behind plan.", bullets=["Churn chart on page 7", "Open question on EMEA launch, page 12"]),
                                  row(btn("Open", "primary"), btn("Share", "secondary", icon="share"), btn("", "ghost", icon="download"), gap="sm"), title="Details"), ratio="5:2", gap="lg"),
                       subtitle="Workspace · 2,481 files · 38 GB of 100 GB", width="wide"))


@screen("module/kanban", "Application modules", "Kanban board", theme="forest", height=1000,
        caption="A kanban board in the Forest theme with tags, assignees and a suggested next priority")
def kanban(ctx):
    c = lambda t, d, who, *tags: {"title": t, "detail": d, "tags": list(tags), "assignee": who}  # noqa: E731
    board = n("Board", columns=[{"title": "Backlog", "cards": [c("Export to spreadsheet", "Requested by 14 customers", PEOPLE[4], "Feature"), c("Dark mode for emails", "Design ready", PEOPLE[6], "Design"), c("Audit log retention", "Needs legal input", PEOPLE[7], "Compliance"), c("Bulk invite by CSV", "Small", PEOPLE[1], "Feature")]},
                                {"title": "This sprint", "cards": [c("Payment sheet: wallets", "Blocks the release", PEOPLE[2], "Checkout", "P0"), c("Accessibility fixes", "17 issues from the audit", PEOPLE[3], "Mobile", "P0"), c("Invoice backfill", "2019–2021 records", PEOPLE[5], "Billing")]},
                                {"title": "In review", "cards": [c("New onboarding checklist", "2 approvals needed", PEOPLE[0], "Growth"), c("Rate limit headers", "Docs updated", PEOPLE[9], "API")]},
                                {"title": "Done", "cards": [c("Passkey sign-in", "Shipped 14 Nov", PEOPLE[8], "Security"), c("Faster search index", "p95 down 61%", PEOPLE[9], "Platform"), c("Button guidelines", "Published", PEOPLE[6], "Design system")]}])
    return app(2, page("Checkout redesign",
                       between(row(n("AvatarStack", names=PEOPLE[:6], max_=5), badge("Sprint 23 · 4 days left", "info"), n("Progress", label="", value=68, showValue=False), gap="md"), row(btn("Filter", "secondary", icon="filter"), btn("Add task", "primary", icon="plus"), gap="sm")),
                       n("Insight", title="Start “Accessibility fixes” next", tone="ai", body="It blocks the Friday decision and has no dependency. Kenji has capacity; Ana is over by six points.", bullets=[]),
                       board, subtitle="12 open · 3 in review · 68% of the sprint delivered", width="full"))


@screen("module/table", "Application modules", "Data grid", theme="emerald", height=1040,
        caption="A dense data grid with plain-language filtering, bulk actions, status badges and pagination")
def data_grid(ctx):
    names = ["Arcwell", "Kestrel Energy", "Oakline Health", "Lumina Semis", "Northpass", "Halden Rail", "Tessellate Labs", "Quillon", "Verano", "Brightside", "Globe & Anchor", "Meridian Works"]
    rows = [{"account": nm, "owner": PEOPLE[i % 10], "plan": ["Enterprise", "Team", "Team", "Enterprise", "Starter", "Team"][i % 6], "seats": [240, 38, 64, 410, 6, 52][i % 6] + i, "mrr": [18400, 2280, 3840, 31600, 240, 3120][i % 6] + i * 37,
             "health": ["Healthy", "Healthy", "At risk", "Healthy", "Trial", "Churned"][i % 6], "renewal": "2027-%02d-%02d" % (1 + i % 12, 3 + i * 2)} for i, nm in enumerate(names)]
    cols = [("account", "Account"), ("owner", "Owner"), ("plan", "Plan", "badge"), ("seats", "Seats", "number", "end"), ("mrr", "MRR", "currency", "end"), ("health", "Health", "badge"), ("renewal", "Renewal", "date")]
    return app(2, page("Accounts",
                       kpis(("Accounts", "1,284", "+38", "this quarter", "building"), ("MRR", "$1.42M", "+6.1%", "vs last month", "dollar", 501), ("At risk", "27", "-4", "since Monday", "alert"), ("Net retention", "118%", "+3 pts", "trailing 12 months", "refresh", 502)),
                       card(between(row(btn("All accounts", "primary", size="sm"), btn("Enterprise", "secondary", size="sm"), btn("At risk", "secondary", size="sm"), btn("Renewing in 90 days", "secondary", size="sm"), gap="xs"), row(btn("Columns", "ghost", size="sm", icon="sliders"), btn("Export", "secondary", size="sm", icon="download"), btn("Add account", "primary", size="sm", icon="plus"), gap="xs")),
                            n("Table", columns=[{"key": c[0], "label": c[1], **({"format": c[2]} if len(c) > 2 else {}), **({"align": c[3]} if len(c) > 3 else {})} for c in cols], rows=rows, pageSize=10, striped=True).ai("data.query"),
                            between(row(muted("Expansion revenue, last 12 weeks"), n("Sparkline", values=series(77, 12, 40, 3.2, 5), kind="area", tone="success", width=132, height=30), gap="sm"),
                                    row(muted("Churned seats"), n("Sparkline", values=[abs(round(v * 9)) + 2 for v in noise(31, 12)], kind="bar", tone="warning", width=96, height=30), gap="sm")),
                            title="All accounts", subtitle="Type a question above the table: “enterprise accounts at risk, largest first”"),
                       subtitle="Sales workspace", width="wide"), brand="Northpass")


@screen("module/notifications", "Application modules", "Notification centre", theme="candy", height=1040,
        caption="A notification centre: grouped activity, an AI digest of what matters and per-channel preferences")
def notifications(ctx):
    feed = [("Ana Lima mentioned you", "“@Mira can you confirm Friday 09:30?” in Checkout redesign", "4m", "Ana Lima", None, "Mention"), ("Deployment succeeded", "checkout-api · production · 42 seconds", "12m", "check-circle", "success"), ("Invoice INV-2041 is overdue", "Globex Marine · $12,400 · 22 days", "1h", "alert", "danger", "Action"),
            ("Kenji Sato assigned you a task", "Review accessibility fixes · due Wednesday", "2h", "Kenji Sato", None, "Task"), ("Weekly report is ready", "Revenue up 6.0%, churn down 0.4 points", "3h", "chart", "info"), ("New sign-in from Lisbon", "Chrome on macOS · if this wasn't you, review sessions", "5h", "shield", "warning"),
            ("Priya Nair shared a file", "Retention cohort.csv", "Yesterday", "Priya Nair")]
    return app(1, page("Notifications",
                       between(n("Segmented", name="tab", value="All", options=["All", "Mentions", "Tasks", "System"]), row(btn("Mark all as read", "secondary", icon="check"), btn("", "ghost", icon="settings"), gap="sm")),
                       split(stack(n("Insight", title="Three things need you today", tone="ai", body="The rest can wait: 14 notifications were routine and have been grouped.", bullets=["Confirm the Friday review with Ana", "Chase invoice INV-2041 (22 days overdue)", "Review the accessibility fixes before Wednesday"]),
                                   card(listing(feed), title="Today", subtitle="7 new", padding="md")),
                             stack(card(n("Toggle", name="n1", label="Mentions and replies", checked=True, help="Push and email"), n("Toggle", name="n2", label="Task assignments", checked=True, help="Push only"), n("Toggle", name="n3", label="Deployments", help="In-app only"),
                                        n("Toggle", name="n4", label="Security alerts", checked=True, help="Always on"), n("Toggle", name="n5", label="AI daily digest", checked=True, help="Weekdays at 08:30"), title="Preferences"),
                                   card(n("Segmented", name="quiet", label="Quiet hours", value="19:00 – 08:00", options=["Off", "19:00 – 08:00", "Custom"]), n("Callout", title="Focus mode is on until 13:00", body="Only mentions from your team come through.", tone="info"), title="Do not disturb")), ratio="5:3", gap="lg"),
                       subtitle="7 unread · 14 grouped", width="wide"))


@screen("module/team", "Application modules", "Team directory", theme="mint", height=1040,
        caption="A team directory: member cards with presence, roles, workload and pending invitations")
def team(ctx):
    roles = ["Finance lead", "Programme lead", "Product designer", "iOS engineer", "Data scientist", "Courier ops", "Design systems", "Security", "Creator success", "Platform"]
    member = lambda i, who: card(row(n("Avatar", name=who, size="lg", status=["online", "online", "away", "online", "busy", "online"][i % 6]), stack(strong(who), muted(roles[i]), gap="none"), gap="md", wrap=False),  # noqa: E731
                                 n("Progress", label="Workload", value=[72, 55, 94, 61, 38, 80, 47, 66, 58, 70][i], tone="danger" if i == 2 else "brand"), between(row(badge(["Admin", "Member", "Member", "Member", "Guest"][i % 5], "neutral"), gap="xs"), row(btn("", "ghost", icon="message"), btn("", "ghost", icon="more"), gap="xs")), padding="md")
    return app(5, page("People",
                       between(n("Search", name="q", placeholder="Search 42 people"), row(n("Select", name="team", value="All teams", options=["All teams", "Product", "Engineering", "Design", "Operations"]), btn("Invite people", "primary", icon="plus"), gap="sm")),
                       grid(*[member(i, who) for i, who in enumerate(PEOPLE[:9])], columns=3, gap="md"),
                       split(card(listing([("idris.bello@arcwell.example", "Invited by Mira · 2 days ago", "Resend", "mail", "info", "Pending"), ("sofia.marin@arcwell.example", "Invited by Jonas · 5 days ago", "Resend", "mail", "info", "Pending")]), title="Pending invitations"),
                             n("Insight", title="Ana is over capacity this sprint", tone="ai", body="She holds 34 points against a plan of 24. Tomás and Omar have room for the invoice backfill.", bullets=[]), ratio="5:3"),
                       subtitle="42 members · 3 guests · 2 pending", width="wide"))


@screen("module/billing", "Application modules", "Billing and usage", theme="ocean", height=1100,
        caption="Billing: the current plan, metered usage against limits, a payment method and invoice history")
def billing(ctx):
    invoices = [{"invoice": "INV-2026-011", "period": "November 2026", "amount": 648.00, "status": "Pending"}, {"invoice": "INV-2026-010", "period": "October 2026", "amount": 612.40, "status": "Paid"}, {"invoice": "INV-2026-009", "period": "September 2026", "amount": 590.00, "status": "Paid"},
                {"invoice": "INV-2026-008", "period": "August 2026", "amount": 590.00, "status": "Paid"}, {"invoice": "INV-2026-007", "period": "July 2026", "amount": 548.20, "status": "Paid"}]
    return app(6, page("Billing",
                       split(stack(card(between(stack(muted("Current plan", "xs"), strong("Team · annual", "xl"), muted("20 seats · $24 per seat / month · renews 1 January 2027", "md"), gap="xs"), stack(strong("$480.00", "xl"), muted("per month"), gap="none", align="end")),
                                        row(btn("Change plan", "primary"), btn("Add seats", "secondary"), btn("Cancel", "ghost"), gap="sm"), title="Plan"),
                                   card(n("Progress", label="Seats · 12 of 20", value=60), n("Progress", label="AI credits · 41,200 of 100,000", value=41, tone="ai"), n("Progress", label="Storage · 38 GB of 100 GB", value=38, tone="success"), n("Progress", label="API requests · 9.1M of 10M", value=91, tone="warning"),
                                        n("Callout", title="API requests will reach the limit on 26 November", body="At the current rate. Overage is billed at $0.40 per 100,000 requests.", tone="warning"), title="Usage this period", subtitle="1 – 30 November"),
                                   card(table([("invoice", "Invoice"), ("period", "Period"), ("amount", "Amount", "currency", "end"), ("status", "Status", "badge")], invoices, dense=True), title="Invoices", padding="none")),
                             stack(card(art("card", hue=215, hue2=170, ratio="16:9", label="4821"), n("KeyValue", columns=2, items=[{"key": "Card", "value": "Ending 4821"}, {"key": "Expires", "value": "08 / 2029"}, {"key": "Billing email", "value": "accounts@arcwell.example"}, {"key": "Tax ID", "value": "PT 509 442 013"}]), btn("Update payment method", "secondary", block=True), title="Payment method"),
                                   card(chart("bar", [{"month": m, "Spend": v} for m, v in zip(MONTHS[5:11], [520, 548, 590, 590, 612, 648])], "month", "Spend", height=170, legend=False, format="currency"), title="Spend", subtitle="Last six months"),
                                   n("Insight", title="Annual billing would save $1,152", tone="ai", body="You have paid monthly overage in four of the last six months. The next tier includes it.", bullets=[])), ratio="5:3", gap="lg"),
                       subtitle="Arcwell Product workspace", width="wide"))


@screen("module/pricing", "Application modules", "Pricing page", theme="citrus", height=1700,
        caption="A complete pricing page: plan cards, a feature comparison and frequently asked questions")
def pricing(ctx):
    return n("Landing",
             nav("Crate", ["Product", "Solutions", "Pricing", "Docs"], btn("Sign in", "ghost"), btn("Start free", "primary"), logo="drop"),
             n("Band", n("Hero", row(n("Segmented", name="cycle", value="Annual · save 20%", options=["Monthly", "Annual · save 20%"]), justify="center"), title="Pricing that grows with you.", highlight="grows with you.", align="center", size="lg", tone="none", subtitle="Start free. Upgrade when your team does. No per-feature surprises."),
               grid(n("PricingCard", plan="Starter", price="$0", period="forever", description="For individuals and side projects.", features=["3 projects", "1 GB storage", "Community support", {"label": "Custom domain", "included": False}, {"label": "Single sign-on", "included": False}], cta="Start free"),
                    n("PricingCard", plan="Team", price="$19", period="per seat / month", description="For teams that ship together.", features=["Unlimited projects", "100 GB storage", "Priority support", "Custom domain", {"label": "Single sign-on", "included": False}], cta="Start 14-day trial", featured=True, badge="Most popular"),
                    n("PricingCard", plan="Business", price="$39", period="per seat / month", description="For organisations with security needs.", features=["Everything in Team", "1 TB storage", "Single sign-on and SCIM", "Audit log", "99.99% uptime SLA"], cta="Talk to sales"), columns=3, gap="lg"), pad="md"),
             n("Band", n("Comparison", label="Compare plans", plans=[{"name": "Starter", "price": "$0"}, {"name": "Team", "price": "$19", "featured": True}, {"name": "Business", "price": "$39"}],
                         rows=[{"group": "Workspace"}, {"label": "Projects", "values": ["3", "Unlimited", "Unlimited"]}, {"label": "Storage", "values": ["1 GB", "100 GB", "1 TB"]}, {"label": "Guests", "values": [False, "10", "Unlimited"]},
                               {"group": "AI"}, {"label": "AI credits per month", "values": ["1,000", "50,000", "250,000"]}, {"label": "Offline (Reflex) answers", "values": [True, True, True]}, {"label": "Bring your own model key", "values": [False, True, True]},
                               {"group": "Security"}, {"label": "Two-step verification", "values": [True, True, True]}, {"label": "Single sign-on", "values": [False, False, True]}, {"label": "Audit log", "values": [False, "30 days", "1 year"]}]),
               title="Every feature, side by side", eyebrow="Compare", tone="line", pad="sm"),
             n("Band", n("FAQ", items=[{"q": "Can I change plans later?", "a": "Yes. Upgrades apply immediately and are prorated. Downgrades take effect at the end of the billing period."}, {"q": "What counts as a seat?", "a": "Anyone who can edit. Viewers and guests are free on every plan."},
                                       {"q": "Do you offer discounts?", "a": "Non-profits and schools get 50% off. Start-ups under two years old get the first year of Team free."}, {"q": "What happens to my data if I cancel?", "a": "You can export everything for 90 days. After that it is deleted."}]), title="Questions", width="narrow", pad="sm"),
             backdrop="glow")


@screen("module/changelog", "Application modules", "Changelog", theme="midnight", height=1100,
        caption="A changelog with release entries, tagged improvements and a subscription card")
def changelog(ctx):
    entry = lambda version, date, title, body, tags, spec: split(stack(strong(version, "lg"), muted(date), gap="none"), card(art(ratio="21:9", **spec), n("Heading", text=title, level=2), muted(body, "md"), row(*[badge(t, tone) for t, tone in tags], gap="xs")), ratio="1:5", gap="lg")  # noqa: E731
    return n("Landing",
             nav("Relay", ["Models", "Routing", "Docs", "Changelog"], btn("Sign in", "ghost"), btn("Get an API key", "primary"), logo="arc"),
             n("Band", n("Hero", row(n("Input", name="email", placeholder="you@company.example", icon="mail"), btn("Subscribe", "primary"), gap="sm"), title="What's new", size="lg", tone="none", subtitle="Every improvement to Relay, newest first. Shipping most weeks."),
               entry("4.2", "19 November 2026", "Automatic failover for every model", "When a provider slows down or errors, requests move to your fallback in under two seconds. No code changes: it is on by default.", [("New", "success"), ("Routing", "brand"), ("Reliability", "info")], {"kind": "beams"}),
               entry("4.1", "5 November 2026", "Budgets per team and per key", "Set a monthly limit, choose what happens at 80% and 100%, and get a forecast of when you will reach it.", [("New", "success"), ("Console", "brand")], {"kind": "rings"}),
               entry("4.0", "22 October 2026", "Offline answers with Reflex", "Common tasks such as classification and extraction can now be answered without a model call. Median latency drops to 3 ms.", [("Major", "danger"), ("Cost", "warning"), ("Performance", "info")], {"kind": "grid"}),
               pad="sm", width="default", align="start"), backdrop="dots")


@screen("module/command", "Application modules", "Command palette", theme="moss", height=980,
        caption="The command palette: language routed to actions, with the matched arguments shown before anything runs")
def command(ctx):
    suggestions = [{"label": "Create invoice for Globex Marine for $1,200, due Friday", "detail": "create_invoice · customer, amount, due", "icon": "plus", "group": "Best match"}, {"label": "Send payment reminder for INV-2041", "detail": "send_reminder · invoice", "icon": "bell"},
                   {"label": "Open the revenue dashboard", "detail": "open_page · page", "icon": "chart"}, {"label": "Export this view as CSV", "detail": "export_report · format", "icon": "download"}, {"label": "Invite a teammate", "detail": "invite_member · email, role", "icon": "users"}]
    return app(0, page("Command",
                       n("IntentBar", open=True, query="invoice globex 1200 friday", placeholder="What would you like to do?", suggestions=suggestions, hint="↵ to run · ⇥ to edit arguments · esc to close"),
                       split(card(n("KeyValue", columns=3, items=[{"key": "Action", "value": "create_invoice"}, {"key": "Customer", "value": "Globex Marine"}, {"key": "Amount", "value": "$1,200.00"}, {"key": "Due", "value": "Friday 20 November"}, {"key": "Confidence", "value": "94%"}, {"key": "Needs approval", "value": "No"}]),
                                  n("Callout", title="Arguments are parsed before anything runs", body="“1200” became an amount and “friday” became a date in your locale. Edit any of them, or press Enter to run.", tone="ai"), title="What will happen", subtitle="Parsed by command.route · works offline"),
                             card(n("List", dense=True, items=[{"title": "Open command palette", "meta": "⌘ K", "icon": "command"}, {"title": "Ask about anything on screen", "meta": "⌥ click", "icon": "cursor"}, {"title": "Search everywhere", "meta": "/", "icon": "search"}, {"title": "New invoice", "meta": "N", "icon": "plus"}, {"title": "Toggle developer tools", "meta": "⌘ .", "icon": "terminal"}]), title="Shortcuts"), ratio="5:3", gap="lg"),
                       subtitle="Type what you want. Fluidian finds the action and fills in the details.", width="wide"), brand="Northwind")


@screen("module/docs", "Application modules", "Documentation site", theme="abyss", height=1160,
        caption="A documentation layout: section navigation, an article with highlighted code and an on-this-page rail")
def docs(ctx):
    side = n("Tree", items=[{"label": "Getting started", "icon": "rocket", "children": [{"label": "Installation"}, {"label": "Your first app"}, {"label": "Project layout"}]}, {"label": "Concepts", "icon": "book", "children": [{"label": "Scenes and nodes"}, {"label": "State and events"}, {"label": "Portable logic"}]},
                            {"label": "AI kernel", "icon": "cpu", "children": [{"label": "Capabilities"}, {"label": "Reflex"}, {"label": "Guardrails"}]}, {"label": "Reference", "icon": "list", "children": [{"label": "Components"}, {"label": "CLI"}]}])
    sample = "from fluidian import App, ui\n\napp = App(\"Counter\")\n\n@app.view\ndef view(ctx):\n    return ui.page(\"Counter\",\n        ui.state().prop(\"values\", {\"count\": 0}),\n        ui.text(\"Count: {{ count }}\"),\n        ui.button(\"Add one\").on(\"click\", \"@count += 1\"))\n\napp.run()\n"
    article = stack(n("Breadcrumbs", items=[{"label": "Docs", "route": "#"}, {"label": "Concepts", "route": "#"}, {"label": "Portable logic"}]), n("Heading", text="Portable logic", level=1, eyebrow="Concepts"),
                    muted("Behaviour that travels with the scene, so it runs the same in every SDK language and on every platform.", "lg"),
                    n("Markdown", source="An action whose name starts with `@` is run by the runtime, not by your app. It can read and write **state** declared with a `State` node, and any string prop can display that state with `\\{{ }}` bindings.\n\nBecause the behaviour is data, a scene that uses portable logic converts between languages with nothing left to port by hand."),
                    tabs(("Python", code(sample, "python", title="counter.py")), ("Go", code("app.View(func(ctx *fl.Ctx) *fl.Node {\n\treturn fl.Page(\"Counter\",\n\t\tfl.State().Prop(\"values\", fl.M{\"count\": 0}),\n\t\tfl.Text(\"Count: {{ count }}\"),\n\t\tfl.Button(\"Add one\").On(\"click\", \"@count += 1\"))\n})", "go", title="main.go")), ("Rust", code("app.view(|_ctx| {\n    ui::page(\"Counter\", vec![\n        ui::state().prop(\"values\", jobj!{\"count\" => 0}),\n        ui::text(\"Count: {{ count }}\"),\n        ui::button(\"Add one\").on(\"click\", \"@count += 1\"),\n    ])\n});", "rust", title="main.rs")), variant="pill"),
                    n("Callout", title="Tip", body="Run `fluidian convert counter.py --to all` to generate this app in the other thirteen languages and verify that every one renders the same scene.", tone="info"),
                    between(btn("Scenes and nodes", "secondary", icon="arrow-left"), btn("The AI kernel", "primary")), gap="lg")
    toc = card(n("List", dense=True, divided=False, items=[{"title": "State"}, {"title": "Bindings"}, {"title": "Actions"}, {"title": "Show and Each"}, {"title": "Calling the kernel"}, {"title": "Limits"}]), n("Divider"), muted("Last updated 19 November 2026"), row(btn("Edit this page", "ghost", size="sm", icon="edit"), gap="xs"), title="On this page")
    return n("Landing", nav("Fluidian", ["Guides", "Reference", "Capabilities", "Showcase"], n("Search", name="q", placeholder="Search the docs", kbd="/"), btn("GitHub", "ghost", icon="branch"), logo="fluidian", tag="Docs"),
             n("Band", split(card(side, padding="sm"), article, toc, ratio="3:8:3", gap="xl"), pad="sm", width="wide", align="start"))


def swatch(name):
    return n("Theme", card(between(strong(name.capitalize()), badge("Aa", "brand")), stat("Revenue", "$284k", delta="+6.0%", spark=series(sum(map(ord, name)), 12, 100, 2, 6)),
                           row(btn("Primary", "primary", size="sm"), btn("Secondary", "secondary", size="sm"), badge("AI", "ai", icon="sparkles"), gap="xs"), n("Progress", value=64, showValue=False), padding="md"), preset=name)


@screen("module/themes", "Application modules", "Theme wall", theme="paper", height=1300,
        caption="All twenty-seven built-in themes on one page, each applied to the same card with a single Theme node")
def themes(ctx):
    names = ["deep", "abyss", "iris", "midnight", "aurora", "sunset", "ember", "ocean", "forest", "moss", "rose", "grape", "citrus", "sand", "graphite", "paper", "terminal", "crimson", "candy", "mint", "gold", "sky", "emerald", "neon", "ruby", "lagoon", "tangerine"]
    return n("Landing", n("Band", grid(*[swatch(nm) for nm in names], columns=6, gap="md"), title="Twenty-seven themes, one prop.", highlight="one prop.", eyebrow="Theme presets", pad="sm", width="wide",
                          subtitle="Every theme is a set of design tokens generated in OKLCH and repaired for contrast. Wrap any part of a page in Theme to switch."))
