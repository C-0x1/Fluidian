import unittest

import support  # noqa: F401
from fluidian import colors as K


class ColourTest(unittest.TestCase):
    def test_contrast_extremes(self):
        self.assertAlmostEqual(K.contrast("#000000", "#ffffff"), 21.0, places=1)
        self.assertAlmostEqual(K.contrast("#777777", "#777777"), 1.0, places=2)

    def test_hex_parsing(self):
        self.assertEqual(K.parse_hex("#fff"), K.parse_hex("#ffffff"))
        self.assertTrue(K.is_hex("#2a6df4"))
        self.assertFalse(K.is_hex("blue"))
        self.assertEqual(K.to_hex(K.parse_hex("#2a6df4")), "#2a6df4")

    def test_oklch_round_trip(self):
        for colour in ("#2a6df4", "#e11d48", "#16a34a", "#f59e0b", "#111827"):
            back = K.oklch(*K.rgb_to_oklch(K.parse_hex(colour)))
            self.assertLess(max(abs(a - b) for a, b in zip(K.parse_hex(colour), K.parse_hex(back))), 3 / 255 + 1e-9, colour)

    def test_heal_contrast_reaches_the_target(self):
        for fg, bg in (("#9db8ff", "#ffffff"), ("#b8bcc4", "#f6f7f9"), ("#334155", "#0b1220")):
            fixed, ratio, _ = K.heal_contrast(fg, bg, 4.5)
            self.assertGreaterEqual(K.contrast(fixed, bg), 4.5, (fg, bg))
            self.assertAlmostEqual(ratio, K.contrast(fixed, bg), places=1)

    def test_heal_contrast_keeps_passing_pairs(self):
        fixed, _, steps = K.heal_contrast("#111827", "#ffffff", 4.5)
        self.assertEqual((fixed, steps), ("#111827", 0))

    def test_ramp_runs_light_to_dark(self):
        ramp = K.ramp("#2a6df4")
        self.assertEqual(len(ramp), 11)
        lightness = [K.rgb_to_oklch(K.parse_hex(ramp[k]))[0] for k in sorted(ramp)]
        self.assertEqual(lightness, sorted(lightness, reverse=True))

    def test_theme_tokens_are_readable(self):
        for dark in (False, True):
            tokens = {t["name"]: t["value"] for t in K.theme_tokens("#2a6df4", dark=dark)} if isinstance(K.theme_tokens("#2a6df4", dark=dark), list) else K.theme_tokens("#2a6df4", dark=dark)
            self.assertGreaterEqual(K.contrast(tokens["--fl-text"], tokens["--fl-bg"]), 7.0)
            self.assertGreaterEqual(K.contrast(tokens["--fl-text-2"], tokens["--fl-surface"]), 4.5)


if __name__ == "__main__":
    unittest.main()
