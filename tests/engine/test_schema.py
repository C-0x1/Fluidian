import unittest

import support  # noqa: F401
from fluidian import schema as SCH
from fluidian.testkit.mock_openai import strict_problems


class SchemaTest(unittest.TestCase):
    def test_compiles_notation_to_strict_json_schema(self):
        sch = SCH.compile_schema({"title": "str", "count": "int", "note?": "str", "tone": "enum:info|warning", "tags": ["str"]})
        self.assertEqual(sch["type"], "object")
        self.assertIs(sch["additionalProperties"], False)
        self.assertEqual(sorted(sch["required"]), ["count", "note", "tags", "title", "tone"], "strict mode requires every key")
        self.assertIn("null", str(sch["properties"]["note"]), "optional keys become nullable")
        self.assertEqual(sch["properties"]["tone"]["enum"], ["info", "warning"])
        self.assertEqual(strict_problems(sch), [])

    def test_validate_accepts_and_rejects(self):
        sch = SCH.compile_schema({"title": "str", "count": "int", "tags": ["str"]})
        self.assertEqual(SCH.validate({"title": "a", "count": 2, "tags": ["x"]}, sch), [])
        self.assertTrue(SCH.validate({"title": "a", "count": "2", "tags": []}, sch))
        self.assertTrue(SCH.validate({"title": "a", "tags": []}, sch))
        self.assertTrue(SCH.validate({"title": "a", "count": 1, "tags": [], "extra": 1}, sch))

    def test_booleans_are_not_integers(self):
        sch = SCH.compile_schema({"count": "int"})
        self.assertTrue(SCH.validate({"count": True}, sch))

    def test_synthesize_always_validates(self):
        for spec in ({"a": "str", "b": ["num"], "c": {"d": "bool", "e?": "int"}}, {"items": [{"label": "str", "score": "num"}]}, {"tone": "enum:a|b", "v": "json"}):
            sch = SCH.compile_schema(spec)
            self.assertEqual(SCH.validate(SCH.synthesize(sch, seed="t"), sch), [], spec)

    def test_every_capability_schema_is_strict_compatible(self):
        for cap in support.CAPS.values():
            for which in (cap.inp, cap.out):
                self.assertEqual(strict_problems(SCH.compile_schema(which)), [], cap.id)

    def test_describe_lists_fields(self):
        text = "\n".join(SCH.describe(SCH.compile_schema({"title": ("str", "Headline"), "n": "int"})))
        self.assertIn("title", text)
        self.assertIn("Headline", text)


if __name__ == "__main__":
    unittest.main()
