"""AI products: the interfaces teams build on top of models."""
from kit import *  # noqa: F401,F403

AI_NAV = [("Chat", "message", "Workspace"), ("Agents", "bot", "Workspace"), ("Playground", "terminal", "Workspace"), ("Knowledge", "book", "Workspace"), ("Evaluations", "target", "Quality"), ("Guardrails", "shield", "Quality"), ("Usage", "chart", "Quality")]


def ai_shell(active, *children, brand="Lumen", **p):
    return shell(brand, AI_NAV, *children, active=active, user={"name": "Mira Okafor", "role": "Workspace admin"}, tagline="AI workspace", **p)


@screen("ai/chat", "AI products", "Assistant chat", theme="aurora", height=1080,
        caption="An assistant conversation with tool calls, citations and follow-ups, beside the sources it read")
def chat(ctx):
    talk = n("Chat", variant="flat", placeholder="Ask a follow-up…", messages=[
        {"from": "me", "text": "Compare our Q3 churn with Q2 and tell me which segment moved most."},
        {"from": "ai", "tool": {"label": "Queried warehouse", "detail": "churn_by_segment · 2 quarters", "icon": "database"}, "rich": True,
         "text": "**Churn fell from 3.8% to 3.1%.** The largest move was in *Self-serve*, down 1.9 points after the onboarding redesign. *Enterprise* was flat and *Mid-market* rose slightly.\n\n- Self-serve: 6.2% → 4.3%\n- Mid-market: 2.4% → 2.7%\n- Enterprise: 0.9% → 0.9%",
         "citations": ["churn_by_segment", "Onboarding launch notes", "Q3 board pack p.7"]},
        {"from": "me", "text": "Chart the three segments by month and draft a note for the leadership channel."},
        {"from": "ai", "tool": {"label": "Drew a chart", "detail": "line · 6 months", "icon": "line-chart"}, "rich": True,
         "text": "Here is the chart. I drafted a four-sentence note and kept the numbers exactly as they appear in the warehouse.",
         "chips": ["Make it shorter", "Add the revenue impact", "Post to #leadership"]}])
    trend = chart("line", [{"month": m, "Self-serve": a, "Mid-market": b, "Enterprise": c} for m, a, b, c in zip(MONTHS[3:9], [6.4, 6.2, 6.1, 5.2, 4.6, 4.3], [2.3, 2.4, 2.4, 2.5, 2.6, 2.7], [1.0, 0.9, 0.9, 0.9, 1.0, 0.9])], "month", ["Self-serve", "Mid-market", "Enterprise"], height=200, format="number")
    return ai_shell(0, page("",
                            split(stack(between(row(heading("Q3 churn review", 1), badge("Lumen 4", "ai", icon="sparkles"), gap="sm"), row(btn("Share", "secondary", icon="share"), btn("New chat", "primary", icon="plus"), gap="sm")), card(talk, padding="sm"), gap="md"),
                                  stack(card(trend, title="Monthly churn by segment", subtitle="Percent of accounts"),
                                        card(listing([("churn_by_segment", "Warehouse table · refreshed 02:00", "Used twice", "database", "info"), ("Onboarding launch notes", "Doc · edited 14 Sep by Ana Lima", "1 passage", "file", "brand"), ("Q3 board pack", "PDF · 42 pages", "p.7", "file", "brand")]), title="Sources", subtitle="Everything this answer is grounded in"),
                                        n("Provenance", model="lumen-4", provider="openai", confidence=0.91, note="Numbers copied verbatim from the warehouse; no arithmetic by the model.")), ratio="3:2", gap="lg"),
                            width="wide"))


@screen("ai/agent-run", "AI products", "Agent run inspector", theme="abyss", height=1100,
        caption="An agent run laid bare: every step, tool call and cost, with an approval waiting for a human")
