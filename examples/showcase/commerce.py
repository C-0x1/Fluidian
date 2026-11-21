"""Storefronts and commerce flows."""
from kit import *  # noqa: F401,F403


def product(name, price, kind, hue, **p):
    return n("ProductCard", name=name, price=price, art={"kind": kind, "hue": hue, "ratio": p.pop("ratio", "4:5"), **p.pop("art", {})}, **p).on("add", "@toast 'Added to bag' success")


OLEA = [("Night Serum", "$64", "bottle", 300, {"rating": 4.9, "reviews": 812, "badge": "Bestseller", "detail": "Retinal + peptides · 30 ml"}),
        ("Cloud Cream", "$48", "jar", 30, {"rating": 4.8, "reviews": 540, "detail": "Ceramide moisturiser · 50 ml"}),
        ("Gentle Cleanser", "$32", "tube", 150, {"rating": 4.7, "reviews": 388, "detail": "Oat milk gel · 120 ml"}),
        ("Ember Candle", "$38", "candle", 55, {"rating": 4.9, "reviews": 204, "badge": "New", "detail": "Amber, fig leaf · 220 g"})]


@screen("store/olea", "Storefronts", "Maison Olea · skincare storefront", theme="sand", height=1700,
        caption="An editorial storefront: serif display type, a split hero and a product grid with procedural product shots")
def olea(ctx):
    return n("Landing",
             nav("Maison Olea", ["Shop", "Rituals", "Ingredients", "Journal", "Stores"], btn("Search", "ghost", icon="search"), btn("Bag · 2", "primary", icon="shopping-bag"), logo="leaf"),
             n("Band", n("PromoTile", row(btn("Shop the ritual", "primary", size="lg"), btn("Take the skin quiz", "secondary", size="lg"), gap="sm"),
                         title="Skin that feels like morning.", highlight="like morning.", eyebrow="The autumn ritual", subtitle="Four formulas, one calm routine. Made in small batches in Porto.",
                         art={"kind": "bottle", "hue": 300, "ratio": "1:1"}, layout="split", size="lg", tone="tint", align="start"), pad="sm", width="wide"),
             n("Band", grid(*[product(nm, pr, kind, hue, **opts) for nm, pr, kind, hue, opts in OLEA], columns=4, gap="lg"),
               title="The essentials", eyebrow="Bestsellers", subtitle="Everything you need and nothing you don't.", pad="sm", width="wide"),
             n("Band", grid(n("Feature", title="Clinically kind", body="Dermatologist tested on sensitive skin, fragrance free where it matters.", icon="heart", variant="plain"),
                            n("Feature", title="Refill, don't replace", body="Every jar and bottle has a refill that uses 80% less packaging.", icon="refresh", variant="plain"),
                            n("Feature", title="Free returns for 60 days", body="Try a full routine. If it isn't right, send it back on us.", icon="truck", variant="plain"), columns=3, gap="lg"), pad="sm", tone="line"),
             n("Band", n("Testimonial", quote="The first routine I have kept for a whole year. My skin has never been calmer.", author="Ines Duarte", role="Verified buyer", company="Lisbon", variant="large", rating=5), pad="sm", tone="soft"),
             footer("Maison Olea", [("Shop", ["Serums", "Moisturisers", "Cleansers", "Sets"]), ("About", ["Our story", "Ingredients", "Sustainability"]), ("Help", ["Shipping", "Returns", "Contact"])],
                    "© 2026 Maison Olea. A fictional brand for demonstration.", logo="leaf", tagline="Quiet skincare, made in small batches."))


def shop_footer(brand, logo, tagline):
    return footer(brand, [("Shop", ["New arrivals", "Bestsellers", "Gift cards"]), ("Help", ["Shipping", "Returns", "Contact"]), ("Company", ["About", "Stores", "Careers"])],
                  "© 2026 %s. A fictional brand for demonstration." % brand, logo=logo, tagline=tagline)


