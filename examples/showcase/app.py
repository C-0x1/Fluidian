"""Fluidian Showcase.

Eighty-five complete screens — landing pages, storefronts, dashboards, AI products,
mobile apps and application modules — each built from Fluidian components in a few
dozen lines of Python.  Start it with ``./fluidian showcase`` and open the printed URL.

Every brand, person and figure in these screens is fictional.
"""
from fluidian import App

from kit import SCREENS, badge, btn, card, grid, muted, n, row, stack, text
import landing  # noqa: F401  (each module registers its screens)
import commerce  # noqa: F401
import dashboards  # noqa: F401
import ai_products  # noqa: F401
import mobile  # noqa: F401
import modules  # noqa: F401

app = App("Fluidian Showcase")
ART = {"Landing pages": "mesh", "Storefronts": "orbs", "Dashboards": "waves", "AI products": "rings", "Mobile and cross-platform": "blocks", "Application modules": "topo"}


def index(ctx):
    groups = []
    for name in dict.fromkeys(s["group"] for s in SCREENS):
        members = [s for s in SCREENS if s["group"] == name]
        cards = [n("Feature", row(badge(s["theme"], "brand"), gap="xs"), title=s["title"], body=s["caption"], variant="card", link="Open").on("click", "open", {"route": s["route"]}).id("open-" + s["slug"])
                 for s in members]
        groups.append(n("Band", grid(*cards, columns=3), title=name, eyebrow="%d screens" % len(members), align="start", pad="sm"))
    return n("Landing",
             n("NavBar", btn("Documentation", "ghost"), brand="Fluidian", tag="Showcase", logo="fluidian"),
             n("Band", n("Hero", title="%d screens, one component library" % len(SCREENS), highlight="one component library", size="lg", align="center", tone="none",
                         subtitle="Landing pages, storefronts, dashboards, AI products and mobile apps. Each one is a short Python function; every brand and figure is fictional."), pad="sm"),
             *groups, backdrop="glow")


@app.view
def view(ctx):
    route = (ctx.route or "/").split("?")[0].rstrip("/") or "/"
    entry = next((s for s in SCREENS if s["route"] == route), None)
    if entry is None:
        return n("Theme", index(ctx), preset="deep").id("root")
    return n("Theme", entry["build"](ctx), preset=entry["theme"]).id("root")


@app.on("open")
def open_screen(ctx, event):
    ctx.navigate(event.payload["route"])


if __name__ == "__main__":
    import sys
    if "--list" in sys.argv:  # used by tools/screenshots.py and the documentation generator
        import json
        json.dump([{k: v for k, v in s.items() if k != "build"} for s in SCREENS], sys.stdout, indent=1)
    else:
        app.run()