def agent_run(ctx):
    steps = [{"title": "Plan the task", "status": "done", "detail": "Split into 5 steps; estimated 40 seconds and $0.06", "tool": "planner", "duration": "1.2 s"},
             {"title": "Read 42 merged pull requests", "status": "done", "detail": "Skipped 3 dependency bumps", "tool": "github.list_prs", "duration": "4.8 s"},
             {"title": "Draft release notes", "status": "done", "detail": "612 words, grouped by area", "tool": "write", "duration": "9.1 s"},
             {"title": "Translate to German and Japanese", "status": "done", "detail": "Glossary applied: 14 product terms", "tool": "translate", "duration": "7.4 s"},
             {"title": "Publish to the changelog", "status": "running", "detail": "Waiting for approval", "tool": "cms.publish"},
             {"title": "Announce in #releases", "status": "pending", "tool": "slack.post"}]
    return ai_shell(1, page("Release notes for 4.2",
                            between(row(badge("Running", "warning", dot=True), muted("Started by Mira Okafor · 38 seconds ago", "md"), gap="sm"), row(btn("Pause", "secondary", icon="pause"), btn("Stop run", "danger"), gap="sm")),
                            split(stack(card(n("AgentTimeline", steps=steps), title="Steps", subtitle="4 of 6 complete"),
                                        n("Terminal", title="tool call · cms.publish", cursor=False, lines=[{"text": "POST /api/changelog/entries", "kind": "cmd"}, {"text": "{", "kind": "dim"}, {"text": "  \"version\": \"4.2.0\",", "kind": "out"}, {"text": "  \"locales\": [\"en\", \"de\", \"ja\"],", "kind": "out"}, {"text": "  \"publish_at\": \"now\"", "kind": "out"}, {"text": "}", "kind": "dim"}, {"text": "⏸ held: this tool requires approval", "kind": "warn"}])),
                                  stack(n("Approval", title="Publish the 4.2 release notes", summary="Creates a public changelog entry in three languages and notifies 18,400 subscribers by email.", risk="medium", agent="release-notes agent",
                                          details=[{"key": "Audience", "value": "Public · 18,400 subscribers"}, {"key": "Reversible", "value": "Yes, for 30 minutes"}, {"key": "Policy", "value": "Publishing always needs a human"}]),
                                        card(n("KeyValue", columns=2, items=[{"key": "Tokens in", "value": "48,210"}, {"key": "Tokens out", "value": "3,940"}, {"key": "Cost so far", "value": "$0.047"}, {"key": "Budget", "value": "$0.50 per run"}, {"key": "Model", "value": "atlas-large"}, {"key": "Cache hits", "value": "2 of 7 calls"}]),
                                             n("Progress", label="Budget used", value=9.4, tone="success"), title="Cost and limits"),
                                        card(n("Diff", before="Fixed an issue where exports could fail for large workspaces.", after="Exports no longer time out for workspaces with more than 50,000 rows.", title="Edit suggested by the reviewer agent"), title="Review")), ratio="5:4", gap="lg"),
                            subtitle="Agent: release-notes · run r_8f3c2a", width="wide"))


@screen("ai/playground", "AI products", "Prompt playground", theme="neon", height=1080,
        caption="A prompt playground: system and user messages, parameters, a streamed answer and token accounting")
def playground(ctx):
    system = "You are a support assistant for Northbank.\nAnswer in two short paragraphs.\nNever give personalised investment advice.\nIf you cite a fee, quote it exactly from the fee schedule."
    return ai_shell(2, page("Playground",
                            between(row(n("Select", name="model", value="atlas-large", options=["atlas-large", "quill-mini", "ember-code", "auto: cheapest"]), badge("v14 · unsaved changes", "warning"), gap="sm"), row(btn("Compare", "secondary", icon="swap"), btn("Save version", "secondary", icon="save"), btn("Run", "primary", icon="play", kbd="⌘↵"), gap="sm")),
                            split(stack(card(n("TextArea", name="system", label="System", rows=6, value=system), n("TextArea", name="user", label="User", rows=3, value="What does it cost to transfer my ISA to you, and how long does it take?"), title="Messages"),
                                        card(n("Slider", name="temp", label="Temperature", value=0.3, min_=0, max_=2, step=0.1), n("Slider", name="max", label="Maximum tokens", value=400, min_=50, max_=2000, step=50),
                                             grid(n("Toggle", name="json", label="JSON schema output"), n("Toggle", name="tools", label="Allow tools", checked=True), columns=2), title="Parameters")),
                                  stack(card(n("StreamText", text="Transferring an ISA to Northbank is free: we do not charge a transfer fee, and we will refund up to £100 of exit fees charged by your current provider.\n\nMost transfers complete in 7 to 10 working days for cash and up to 30 days for investments. You can start one from the Transfers page; you will not need to contact your old provider.", streaming=True),
                                             row(badge("412 ms to first token", "info", icon="clock"), badge("86 tokens out", "neutral"), badge("$0.0009", "success", icon="dollar"), gap="xs"), title="Response", subtitle="atlas-large · temperature 0.3"),
                                        n("Insight", title="Two guardrails passed, one warning", tone="warning", icon="shield", body="The answer quotes a fee refund. Check it against the current fee schedule before saving this version.", bullets=["No personalised advice detected", "No personal data in the output", "Fee claim: “up to £100” — not found in the attached schedule"]),
                                        card(table([("version", "Version"), ("score", "Eval score", None, "end"), ("cost", "Cost / run", None, "end"), ("latency", "p50", None, "end")], [{"version": "v14 (this run)", "score": "—", "cost": "$0.0009", "latency": "0.9 s"}, {"version": "v13 · live", "score": "94%", "cost": "$0.0011", "latency": "1.1 s"}, {"version": "v12", "score": "91%", "cost": "$0.0012", "latency": "1.2 s"}], dense=True, sortable=False), title="Versions", padding="none")), ratio="1:1", gap="lg"),
                            subtitle="Prompt: support/isa-transfer", width="wide"))