AUDIO = [("Arc Studio", "$349", "headphones", 250, {"rating": 4.8, "reviews": 2140, "badge": "Editor's pick", "detail": "Over-ear · 40 h battery", "swatches": ["#5b6cff", "#111318", "#d9d2c5"]}),
         ("Mono One", "$229", "speaker", 20, {"rating": 4.6, "reviews": 918, "detail": "Bookshelf speaker · Wi-Fi", "swatches": ["#e0633a", "#111318"]}),
         ("Arc Air", "$179", "headphones", 160, {"rating": 4.7, "reviews": 3302, "detail": "On-ear · 28 h battery", "swatches": ["#2fb58a", "#f2efe8"]}),
         ("Mono Mini", "$129", "speaker", 300, {"rating": 4.5, "reviews": 640, "badge": "New", "detail": "Portable · IP67"}),
         ("Arc Studio Pro", "$499", "headphones", 40, {"rating": 4.9, "reviews": 512, "detail": "Planar drivers · wired + wireless"}),
         ("Mono Tower", "$899", "speaker", 215, {"rating": 4.8, "reviews": 201, "compareAt": "$999", "detail": "Floor-standing pair"})]


@screen("store/kordo", "Storefronts", "Kordo · category listing", theme="neon", height=1280,
        caption="A dark category page: filters, sort controls and a product grid with colour swatches")
def kordo(ctx):
    filters = card(n("Search", name="q", placeholder="Search audio"),
                   n("RadioGroup", name="type", label="Category", value="All audio", options=["All audio", "Headphones", "Speakers", "Turntables"]),
                   n("Slider", name="price", label="Max price", value=600, min_=50, max_=1000, unit="USD"),
                   n("Swatches", name="colour", label="Colour", options=[{"label": "Cobalt", "color": "#5b6cff"}, {"label": "Ink", "color": "#111318"}, {"label": "Bone", "color": "#d9d2c5"}, {"label": "Ember", "color": "#e0633a"}, {"label": "Moss", "color": "#2fb58a"}]),
                   n("Checkbox", name="stock", label="In stock only", checked=True), n("Checkbox", name="sale", label="On sale"), title="Filters")
    return n("Landing",
             nav("Kordo", ["Headphones", "Speakers", "Turntables", "Accessories", "Sale"], btn("Search", "ghost", icon="search"), btn("Cart · 1", "primary", icon="cart"), logo="dot"),
             n("Band", n("Breadcrumbs", items=[{"label": "Home", "route": "#"}, {"label": "Audio", "route": "#"}, {"label": "All audio"}]),
               between(stack(heading("All audio", 1), muted("24 products · free shipping over $100", "md"), gap="xs"),
                       row(n("Segmented", name="view", value="Grid", options=["Grid", "List"]), n("Select", name="sort", value="Most popular", options=["Most popular", "Price: low to high", "Newest"]), gap="sm")),
               split(filters, grid(*[product(nm, pr, kind, hue, ratio="1:1", art={"tone": "dark"}, brand="Kordo", **opts) for nm, pr, kind, hue, opts in AUDIO], columns=3, gap="md"), ratio="1:3", gap="lg"),
               pad="sm", width="wide", align="start"))


@screen("store/product", "Storefronts", "Kordo · product page", theme="emerald", height=1500,
        caption="A product detail page with a media gallery, variant pickers and a review summary written by the AI kernel")
