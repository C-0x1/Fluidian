import json
import os
import unittest

import support
from fluidian import components as C


def scene():
    return {"type": "Page", "props": {"title": "Orders"}, "children": [
        {"type": "Button", "id": "new", "props": {"label": "New order", "colour": "red"}, "on": {"click": "create_order"}},
        {"type": "Hologram", "props": {"text": "?"}},
        {"type": "Table", "id": "orders", "props": {"rows": [{"a": 1}]}, "ai": [{"capability": "data.query"}, {"capability": "nope.nothing"}]},
    ]}


class ComponentTest(unittest.TestCase):
    def test_registry_size_and_shape(self):
        self.assertEqual(len(C.COMPONENTS), 123)
        self.assertEqual(len({c["type"] for c in C.COMPONENTS}), 123)
        for spec in C.COMPONENTS:
            self.assertTrue(spec["summary"] and spec["category"], spec["type"])

    def test_every_example_is_already_normal(self):
        for spec in C.COMPONENTS:
            fixed, fixes = C.normalize(support.example_node(spec), drop_unknown=True)
            self.assertEqual(fixes, [], spec["type"])
            self.assertEqual(fixed["type"], spec["type"])

    def test_normalize_repairs_and_reports(self):
        fixed, fixes = C.normalize(scene(), actions=["list_orders"], capabilities={"data.query"}, drop_unknown=True)
        text = " ".join(fixes)
        self.assertIn("colour", text)
        self.assertIn("create_order", text)
        self.assertIn("Hologram", text)
        self.assertIn("nope.nothing", text)
        button = C.find(fixed, "new")
        self.assertNotIn("colour", button["props"])
        self.assertEqual(button["on"], {})
        self.assertEqual([b["capability"] for b in C.find(fixed, "orders")["ai"]], ["data.query"])

    def test_unknown_components_degrade_gracefully(self):
        wrapper = {"type": "FancyPanel", "props": {}, "children": [{"type": "Text", "props": {"content": "kept"}}]}
        fixed, fixes = C.normalize({"type": "Page", "props": {"title": "T"}, "children": [wrapper, {"type": "Mystery", "props": {"label": "Readable"}}, {"type": "Void", "props": {}}]}, drop_unknown=True)
        self.assertEqual([c["type"] for c in fixed["children"]], ["Stack", "Text"])
        self.assertEqual(fixed["children"][0]["children"][0]["props"]["content"], "kept")
        self.assertEqual(fixed["children"][1]["props"]["content"], "Readable")
        self.assertEqual(len(fixes), 3)
        lenient, _ = C.normalize({"type": "Page", "props": {"title": "T"}, "children": [{"type": "Void", "props": {}}]})
        self.assertEqual(lenient["children"][0]["props"]["content"], "Void", "outside grounding the placeholder stays visible to the developer")

    def test_ids_are_stable_and_explicit_ids_survive(self):
        first, _ = C.normalize(scene())
        second, _ = C.normalize(scene())
        self.assertEqual(first, second)
        ids = [n["id"] for n, _, _ in C.walk(first)]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("new", ids)
        self.assertTrue(C.is_auto_id(first["id"]))
        self.assertFalse(C.is_auto_id("name"))
        self.assertFalse(C.is_auto_id("new"))

    def test_normalize_is_idempotent(self):
        once, _ = C.normalize(scene())
        twice, fixes = C.normalize(once)
        self.assertEqual(once, twice)
        self.assertEqual(fixes, [])

    def test_hostile_input_never_raises(self):
        for junk in (None, 3, "x", [], {"type": 5}, {"type": "Page", "children": "no"}, {"type": "Page", "props": [], "children": [None, 1, {"props": {}}]}):
            fixed, _ = C.normalize(junk)
            self.assertIsInstance(fixed, dict)
            self.assertIn("type", fixed)

    def test_transport_round_trip(self):
        for spec in C.COMPONENTS:
            normal, _ = C.normalize(support.example_node(spec))
            wire = C.to_transport(normal)
            self.assertTrue(C.is_transport(wire), spec["type"])
            back, _ = C.normalize(C.from_transport(wire))
            self.assertEqual(back, normal, spec["type"])

    def test_diff_reports_added_removed_and_changed(self):
        before, _ = C.normalize({"type": "Page", "props": {"title": "A"}, "children": [{"type": "Text", "id": "t", "props": {"content": "one"}}, {"type": "Button", "id": "b", "props": {"label": "Go"}}]})
        after, _ = C.normalize({"type": "Page", "props": {"title": "A"}, "children": [{"type": "Text", "id": "t", "props": {"content": "two"}}, {"type": "Search", "id": "q", "props": {"name": "q"}}]})
        changes = {(d["op"], d["id"]) for d in C.diff(before, after)}
        self.assertEqual(changes, {("changed", "t"), ("removed", "b"), ("added", "q")})
        self.assertEqual(C.diff(before, before), [])

    def test_digest_respects_its_budget(self):
        big, _ = C.normalize({"type": "Page", "props": {"title": "Big"}, "children": [{"type": "Text", "props": {"content": "row %d " % i * 8}} for i in range(300)]})
        self.assertLessEqual(len(C.digest(big, 800)), 900)
        self.assertIn("Big", C.digest(big, 800))

    def test_published_spec_is_current(self):
        with open(os.path.join(support.ROOT, "spec", "components.json"), encoding="utf-8") as fh:
            published = json.load(fh)
        self.assertEqual(published, json.loads(json.dumps(C.export_spec())), "run `./fluidian codegen` to refresh spec/components.json")


if __name__ == "__main__":
    unittest.main()