@screen("ai/models", "AI products", "Model comparison", theme="ruby", height=1100,
        caption="Choosing a model with evidence: quality, speed and price side by side, and the same prompt answered three ways")
def models(ctx):
    rows = [{"model": "atlas-large", "quality": 94, "speed": "62 tok/s", "price": "$2.40", "context": "1M", "best": "Reasoning, long documents"}, {"model": "quill-mini", "quality": 86, "speed": "210 tok/s", "price": "$0.35", "context": "200k", "best": "High-volume chat, extraction"},
            {"model": "ember-code", "quality": 91, "speed": "98 tok/s", "price": "$1.10", "context": "400k", "best": "Code and structured output"}, {"model": "onyx-vision", "quality": 88, "speed": "74 tok/s", "price": "$1.90", "context": "128k", "best": "Images, charts, documents"}]
    answer = lambda model, text, ms, cost, tone="neutral": card(text_block(text), row(badge(ms, "info", icon="clock"), badge(cost, "success"), gap="xs"), title=model, tone=tone)  # noqa: E731
    return ai_shell(4, page("Compare models",
                            split(card(n("BarList", items=[{"label": r["model"], "value": r["quality"], "display": "%d%%" % r["quality"], "detail": r["best"]} for r in rows], max_=100), title="Quality on your evaluation set", subtitle="312 graded examples from production"),
                                  card(chart("scatter", [{"price": 2.4, "quality": 94}, {"price": 0.35, "quality": 86}, {"price": 1.1, "quality": 91}, {"price": 1.9, "quality": 88}, {"price": 0.9, "quality": 83}, {"price": 3.2, "quality": 95}], "price", "quality", height=250, format="number"), title="Quality against price", subtitle="US dollars per million tokens; top-left is better"), ratio="1:1"),
                            card(table([("model", "Model"), ("quality", "Quality", "percent", "end"), ("speed", "Speed", None, "end"), ("price", "Price / 1M", None, "end"), ("context", "Context", None, "end"), ("best", "Best for")], rows), title="At a glance", padding="none"),
                            grid(answer("atlas-large", "The clause limits liability to fees paid in the prior 12 months, but carves out data breaches and wilful misconduct, where liability is uncapped.", "2.1 s", "$0.0042", "ai"),
                                 answer("quill-mini", "Liability is capped at 12 months of fees. Some exceptions apply.", "0.4 s", "$0.0003"), answer("ember-code", "Cap: fees in the preceding 12 months. Exceptions: data breach, wilful misconduct (uncapped).", "0.9 s", "$0.0014"), columns=3),
                            n("Insight", title="Use quill-mini for triage and atlas-large for review", tone="ai", body="Routing the 82% of requests that are simple lookups to quill-mini would cut spend by 64% with no measurable drop in graded quality.", bullets=[]),
                            subtitle="Prompt: “Summarise the limitation of liability clause” · same input, three models", width="wide"))


def text_block(content):
    return n("Text", content=content, size="md")


@screen("ai/compose", "AI products", "Generative interface", theme="iris", height=1160,
        caption="Generative UI, live: a sentence becomes a working interface, composed by the kernel and editable afterwards")