def product_page(ctx):
    gallery = n("MediaGallery", layout="side", items=[{"kind": "headphones", "hue": 250, "ratio": "1:1"}, {"kind": "headphones", "hue": 250, "ratio": "1:1", "tone": "dark"}, {"kind": "waves", "hue": 250, "ratio": "1:1"}, {"kind": "rings", "hue": 250, "ratio": "1:1"}])
    buy = stack(n("Breadcrumbs", items=[{"label": "Audio", "route": "#"}, {"label": "Headphones", "route": "#"}, {"label": "Arc Studio"}]),
                stack(muted("KORDO", "xs"), heading("Arc Studio wireless headphones", 1), row(n("RatingSummary", average=4.8, count=2140, distribution=[1720, 300, 80, 25, 15]), gap="sm"), gap="xs"),
                row(strong("$349", "xl"), badge("Free 2-day shipping", "success", icon="truck"), badge("In stock", "neutral", dot=True), gap="sm"),
                n("Swatches", name="colour", label="Colour", value="Cobalt", options=[{"label": "Cobalt", "color": "#5b6cff"}, {"label": "Ink", "color": "#111318"}, {"label": "Bone", "color": "#d9d2c5"}]),
                n("Swatches", name="plan", label="Protection", value="None", options=["None", "2 years · $29", "3 years · $39"]),
                row(n("Quantity", name="qty", value=1), btn("Add to cart", "primary", size="lg", icon="cart"), btn("Save", "secondary", size="lg", icon="heart"), gap="sm", align="end"),
                n("Insight", title="What 2,140 reviewers agree on", tone="ai", body="Comfortable for long sessions and the noise cancelling holds up on flights. A few buyers found the case bulky.",
                  bullets=["Battery: most report 38–42 hours", "Fit: glasses wearers rate comfort 4.7", "Calls: microphone praised in 81% of mentions"]),
                gap="lg")
    return n("Landing",
             nav("Kordo", ["Headphones", "Speakers", "Turntables", "Accessories", "Sale"], btn("Search", "ghost", icon="search"), btn("Cart · 1", "primary", icon="cart"), logo="dot"),
             n("Band", split(gallery, buy, ratio="11:9", gap="xl"), pad="sm", width="wide", align="start"),
             n("Band", grid(card(n("KeyValue", columns=2, items=[{"key": "Drivers", "value": "40 mm beryllium"}, {"key": "Battery", "value": "40 hours"}, {"key": "Weight", "value": "254 g"}, {"key": "Codecs", "value": "AAC, aptX, LC3"},
                                                                {"key": "Charging", "value": "USB-C · 5 min = 4 h"}, {"key": "Warranty", "value": "2 years"}]), title="Specifications"),
                            n("Testimonial", quote="Wore them from London to Singapore. Forgot they were on.", author="Kenji Sato", role="Verified buyer", rating=5),
                            n("Testimonial", quote="The transparency mode sounds natural, which is rarer than it should be.", author="Sofia Marin", role="Verified buyer", rating=5), columns=3, gap="lg"), pad="sm", width="wide", tone="line"))


CART = [{"name": "Night Serum", "variant": "30 ml · Retinal + peptides", "price": "$64.00", "qty": 1, "art": {"kind": "bottle", "hue": 300}},
        {"name": "Cloud Cream", "variant": "50 ml · Refill pouch", "price": "$76.00", "qty": 2, "art": {"kind": "jar", "hue": 30}},
        {"name": "Ember Candle", "variant": "220 g · Amber, fig leaf", "price": "$38.00", "qty": 1, "art": {"kind": "candle", "hue": 55}}]


@screen("store/cart", "Storefronts", "Maison Olea · cart", theme="rose", height=1180,
        caption="A cart in the Rose theme: line items with steppers, an order summary and recommendations")
def cart(ctx):
    summary = card(n("OrderSummary", n("Input", name="code", placeholder="Gift card or promo code", suffix="Apply"), btn("Checkout · $169.20", "primary", size="lg", block=True),
                     row(n("Icon", name="lock", size=14), muted("Secure checkout · 60-day returns"), gap="xs", justify="center"),
                     title="Order summary", lines=[{"label": "Subtotal", "value": "$178.00"}, {"label": "Autumn ritual discount", "value": "−$17.80", "tone": "success"}, {"label": "Shipping", "value": "Free", "tone": "success"}, {"label": "Estimated tax", "value": "$9.00"}], total="$169.20"),
                   elevated=True)
    return n("Landing",
             nav("Maison Olea", ["Shop", "Rituals", "Ingredients", "Journal"], btn("Account", "ghost", icon="user"), btn("Bag · 4", "primary", icon="shopping-bag"), logo="leaf"),
             n("Band", n("Steps", current=0, items=[{"title": "Bag"}, {"title": "Details"}, {"title": "Payment"}, {"title": "Done"}]),
               split(stack(between(heading("Your bag", 1), muted("4 items", "md")), n("Banner", text="You have unlocked free shipping and a sample of Morning Mist.", tone="success", icon="gift"), card(n("Cart", items=CART))),
                     summary, ratio="5:3", gap="xl"),
               pad="sm", width="default", align="start"),
             n("Band", grid(*[product(nm, pr, kind, hue, ratio="1:1", **opts) for nm, pr, kind, hue, opts in [("Morning Mist", "$28", "bottle", 190, {"detail": "Hydrating toner"}), ("Lip Balm", "$14", "tube", 10, {"detail": "Shea + vanilla"}),
                                                                                                           ("Hand Cream", "$22", "tube", 60, {"detail": "Neroli"}), ("Travel Set", "$58", "box", 320, {"detail": "Four minis", "badge": "Gift"})]], columns=4, gap="md"),
               title="Pairs well with", align="start", pad="sm", tone="line"))


