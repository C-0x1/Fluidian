"""The brand assets: one definition, and every copy of the logo agrees with it."""
import json
import os
import re
import struct
import unittest

import support
from fluidian import colors

ROOT = support.ROOT


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def png_size(*parts):
    with open(os.path.join(ROOT, *parts), "rb") as fh:
        head = fh.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", head[16:24])


class BrandTest(unittest.TestCase):
    def setUp(self):
        self.mark = json.loads(read("runtime", "brand.js").split("=", 1)[1].rstrip().rstrip(";"))

    def test_the_favicon_and_the_documentation_logo_are_the_same_file(self):
        self.assertEqual(read("runtime", "logo.svg"), read("docs", "assets", "logo.svg"))

    def test_every_logo_file_draws_the_same_mark_in_the_brand_colours(self):
        for parts in (("runtime", "logo.svg"), ("docs", "assets", "mark.svg"), ("docs", "assets", "wordmark.svg"),
                      ("docs", "assets", "wordmark-dark.svg"), ("docs", "assets", "banner.svg")):
            svg = read(*parts)
            with self.subTest(file="/".join(parts)):
                self.assertIn('d="%s"' % self.mark["stem"], svg)
                self.assertIn('d="%s"' % self.mark["wave"], svg)
                self.assertIn(colors.BRAND["blue"], svg)
                if parts[-1] != "mark.svg":
                    self.assertIn(colors.BRAND["sky"], svg)

    def test_the_runtime_mark_uses_the_palette_in_the_engine(self):
        self.assertEqual([colour for _, colour in self.mark["tile"]], [colors.BRAND["blue"], colors.BRAND["navy"], colors.BRAND["midnight"]])
        self.assertEqual([colour for _, colour in self.mark["ribbon"]], [colors.BRAND["white"], colors.BRAND["sky"]])

    def test_the_default_theme_is_built_from_the_palette_and_no_other_is(self):
        default = colors.THEMES[colors.DEFAULT_THEME]
        self.assertEqual(default["brand"], colors.BRAND["blue"])
        self.assertEqual(default["accent"], colors.BRAND["sky"])
        tokens = read("runtime", "tokens.css")
        self.assertIn("--fl-ai-a: %s;" % colors.BRAND["blue"], tokens, "runtime/tokens.css is stale: run tools/build_tokens.py")
        seeds = [spec["brand"] for spec in colors.THEMES.values()]
        self.assertEqual(len(set(seeds)), len(seeds), "every preset has a brand colour of its own")

    def test_the_showcase_uses_every_preset_and_leans_on_none(self):
        import subprocess
        import sys
        out = subprocess.run([sys.executable, os.path.join(ROOT, "examples", "showcase", "app.py"), "--list"], stdout=subprocess.PIPE, check=True,
                             env=dict(os.environ, PYTHONPATH=os.path.join(ROOT, "sdks", "python"))).stdout
        used = [screen["theme"] for screen in json.loads(out)]
        self.assertEqual(set(used), set(colors.THEMES), "each preset is shown by at least one screen")
        most = max(used.count(name) for name in set(used))
        self.assertLessEqual(most, len(used) // 10, "no single colour scheme carries more than a tenth of the screens")

    def test_the_wordmarks_are_outlines_and_differ_only_in_ink(self):
        light, dark = read("docs", "assets", "wordmark.svg"), read("docs", "assets", "wordmark-dark.svg")
        for svg in (light, dark):
            self.assertNotIn("<text", svg, "letters are paths, so the file looks the same without the font installed")
            self.assertNotIn("font-family", svg)
        def plain(svg, ink, dot):
            return svg.replace('fill="%s" d=' % colors.BRAND[ink], "X").replace('fill="%s" d=' % colors.BRAND[dot], "Y")
        self.assertEqual(plain(light, "midnight", "blue"), plain(dark, "white", "sky"))

    def test_no_file_still_carries_the_previous_logo(self):
        old_shape, old_colours = "M33 13c8 9", ("#a96ff1", "#00b5e8", "#32ccb0")
        for folder in ("runtime", "docs", "tools", "engine", "examples"):
            for base, _, names in os.walk(os.path.join(ROOT, folder)):
                for name in names:
                    if not name.endswith((".svg", ".js", ".css", ".html", ".py", ".md")):
                        continue
                    text = read(os.path.relpath(os.path.join(base, name), ROOT))
                    if name == "test_brand.py":
                        continue
                    self.assertNotIn(old_shape, text, name)
                    for colour in old_colours:
                        self.assertNotIn(colour, text.lower(), name)

    def test_the_app_icons_have_the_sizes_the_manifest_declares(self):
        self.assertEqual(png_size("runtime", "pwa", "icon-192.png"), (192, 192))
        self.assertEqual(png_size("runtime", "pwa", "icon-512.png"), (512, 512))
        self.assertEqual(png_size("runtime", "pwa", "maskable-512.png"), (512, 512))
        self.assertEqual(png_size("runtime", "pwa", "apple-touch-icon.png"), (180, 180))

    def test_the_banner_states_the_real_counts(self):
        banner = read("docs", "assets", "banner.svg")
        self.assertIn("%d AI capabilities" % len(support.CAPS), banner)
        self.assertIn("%d themes" % len(colors.THEMES), banner)
        components = len(json.loads(read("spec", "components.json"))["components"])
        self.assertIn("%d components" % components, banner)

    def test_the_logo_is_well_formed_and_self_contained(self):
        import xml.dom.minidom
        for name in ("logo.svg", "mark.svg", "wordmark.svg", "wordmark-dark.svg", "banner.svg"):
            svg = read("docs", "assets", name)
            xml.dom.minidom.parseString(svg)
            self.assertIsNone(re.search(r'(href|src)="https?:', svg), name)


if __name__ == "__main__":
    unittest.main()