def compose(ctx):
    return ai_shell(1, page("Compose an interface",
                            n("PromptBox", value="A weekly sales report with revenue, orders and top products", modes=["Screen", "Form", "Report"], mode="Report", hint="compose.intent · works offline", chips=["An onboarding checklist", "A feedback form with a rating", "A customer table with filters"]),
                            split(n("Generative", intent="A weekly sales report with revenue, orders and top products"),
                                  stack(card(n("Thinking", label="Composing", steps=["Read the intent", "Pick components", "Lay out the hierarchy", "Check contrast and labels"], current=3), title="What the kernel is doing"),
                                        card(listing([("Stat", "“Revenue” and “orders” are headline numbers", "content", "trend-up", "brand"), ("Chart", "“Weekly” implies a trend over time", "data", "chart", "info"), ("Table", "“Top products” is a ranked list of records", "data", "list", "success")], dense=True), title="Why these components", subtitle="Every choice is explained and can be overridden"),
                                        n("Callout", title="The result is ordinary Fluidian", body="Export the scene to any of the 14 SDK languages with one command, then edit it like code you wrote.", tone="ai")), ratio="5:3", gap="lg"),
                            subtitle="Describe a screen. Fluidian composes it from the same components you use by hand.", width="wide"), brand="Fluidian")


@screen("ai/search", "AI products", "Answer engine", theme="deep", height=1160,
        caption="A search experience that answers: a cited summary, the passages behind it and related questions")
def search(ctx):
    hit = lambda t, src, body, k: card(between(strong(t), badge(src, "neutral")), muted(body, "md"), row(badge("Cited as %d" % k, "brand"), muted("Relevance 0.%d" % (97 - k * 4)), gap="sm"), padding="md")  # noqa: E731
    return n("Landing",
             nav("Almanac", ["Search", "Collections", "History"], btn("Sign in", "ghost"), logo="half"),
             n("Band", n("Search", name="q", value="how long can sourdough starter live in the fridge without feeding", kbd="/"),
               split(stack(n("Insight", title="About two to three weeks unfed; months if you revive it patiently", tone="ai", source="4 sources",
                             body="A mature starter slows down at fridge temperature and stays healthy for two to three weeks between feedings. Left longer it turns sour and forms a dark liquid on top, which is harmless: pour it off and feed twice a day for two to three days to bring it back.",
                             bullets=["Feed before chilling, and use a loose lid", "Dark liquid means hungry, not spoiled", "Pink or orange streaks mean discard it"], confidence=0.86),
                           hit("Storing your starter", "Mill & Hearth guide", "“…refrigerated starter can go two to three weeks between feedings. Expect a layer of dark liquid…”", 1),
                           hit("Reviving a neglected starter", "The Proof Journal", "“…even after three months, twice-daily feedings at room temperature restored activity in 72 hours…”", 2),
                           hit("When to throw it away", "Home Fermentation Handbook", "“…pink, orange or fuzzy growth indicates contamination and the culture should be discarded…”", 3), gap="md"),
                     stack(card(n("Suggestions", variant="list", items=[{"label": "How do I revive a starter after a month?", "icon": "search"}, {"label": "Can I freeze sourdough starter?", "icon": "search"}, {"label": "What is the dark liquid on my starter?", "icon": "search"}, {"label": "How often to feed at room temperature?", "icon": "search"}]), title="People also ask"),
                           card(n("Confidence", value=0.86, label="Sources agree"), n("KeyValue", items=[{"key": "Sources read", "value": "12"}, {"key": "Cited", "value": "4"}, {"key": "Conflicts found", "value": "1 · freezing advice differs"}]), title="How sure is this?"),
                           art("dish", hue=45, ratio="16:9", seed=5)), ratio="2:1", gap="xl"),
               pad="sm", align="start"))


@screen("ai/doc-qa", "AI products", "Document question answering", theme="ocean", height=1120,
        caption="Ask a contract: the document on the left, answers on the right with the clause each one came from")