@screen("store/checkout", "Storefronts", "Maison Olea · checkout", theme="ocean", height=1300,
        caption="A checkout with smart paste: one pasted address fills the form, and totals stay in view")
def checkout(ctx):
    form = n("Form",
             card(grid(field("Email", "email", "ines.duarte@example.com", kind="email"), field("Phone", "phone", "+351 912 345 678"), columns=2), title="Contact", eyebrow="Step 1"),
             card(grid(field("First name", "first", "Ines"), field("Last name", "last", "Duarte"), columns=2), field("Address", "address", "Rua das Flores 28, 3º Esq"),
                  grid(field("City", "city", "Porto"), field("Postcode", "postcode", "4050-262"), n("Select", name="country", label="Country", value="Portugal", options=["Portugal", "Spain", "France", "Germany"]), columns=3),
                  n("Callout", title="Filled from your clipboard", body="We read the address you pasted and split it into fields. Check it before you continue.", tone="ai"), title="Delivery", eyebrow="Step 2"),
             card(n("RadioGroup", name="shipping", layout="cards", value="Standard", options=[{"label": "Standard", "value": "Standard", "detail": "3–5 days · Free"}, {"label": "Express", "value": "Express", "detail": "Next day · $9"}, {"label": "Pick-up point", "value": "Pickup", "detail": "2 days · Free"}]), title="Shipping", eyebrow="Step 3"),
             card(split(stack(field("Card number", "card", "4242 4242 4242 4242", icon="card"), grid(field("Expiry", "exp", "08 / 29"), field("Security code", "cvc", "•••"), columns=2), n("Checkbox", name="save", label="Save this card for next time", checked=True)),
                        art("card", hue=215, hue2=170, ratio="16:9", label="4242"), ratio="3:2"), title="Payment", eyebrow="Step 4"), name="checkout")
    summary = card(n("Cart", items=CART[:2]), n("OrderSummary", btn("Pay $149.00", "primary", size="lg", block=True), lines=[{"label": "Subtotal", "value": "$140.00"}, {"label": "Shipping", "value": "Free", "tone": "success"}, {"label": "Tax", "value": "$9.00"}], total="$149.00",
                                                note="By paying you agree to the terms of sale."), title="Your order")
    return n("Landing",
             nav("Maison Olea", [], row(n("Icon", name="lock", size=15), muted("Secure checkout", "md"), gap="xs"), logo="leaf"),
             n("Band", n("Steps", current=2, items=[{"title": "Bag"}, {"title": "Details"}, {"title": "Payment"}, {"title": "Done"}]), split(form, summary, ratio="5:3", gap="xl"), pad="sm", align="start"))


@screen("store/order", "Storefronts", "Order tracking", theme="mint", height=1120,
        caption="Order confirmation with live tracking: a route on the generated city map and a delivery timeline")
def order(ctx):
    track = n("Timeline", items=[{"title": "Order placed", "time": "Mon 09:14", "tone": "success", "icon": "check"}, {"title": "Packed in Porto", "time": "Mon 15:40", "tone": "success", "icon": "check"},
                                 {"title": "Out for delivery", "time": "Today 08:02", "tone": "brand", "icon": "truck", "detail": "Tomás is 6 stops away"}, {"title": "Delivered", "time": "Expected 11:30 – 12:00"}])
    route = n("MapView", kind="city", height=420, seed=7, routes=[{"points": [[12, 78], [28, 70], [38, 52], [55, 46], [63, 30], [80, 24]]}],
              pins=[{"x": 12, "y": 78, "label": "Depot", "tone": "neutral"}, {"x": 55, "y": 46, "label": "Courier · 12 min", "tone": "brand", "pulse": True, "size": 8}, {"x": 80, "y": 24, "label": "Your address", "tone": "success"}])
    return n("Landing",
             nav("Maison Olea", ["Shop", "Rituals", "Journal"], btn("Account", "ghost", icon="user"), logo="leaf"),
             n("Band", row(n("Icon", name="check-circle", size=40, tone="success"), stack(heading("Thank you, Ines. Your order is on its way.", 1), muted("Order MO-48213 · a confirmation was sent to ines.duarte@example.com", "md"), gap="xs"), gap="md", wrap=False),
               split(stack(card(route, padding="none"), card(n("Cart", items=CART[:2]), title="In this delivery")),
                     stack(card(track, title="Arriving today", subtitle="Between 11:30 and 12:00"),
                           card(n("KeyValue", items=[{"key": "Deliver to", "value": "Ines Duarte, Rua das Flores 28, Porto"}, {"key": "Courier", "value": "Tomás Rey · electric van"}, {"key": "Instructions", "value": "Leave with the neighbour at 26"}]),
                                row(btn("Change delivery", "secondary"), btn("Message courier", "secondary", icon="message"), gap="sm"), title="Delivery details"),
                           n("Callout", title="Need it later?", body="Reschedule for free until the courier is two stops away.", tone="info")), ratio="5:3", gap="lg"),
               pad="sm", width="wide", align="start"))


PLANTS = [("Monstera Deliciosa", "$42", 15, 3, {"detail": "Bright, indirect light", "badge": "Easy care"}), ("Fiddle Leaf Fig", "$68", 200, 5, {"detail": "Loves a sunny corner"}),
          ("Snake Plant", "$29", 40, 8, {"detail": "Thrives on neglect", "badge": "Pet safe"}), ("Bird of Paradise", "$95", 330, 2, {"detail": "Statement height: 150 cm"}),
          ("Olive Tree", "$74", 90, 6, {"detail": "Indoor or balcony"}), ("Rubber Plant", "$38", 265, 9, {"detail": "Glossy and forgiving"}),
          ("Calathea Orbifolia", "$46", 170, 4, {"detail": "Prefers humidity"}), ("ZZ Plant", "$34", 0, 7, {"detail": "Low light champion", "badge": "Bestseller"})]


@screen("store/fern", "Storefronts", "Fern & Co · plant shop", theme="moss", height=1560,
        caption="A plant shop in the Moss theme: lime on deep green, with every plant drawn from a seed")
def fern(ctx):
    return n("Landing",
             nav("Fern & Co", ["Plants", "Pots", "Care", "Gifts", "Workshops"], btn("Search", "ghost", icon="search"), btn("Basket", "primary", icon="shopping-bag"), logo="leaf", variant="pill"),
             n("Band", split(n("Hero", row(btn("Shop plants", "primary", size="lg"), btn("Find my plant", "secondary", size="lg", icon="sparkles"), gap="sm"),
                               row(badge("Delivered potted", "success", icon="check"), badge("30-day plant guarantee", "neutral", icon="shield"), gap="xs"),
                               title="Bring the outside in.", highlight="outside in.", size="xl", tone="none", eyebrow="Grown in Aalsmeer · delivered in 48 hours",
                               subtitle="Healthy, well-rooted houseplants with a care plan that reminds you when to water."),
                             art("plant", hue=25, ratio="1:1", seed=3, tone="dark"), ratio="1:1", gap="xl"), pad="sm", width="wide"),
             n("Band", row(*[n("Button", label=c, variant="secondary" if i else "primary") for i, c in enumerate(["All plants", "Low light", "Pet safe", "Statement", "Hanging", "Air purifying", "Gift sets"])], gap="xs"),
               grid(*[n("ProductCard", name=nm, price=pr, art={"kind": "plant", "hue": hue, "seed": seed, "ratio": "4:5", "tone": "dark"}, rating=4.8, **opts).on("add", "@toast 'Added to basket' success") for nm, pr, hue, seed, opts in PLANTS], columns=4, gap="md"),
               title="Fresh this week", eyebrow="Shop", align="start", pad="sm", width="wide"),
             shop_footer("Fern & Co", "leaf", "Plants for people who forget to water."), backdrop="glow")


@screen("store/glyph", "Storefronts", "Glyph Market · digital goods", theme="candy", height=1320,
        caption="A marketplace for fonts and templates: type specimens and interface thumbnails generated on the fly")