def doc_qa(ctx):
    doc = "## 9. Limitation of liability\n\n**9.1** Neither party is liable for indirect or consequential loss.\n\n**9.2** Subject to clause 9.3, each party's total liability in any contract year is limited to the fees paid in the preceding twelve months.\n\n**9.3** Nothing in this agreement limits liability for (a) death or personal injury caused by negligence, (b) fraud, (c) breach of clause 12 (Data protection), or (d) wilful misconduct.\n\n## 10. Term and termination\n\n**10.1** The initial term is thirty-six months from the effective date.\n\n**10.2** Either party may terminate on ninety days' written notice after the initial term."
    qa = n("Chat", variant="flat", placeholder="Ask about this agreement…", messages=[
        {"from": "me", "text": "What is our maximum exposure if there is a data breach?"},
        {"from": "ai", "rich": True, "text": "**It is uncapped.** Clause 9.2 limits liability to twelve months of fees, but clause 9.3(c) removes that limit for breaches of the data-protection clause.", "citations": ["Clause 9.2", "Clause 9.3(c)", "Clause 12"]},
        {"from": "me", "text": "When is the earliest we can leave?"},
        {"from": "ai", "rich": True, "text": "After the 36-month initial term, with 90 days' written notice: **the earliest exit is 14 June 2028** if notice is served by 16 March 2028.", "citations": ["Clause 10.1", "Clause 10.2"], "chips": ["Draft the notice", "List every deadline", "Compare with our standard terms"]}])
    return ai_shell(3, page("Master services agreement · Arcwell",
                            between(row(badge("PDF · 42 pages", "neutral", icon="file"), badge("Indexed", "success", dot=True), badge("3 risks flagged", "warning", icon="alert"), gap="xs"), row(btn("Summarise", "ai"), btn("Export answers", "secondary", icon="download"), gap="sm")),
                            split(card(n("Markdown", source=doc), n("Callout", title="Highlighted: the passages the answers rely on", body="Clauses 9.2, 9.3(c), 10.1 and 10.2", tone="ai"), title="Document", subtitle="Page 18 of 42"),
                                  stack(card(qa, padding="sm"), card(listing([("Uncapped data-breach liability", "Clause 9.3(c) · unusual for this contract value", "High", "alert", "danger"), ("Auto-renewal for 12 months", "Clause 10.4 · notice window is short", "Medium", "clock", "warning"), ("Governing law: Delaware", "Clause 18 · differs from your standard", "Low", "globe", "info")]), title="Flagged for review")), ratio="1:1", gap="lg"),
                            subtitle="Uploaded by Jonas Weber · 12 November", width="wide"))


@screen("ai/analyst", "AI products", "Data analyst", theme="mint", height=1140,
        caption="Ask your data: a plain-language question becomes a query, a chart and a written finding you can check")
def analyst(ctx):
    data = [{"month": m, "New": a, "Expansion": b, "Churned": -c} for m, a, b, c in zip(MONTHS[:9], [42, 48, 51, 46, 58, 63, 61, 72, 78], [12, 14, 13, 18, 19, 22, 26, 25, 31], [9, 11, 8, 12, 10, 9, 13, 8, 7])]
    sql = "SELECT date_trunc('month', booked_at) AS month,\n       sum(amount) FILTER (WHERE kind = 'new')       AS new,\n       sum(amount) FILTER (WHERE kind = 'expansion') AS expansion,\n       -sum(amount) FILTER (WHERE kind = 'churn')    AS churned\nFROM   revenue_movements\nWHERE  booked_at >= date '2026-01-01'\nGROUP  BY 1 ORDER BY 1;"
    return ai_shell(3, page("Ask your data",
                            n("PromptBox", value="How has net new revenue changed this year, split by new business, expansion and churn?", modes=["Chart", "Table", "Number"], hint="data.query → data.chart_choose → data.narrate", rows=1),
                            split(stack(card(chart("bar", data, "month", ["New", "Expansion", "Churned"], height=280, stacked=True, format="currency"), title="Net new revenue by month", subtitle="$k · bars below zero are churn"),
                                        n("Insight", title="Net new revenue has doubled since January", tone="ai", confidence=0.88, body="It grew from $45k to $102k a month. Expansion is the fastest-growing part, up 158%, while churn fell by a fifth.", bullets=["Largest month: September ($102k net)", "Expansion overtook churn in April and never fell back", "August churn was unusually low: check for a billing delay"])),
                                  stack(card(code(sql, "sql", title="Generated query"), row(badge("Read-only", "success", icon="lock"), badge("Scanned 1.2M rows", "neutral"), badge("0.8 s", "info"), gap="xs"), title="How this was computed", subtitle="Nothing is hidden: run it yourself"),
                                        card(n("Suggestions", variant="list", title="Follow-ups", items=[{"label": "Break expansion down by plan", "icon": "chart"}, {"label": "Which customers churned in March?", "icon": "users"}, {"label": "Forecast the next three months", "icon": "trend-up"}]))), ratio="5:4", gap="lg"),
                            subtitle="Connected to the analytics warehouse · 214 tables", width="wide"), brand="Orbit")


@screen("ai/review", "AI products", "Reviewing AI edits", theme="rose", height=1120,
        caption="Human review of AI changes: each rewrite shown as a diff with its reason, risk and an accept or reject")