def glyph(ctx):
    fonts = [("Soleil Grotesk", "12 styles", "$49", {"label": "Ag", "hue": 280}), ("Marlowe Serif", "8 styles", "$65", {"label": "Rr", "hue": 20, "variant": "serif"}), ("Kiln Mono", "6 styles", "$39", {"label": "{}", "hue": 150, "variant": "mono"}),
             ("Aster Display", "4 styles", "$29", {"label": "Qa", "hue": 330}), ("Tidewater", "10 styles", "$55", {"label": "Ty", "hue": 200, "variant": "serif"}), ("Pixel Sans", "3 styles", "Free", {"label": "px", "hue": 60, "variant": "mono"})]
    kits = [("Orbit dashboard kit", "240 components", "$89", "dashboard", 2), ("Launchpad landing kit", "36 sections", "$59", "landing", 5), ("Pocket mobile kit", "120 screens", "$79", "mobile", 7)]
    return n("Landing",
             nav("Glyph Market", ["Fonts", "UI kits", "Icons", "Illustrations", "Sell"], btn("Sign in", "ghost"), btn("Cart", "primary", icon="cart"), logo="slash"),
             n("Band", between(stack(heading("Type and templates from independent makers", 1), muted("12,400 products · instant download · one simple licence", "md"), gap="xs"), n("Search", name="q", placeholder="Search 12,400 products", kbd="/")),
               row(*[n("Button", label=c, variant="primary" if not i else "secondary", size="sm") for i, c in enumerate(["Trending", "New", "Free", "Variable fonts", "Dark mode kits", "Under $30"])], gap="xs"),
               grid(*[card(art("poster", ratio="4:3", **spec), between(stack(strong(name), muted(detail), gap="none"), badge(price, "success" if price == "Free" else "brand")), padding="sm") for name, detail, price, spec in fonts], columns=3, gap="md"),
               pad="sm", width="wide", align="start"),
             n("Band", grid(*[card(art("ui", variant=v, seed=s, ratio="16:9"), between(stack(strong(name), muted(detail), gap="none"), btn(price, "secondary", size="sm")), padding="sm") for name, detail, price, v, s in kits], columns=3, gap="md"),
               title="Interface kits", eyebrow="Staff picks", align="start", pad="sm", width="wide", tone="soft"))


@screen("store/tempo", "Storefronts", "Tempo · watches", theme="gold", height=1640,
        caption="A luxury product page: gold on black, serif headlines and a generated watch as the centrepiece")
def tempo(ctx):
    models = [("Meridian 38", "Steel, midnight dial", "$1,450", 220), ("Solstice 40", "Rose gold, ivory dial", "$3,200", 45), ("Fathom 42", "Titanium, deep green", "$2,150", 160), ("Nocturne 36", "Black ceramic", "$2,800", 280)]
    return n("Landing",
             nav("Tempo", ["Collections", "Craft", "Stores", "Service"], btn("Book a viewing", "primary"), logo="ring"),
             n("Band", n("PromoTile", row(btn("Discover the Solstice", "primary", size="lg"), btn("Find a boutique", "secondary", size="lg"), gap="sm"), title="Time, made by hand.", highlight="made by hand.", eyebrow="The Solstice collection",
                         subtitle="Assembled by eleven watchmakers in Le Locle. Four hundred pieces a year.", art={"kind": "watch", "hue": 45, "ratio": "21:9", "bare": True, "tone": "dark"}, tone="dark", size="xl"), pad="sm", width="wide"),
             n("Band", grid(*[n("ProductCard", name=nm, price=pr, detail=d, variant="plain", art={"kind": "watch", "hue": hue, "ratio": "4:5", "tone": "dark"}) for nm, d, pr, hue in models], columns=4, gap="lg"), title="The collection", eyebrow="Automatic", pad="sm", width="wide"),
             n("Band", n("Metrics", variant="divided", items=[{"value": "72 h", "label": "power reserve"}, {"value": "284", "label": "hand-finished parts"}, {"value": "10 yr", "label": "warranty"}, {"value": "1987", "label": "founded in Le Locle"}]), pad="sm", tone="line"),
             n("Band", n("Testimonial", quote="A watch should be the quietest object you own and the one you would save first.", author="Sofia Marin", role="Master watchmaker", company="Tempo", variant="large"), pad="sm"),
             shop_footer("Tempo", "ring", "Independent watchmaking since 1987."))