def review(ctx):
    edit = lambda title, before, after, reason, risk: card(n("Diff", before=before, after=after, title=title), between(row(badge(risk, {"Low risk": "success", "Check the fact": "warning", "Legal": "danger"}[risk], dot=True), muted(reason), gap="sm"), row(btn("Reject", "ghost", size="sm"), btn("Accept", "primary", size="sm", icon="check"), gap="xs")))  # noqa: E731
    return ai_shell(5, page("Review 6 suggested edits",
                            between(row(n("AvatarStack", names=PEOPLE[:3], label="3 reviewers"), badge("2 accepted", "success"), badge("4 to go", "neutral"), gap="sm"), row(btn("Reject all", "secondary"), btn("Accept low-risk edits", "primary", icon="check"), gap="sm")),
                            split(stack(edit("Tone: plainer", "We regret to inform you that your request cannot be actioned at this time.", "We can't do this yet, and here is why.", "Shorter and more direct; same meaning", "Low risk"),
                                        edit("Clarity", "Refunds are processed within a reasonable timeframe.", "Refunds reach your account within 5 working days.", "Adds a specific commitment: confirm the number", "Check the fact"),
                                        edit("Compliance", "Our product guarantees you will save money.", "Most customers save money; your results depend on usage.", "Removes an absolute claim", "Legal"), gap="md"),
                                  stack(card(n("Rings", size=140, center="6", items=[{"label": "Accepted", "value": 2, "max": 6, "display": "2"}, {"label": "Pending", "value": 4, "max": 6, "display": "4"}]), title="Progress"),
                                        card(n("KeyValue", items=[{"key": "Document", "value": "Help centre · Refunds and cancellations"}, {"key": "Suggested by", "value": "access.plain_language · atlas-large"}, {"key": "Reading level", "value": "Grade 11 → Grade 7"}, {"key": "Words", "value": "1,240 → 1,010"}]), title="This batch"),
                                        n("Callout", title="Nothing is published without a person", body="Accepted edits go to a draft. Publishing needs a second reviewer.", tone="info")), ratio="2:1", gap="lg"),
                            subtitle="Help centre · Refunds and cancellations", width="wide"))


@screen("ai/memory", "AI products", "Memory inspector", theme="grape", height=1100,
        caption="What the assistant remembers and why: facts with their source, confidence and a way to forget")
def memory(ctx):
    facts = [{"fact": "Prefers aisle seats and vegetarian meals", "source": "Chat · 3 Nov", "used": "12 times", "confidence": "High", "status": "Active"}, {"fact": "Works at Arcwell as head of procurement", "source": "Email signature", "used": "31 times", "confidence": "High", "status": "Active"},
             {"fact": "Budget approval limit is $25,000", "source": "Chat · 28 Oct", "used": "4 times", "confidence": "Medium", "status": "Review"}, {"fact": "Based in Bristol, travels to Lisbon monthly", "source": "Calendar", "used": "9 times", "confidence": "High", "status": "Active"},
             {"fact": "Allergic to shellfish", "source": "Chat · 14 Sep", "used": "2 times", "confidence": "High", "status": "Active"}, {"fact": "Manager is Jonas Weber", "source": "Inferred from email threads", "used": "1 time", "confidence": "Low", "status": "Expired"}]
    return ai_shell(3, page("Memory · Amara Nwosu",
                            kpis(("Memories", "214", "+18", "this month", "brain"), ("Retrieved", "1,402", "+12%", "this month", "search", 301), ("Token savings", "81%", "vs full history", "per request", "bolt"), ("Awaiting review", "3", "low confidence", "", "eye")),
                            split(card(table([("fact", "Memory"), ("source", "Learned from"), ("used", "Used", None, "end"), ("confidence", "Confidence", "badge"), ("status", "Status", "badge")], facts), between(muted("Showing 6 of 214"), row(btn("Export", "secondary", size="sm", icon="download"), btn("Forget selected", "danger", size="sm"), gap="xs")), title="What the assistant knows", padding="none"),
                                  stack(card(n("Timeline", items=[{"title": "Updated: travels to Lisbon monthly", "time": "Today", "tone": "ai", "icon": "refresh", "detail": "Was “quarterly”; three trips in the calendar since September"}, {"title": "Added: aisle seats, vegetarian meals", "time": "3 Nov", "tone": "success", "icon": "plus"},
                                                                  {"title": "Expired: manager is Jonas Weber", "time": "1 Nov", "tone": "neutral", "icon": "clock", "detail": "Not confirmed in 90 days"}, {"title": "Forgotten on request: home address", "time": "22 Oct", "tone": "danger", "icon": "trash"}]), title="Recent changes"),
                                        card(n("Toggle", name="learn", label="Learn from conversations", checked=True, help="New facts are proposed, never stored silently"), n("Toggle", name="sensitive", label="Store health and financial details", help="Off by default"), n("Select", name="retention", label="Forget unused memories after", value="90 days", options=["30 days", "90 days", "1 year", "Never"]), title="Controls")), ratio="5:3", gap="lg"),
                            subtitle="Every memory has a source. Anything can be corrected or forgotten.", width="wide"), brand="Mnemo")