PRODUCE = [("Navel oranges", "$3.20 / kg", "round", 55), ("Amalfi lemons", "$4.10 / kg", "oval", 100), ("Pink Lady apples", "$3.60 / kg", "round", 20), ("Hass avocados", "$1.40 each", "pear", 135),
           ("Black plums", "$5.20 / kg", "round", 330), ("Blueberries", "$3.90 / punnet", "round", 265), ("Limes", "$0.50 each", "oval", 135), ("Conference pears", "$3.10 / kg", "pear", 105)]


@screen("store/crate", "Storefronts", "Crate · grocery delivery", theme="tangerine", height=1240,
        caption="Grocery delivery in the Tangerine theme: produce drawn as artwork, quick-add buttons and a live basket")
def crate(ctx):
    basket = card(n("Cart", items=[{"name": "Navel oranges", "variant": "1 kg", "price": "$3.20", "qty": 1, "art": {"kind": "fruit", "hue": 55}}, {"name": "Hass avocados", "variant": "each", "price": "$4.20", "qty": 3, "art": {"kind": "fruit", "hue": 135, "variant": "pear"}},
                                   {"name": "Blueberries", "variant": "punnet", "price": "$7.80", "qty": 2, "art": {"kind": "fruit", "hue": 265}}]),
                  n("Progress", label="$4.80 more for free delivery", value=76, tone="success"),
                  n("OrderSummary", btn("Checkout", "primary", size="lg", block=True), lines=[{"label": "Subtotal", "value": "$15.20"}, {"label": "Delivery · today 18:00–19:00", "value": "$2.50"}], total="$17.70"), title="Your basket", subtitle="Arrives in 42 minutes")
    return n("Landing",
             nav("Crate", ["Produce", "Bakery", "Dairy", "Pantry", "Recipes"], n("Search", name="q", placeholder="Search 4,000 products"), btn("Account", "ghost", icon="user"), logo="drop"),
             n("Band", split(stack(n("PromoTile", row(btn("Shop the box", "primary"), gap="sm"), title="The autumn box is here", subtitle="Twelve seasonal picks from farms within 80 km.", eyebrow="This week", art={"kind": "fruit", "hue": 55, "ratio": "21:9", "bare": True}, layout="split", size="sm", tone="tint", align="start"),
                                   row(*[n("Button", label=c, variant="primary" if not i else "secondary", size="sm") for i, c in enumerate(["Fruit", "Vegetables", "Herbs", "Organic", "On offer", "Local"])], gap="xs"),
                                   grid(*[n("ProductCard", name=nm, price=pr, art={"kind": "fruit", "hue": hue, "variant": v, "ratio": "1:1"}).on("add", "@toast 'Added to basket' success") for nm, pr, v, hue in PRODUCE], columns=4, gap="md")),
                             basket, ratio="5:2", gap="lg"), pad="sm", width="wide", align="start"))


@screen("store/admin", "Storefronts", "Merchant admin", theme="deep", height=1180,
        caption="The merchant side: revenue, orders and stock alerts, with an AI briefing on what needs attention")