@screen("ai/voice", "AI products", "Voice notes to actions", theme="ember", height=1080,
        caption="A recording becomes a summary, decisions and assigned actions, with the transcript one click away")
def voice(ctx):
    transcript = [("Mira Okafor", "00:12", "Right, the main question is whether we ship the checkout redesign before or after the holiday freeze."), ("Jonas Weber", "00:31", "Before, if the payment sheet passes review by Friday. Otherwise it waits until January."),
                  ("Ana Lima", "00:48", "I can finish Apple and Google Pay by Thursday. The accessibility fixes are the risk."), ("Mira Okafor", "01:06", "Then Kenji owns accessibility, due Wednesday, and we decide on Friday morning.")]
    return ai_shell(0, page("Checkout sync · 19 November",
                            split(stack(card(row(btn("", "primary", icon="pause"), stack(n("Waveform", progress=0.42, height=56, seed=11, bars=90), between(muted("06:14"), muted("14:52")), gap="xs"), gap="md", wrap=False, align="center"),
                                             row(badge("4 speakers", "neutral", icon="users"), badge("English", "neutral", icon="globe"), badge("Transcribed on device", "success", icon="lock"), gap="xs"), title="Recording"),
                                        card(n("Thread", messages=[{"author": who, "time": t, "content": said} for who, t, said in transcript]), title="Transcript", subtitle="Tap a line to jump to that moment")),
                                  stack(n("Insight", title="Ship before the freeze if the payment sheet passes review on Friday", tone="ai", confidence=0.9, body="The team agreed on a go or no-go on Friday morning. The open risk is the accessibility fixes.", bullets=["Decision owner: Mira Okafor", "Fallback: ship on 12 January"]),
                                        card(listing([("Finish Apple and Google Pay", "Ana Lima · due Thursday", "01:02", "check-circle", "success"), ("Complete accessibility fixes", "Kenji Sato · due Wednesday", "01:06", "circle", "warning"), ("Go or no-go meeting", "Mira Okafor · Friday 09:30", "01:10", "calendar", "brand")]),
                                             row(btn("Create 3 tasks", "primary", icon="plus"), btn("Send summary", "secondary", icon="send"), gap="sm"), title="Actions", subtitle="Detected from what was said"),
                                        card(n("KeyValue", columns=2, items=[{"key": "Talk time", "value": "Mira 38% · Jonas 27%"}, {"key": "Questions", "value": "7 asked, 6 answered"}, {"key": "Sentiment", "value": "Constructive"}, {"key": "Next meeting", "value": "Friday 09:30"}]), title="Meeting notes")), ratio="1:1", gap="lg"),
                            subtitle="14 minutes · recorded by Mira Okafor", width="wide"))


@screen("ai/router", "AI products", "Routing and guardrails", theme="terminal", height=1100,
        caption="Model governance in the Terminal theme: routing rules, a fallback chain, guardrails and data residency")
def router(ctx):
    rules = [{"when": "task = classify OR tokens < 400", "route": "quill-mini", "share": "61%", "status": "Active"}, {"when": "has_image = true", "route": "onyx-vision", "share": "8%", "status": "Active"}, {"when": "task = code", "route": "ember-code", "share": "14%", "status": "Active"},
             {"when": "contains_pii = true", "route": "atlas-large @ eu-only", "share": "5%", "status": "Active"}, {"when": "default", "route": "atlas-large", "share": "12%", "status": "Active"}]
    return ai_shell(5, page("routing & guardrails",
                            split(stack(card(table([("when", "when"), ("route", "route to"), ("share", "share", None, "end"), ("status", "status", "badge")], rules, dense=True, sortable=False), between(muted("rules are evaluated top to bottom"), btn("add rule", "secondary", size="sm", icon="plus")), title="routing rules", padding="none"),
                                        card(n("Steps", current=1, items=[{"title": "atlas-large", "detail": "primary"}, {"title": "tidal-3", "detail": "if p95 > 4 s"}, {"title": "quill-mini", "detail": "if both fail"}, {"title": "reflex", "detail": "offline answer"}]), muted("214 automatic failovers this week · 0 user-facing errors"), title="fallback chain"),
                                        n("Terminal", title="relay · decision log", cursor=False, lines=[{"text": "15:02:41 route  req_8f3c  rule#1 → quill-mini  (tokens=212)", "kind": "dim"}, {"text": "15:02:41 guard  req_8f3c  redacted 2 emails, 1 phone", "kind": "ok"}, {"text": "15:02:43 route  req_8f3d  rule#4 → atlas-large@eu  (pii)", "kind": "dim"},
                                                                                                         {"text": "15:02:44 guard  req_8f3e  BLOCKED prompt injection (score 0.97)", "kind": "err"}, {"text": "15:02:45 fail   req_8f3f  atlas-large timeout → tidal-3", "kind": "warn"}])),
                                  stack(card(n("Toggle", name="pii", label="redact personal data", checked=True, help="emails, phones, cards, national ids"), n("Toggle", name="inject", label="prompt-injection shield", checked=True, help="blocks instructions hidden in documents"),
                                             n("Toggle", name="mod", label="moderation", checked=True), n("Toggle", name="ground", label="require citations", help="answers without a source are withheld"), title="guardrails"),
                                        card(n("RadioGroup", name="region", value="EU only", options=["Any region", "EU only", "EU and UK", "Custom"]), n("Progress", label="monthly budget · $12,840 of $20,000", value=64), title="residency & budget"),
                                        card(n("Gauge", value=99.2, display="99.2%", label="policy pass rate", detail="38 blocked today", tone="success", size=150), title="today")), ratio="5:3", gap="lg"),
                            subtitle="policy: production · last edited 2 hours ago by idris", width="wide"), brand="relay")