def admin(ctx):
    orders = [{"order": "#48213", "customer": "Ines Duarte", "items": 3, "total": 169.20, "status": "Paid", "channel": "Web"}, {"order": "#48212", "customer": "Kenji Sato", "items": 1, "total": 64.00, "status": "Pending", "channel": "App"},
              {"order": "#48211", "customer": "Sofia Marin", "items": 5, "total": 242.50, "status": "Paid", "channel": "Web"}, {"order": "#48210", "customer": "Omar Haddad", "items": 2, "total": 96.00, "status": "Refunded", "channel": "Store"},
              {"order": "#48209", "customer": "Lena Fischer", "items": 4, "total": 188.00, "status": "Paid", "channel": "App"}, {"order": "#48208", "customer": "Idris Bello", "items": 1, "total": 38.00, "status": "Failed", "channel": "Web"}]
    return shell("Maison Olea", [("Home", "home", "Store"), ("Orders", "inbox", "Store", "12"), ("Products", "tag", "Store"), ("Customers", "users", "Store"), ("Analytics", "chart", "Grow"), ("Marketing", "send", "Grow"), ("Discounts", "percent", "Grow"), ("Settings", "settings", "Admin")],
                 page("Today at a glance",
                      kpis(("Sales", "$18,420", "+14.2%", "vs last Thursday", "dollar", 81), ("Orders", "212", "+9.6%", "vs last Thursday", "inbox", 82), ("Conversion", "3.84%", "+0.4 pts", "sessions to orders", "target", 83), ("Average order", "$86.90", "+$3.10", "this week", "tag", 84)),
                      split(card(chart("bar", [{"hour": "%02d:00" % h, "web": a, "app": b} for h, a, b in zip(range(8, 20), series(85, 12, 600, 40, 160, 200), series(86, 12, 300, 30, 120, 100))], "hour", ["web", "app"], height=260, stacked=True), title="Sales by hour", subtitle="Web and app, today"),
                            stack(n("Insight", title="Three things need you today", tone="ai", body="Night Serum will sell out by Saturday at the current rate.", bullets=["Reorder 400 units of Night Serum (lead time 9 days)", "12 orders are waiting for a shipping label", "Refund rate on Cloud Cream doubled this week"]),
                                  card(n("BarList", format="currency", items=[{"label": "Night Serum", "value": 6240, "detail": "97 sold"}, {"label": "Cloud Cream", "value": 4180, "detail": "88 sold"}, {"label": "Ember Candle", "value": 2290, "detail": "60 sold"}]), title="Top products")), ratio="5:3"),
                      card(table([("order", "Order"), ("customer", "Customer"), ("channel", "Channel"), ("items", "Items", "number", "end"), ("total", "Total", "currency", "end"), ("status", "Status", "badge")], orders), title="Recent orders", padding="none"),
                      subtitle="Thursday 19 November · store is open", width="wide"),
                 user={"name": "Ines Duarte", "role": "Owner"}, tagline="Admin")


@screen("store/lookbook", "Storefronts", "Casa Verano · lookbook", theme="forest", height=1700,
        caption="An editorial homeware lookbook in the Forest theme: overlay tiles, serif type and warm product shots")
def lookbook(ctx):
    goods = [("Stoneware mug", "$24", "mug", 25), ("Linen tote", "$38", "bag", 95), ("Bud vase", "$46", "vase", 200), ("Reading lamp", "$120", "lamp", 60)]
    return n("Landing",
             nav("Casa Verano", ["Living", "Kitchen", "Bedroom", "Garden", "Journal"], btn("Search", "ghost", icon="search"), btn("Basket", "primary", icon="shopping-bag"), logo="arc"),
             n("Band", n("PromoTile", row(btn("Shop the collection", "primary", size="lg"), gap="sm"), title="Slow mornings, warm light.", highlight="warm light.", eyebrow="Autumn collection", subtitle="Stoneware, linen and oak for rooms that take their time.",
                         art={"kind": "dunes", "hue": 40, "hue2": 20, "ratio": "21:9"}, layout="overlay", size="lg"),
               grid(n("PromoTile", row(btn("Shop kitchen", "secondary"), gap="sm"), title="The table", subtitle="Hand-thrown in Alentejo.", art={"kind": "mug", "hue": 25, "ratio": "16:9", "bare": True}, tone="tint", size="sm"),
                    n("PromoTile", row(btn("Shop living", "secondary"), gap="sm"), title="The corner", subtitle="Light for long evenings.", art={"kind": "lamp", "hue": 60, "ratio": "16:9", "bare": True}, size="sm"), columns=2, gap="md"), pad="sm", width="wide"),
             n("Band", grid(*[product(nm, pr, kind, hue, ratio="1:1", variant="plain") for nm, pr, kind, hue in goods], columns=4, gap="lg"), title="Objects for every day", eyebrow="New in", pad="sm", width="wide"),
             n("Band", split(art("forest", hue=140, ratio="4:3"), stack(n("Heading", text="Made by eleven workshops, all within a day's drive.", level=2, eyebrow="Our makers"),
                                                                        muted("We publish who made every object, what they were paid and how far it travelled. Nothing in this collection crossed an ocean.", "lg"), btn("Meet the makers", "secondary"), gap="md"), ratio="1:1", gap="xl"), pad="sm", tone="soft"),
             shop_footer("Casa Verano", "arc", "Homeware with a short journey."))