@screen("ai/evals", "AI products", "Evaluation dashboard", theme="lagoon", height=1120,
        caption="Keeping quality honest: pass rates per suite, a regression flagged against the last release and failing examples")
def evals(ctx):
    suites = [{"suite": "Refund policy answers", "cases": 120, "pass": "97%", "delta": "+1", "status": "Passed"}, {"suite": "Tone and empathy", "cases": 80, "pass": "94%", "delta": "0", "status": "Passed"}, {"suite": "Fee accuracy", "cases": 64, "pass": "81%", "delta": "-9", "status": "Failed"},
              {"suite": "Injection resistance", "cases": 150, "pass": "100%", "delta": "0", "status": "Passed"}, {"suite": "Multilingual (de, ja, pt)", "cases": 90, "pass": "92%", "delta": "+3", "status": "Passed"}]
    fails = [{"input": "What does a same-day transfer cost?", "expected": "£15", "got": "£12", "judge": "Wrong fee"}, {"input": "Is there an exit fee on the cash ISA?", "expected": "No", "got": "Up to £100", "judge": "Invented fee"}, {"input": "Overseas card charge?", "expected": "0.5%", "got": "0.5% (correct), plus a £1 fee", "judge": "Added a fee"}]
    return ai_shell(4, page("Evaluations · v14",
                            n("Banner", text="Fee accuracy fell 9 points against v13. This version is blocked from release until it recovers.", tone="danger", icon="alert"),
                            kpis(("Overall pass rate", "93.4%", "-1.6 pts", "vs v13", "target", 311), ("Cases run", "504", "5 suites", "4m 12s", "list"), ("Cost of this run", "$1.84", "-12%", "vs v13", "dollar"), ("Human agreement", "96%", "judge vs people", "last audit", "users")),
                            split(card(chart("line", [{"version": "v%d" % v, "Fee accuracy": a, "Overall": b} for v, a, b in zip(range(7, 15), [84, 86, 88, 89, 91, 90, 90, 81], [90, 91, 92, 93, 94, 94, 95, 93.4])], "version", ["Fee accuracy", "Overall"], height=240, baseline="auto", annotations=[{"x": "v14", "label": "Regression", "tone": "danger"}]), title="Pass rate by version"),
                                  card(table([("suite", "Suite"), ("cases", "Cases", "number", "end"), ("pass", "Pass", None, "end"), ("delta", "Δ", None, "end"), ("status", "Result", "badge")], suites, dense=True), title="Suites", padding="none"), ratio="1:1"),
                            split(card(table([("input", "Input"), ("expected", "Expected"), ("got", "Model said"), ("judge", "Judge")], fails, dense=True, sortable=False), title="Failing examples · fee accuracy", padding="none"),
                                  n("Insight", title="The new system prompt removed the fee schedule", tone="ai", body="v14 dropped the attached schedule to save tokens. Every failure is a fee the model had to guess.", bullets=["Restore the schedule: +310 tokens per request", "Or ground fees with a lookup tool"]), ratio="5:3"),
                            subtitle="Prompt: support/isa-transfer · run 2 minutes ago", width="wide"))
