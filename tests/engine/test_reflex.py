"""Behaviour of the offline Reflex engine: every answer here is computed locally, without a model."""
import unittest
from datetime import datetime

import support
from fluidian.reflex import behavior as B
from fluidian.reflex import data as D
from fluidian.reflex import parse as PA
from fluidian.reflex import scene as SC
from fluidian.reflex import text as T

NOW = datetime(2026, 11, 19, 10, 0)  # a Thursday
NOTES = ("The importer now accepts CSV and Excel files up to 50 MB. Column types are detected automatically and can be corrected before import. "
         "Duplicate detection is not included in this release and arrives on the 14th. Imports run in the background, and you will be notified "
         "when they finish. Failed rows are collected in a downloadable report so nothing is lost.")


class ReflexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.k = support.offline_kernel()

    def ask(self, capability, payload, **kw):
        result = self.k.invoke(capability, payload, sid="t", now=NOW, **kw)
        self.assertTrue(result["ok"], result.get("error"))
        self.assertEqual(result["provenance"]["provider"], "reflex")
        return result["data"]

    # -- input ------------------------------------------------------------
    def test_natural_dates(self):
        self.assertEqual(self.ask("input.natural_date", {"text": "next friday 3pm"})["value"], "2026-11-27T15:00")
        self.assertEqual(self.ask("input.natural_date", {"text": "tomorrow"})["value"], "2026-11-20")
        self.assertEqual(self.ask("input.natural_date", {"text": "in 3 days"})["value"], "2026-11-22")
        self.assertEqual(self.ask("input.natural_date", {"text": "2027-01-05"})["value"], "2027-01-05")
        self.assertEqual(self.ask("input.natural_date", {"text": "purple"})["kind"], "unknown")

    def test_natural_quantities(self):
        mass = self.ask("input.natural_quantity", {"text": "2.5 tonnes", "expect": "mass"})
        self.assertEqual((mass["value"], mass["unit"], mass["dimension"]), ("2500", "kg", "mass"))
        self.assertEqual(self.ask("input.natural_quantity", {"text": "12 lbs"})["unit"], "kg")
        self.assertEqual(self.ask("input.natural_quantity", {"text": "90 minutes"})["dimension"], "time")

    def test_format_healing(self):
        email = self.ask("input.format_heal", {"value": "amara@gmial.com", "kind": "email"})
        self.assertEqual((email["value"], email["changed"]), ("amara@gmail.com", True))
        self.assertFalse(self.ask("input.format_heal", {"value": "amara@example.com", "kind": "email"})["changed"])

    def test_semantic_validation(self):
        bad = self.ask("input.semantic_validate", {"value": "amara@calder.example", "expectation": "job title"})
        self.assertFalse(bad["ok"])
        self.assertTrue(self.ask("input.semantic_validate", {"value": "Head of Procurement", "expectation": "job title"})["ok"])
        self.assertFalse(self.ask("input.semantic_validate", {"value": "asdf", "expectation": "company name"})["ok"])

    def test_smart_paste_maps_a_signature_onto_fields(self):
        text = "Dr. Amara Nwosu\nHead of Procurement, Calder Robotics\namara.nwosu@calder-robotics.example\n+44 20 7946 0321\n14 Wharf Lane, Bristol BS1 4RW, United Kingdom"
        fields = {f["name"]: f["value"] for f in self.ask("input.smart_paste", {"text": text, "fields": ["name", "title", "email", "phone", "postcode", "country"]})["fields"]}
        self.assertEqual(fields["email"], "amara.nwosu@calder-robotics.example")
        self.assertIn("Amara Nwosu", fields["name"])
        self.assertEqual(fields["title"], "Head of Procurement")
        self.assertEqual(fields["phone"].replace(" ", ""), "+442079460321")
        self.assertEqual(fields["postcode"], "BS1 4RW")
        self.assertEqual(fields["country"], "United Kingdom")

    def test_sensitive_data_shield(self):
        risky = self.ask("input.sensitive_shield", {"text": "Card 4242 4242 4242 4242, call +1 415 555 0134"})
        self.assertFalse(risky["safe"])
        self.assertNotIn("4242 4242", risky["redacted"])
        self.assertTrue(self.ask("input.sensitive_shield", {"text": "Leave the parcel at the loading dock."})["safe"])

    def test_ghost_completion(self):
        self.assertEqual(self.ask("input.ghost", {"text": "amara@gm"})["completion"], "ail.com")
        self.assertTrue(self.ask("input.ghost", {"text": "Sorry for"})["completion"].strip())
        self.assertEqual(self.ask("input.ghost", {"text": "Qz", "examples": ["Qzar Industries"]})["completion"], "ar Industries")

    # -- text -------------------------------------------------------------
    def test_titles_come_from_the_opening_clause(self):
        self.assertEqual(T.title_of(NOTES), "The importer now accepts CSV and Excel files")
        self.assertEqual(T.title_of("Short one."), "Short one")

    def test_questions_from_statements(self):
        questions = [T.question_from(s) for s in T.sentences(NOTES)]
        self.assertEqual(questions, ["Does the importer accept CSV and Excel files up to 50 MB?", "Are column types detected automatically?",
                                     "Is duplicate detection included in this release?", "Do imports run in the background?",
                                     "Are failed rows collected in a downloadable report?"])
        self.assertEqual(T.question_from("Hello there"), "")

    def test_plain_language_and_tone(self):
        self.assertEqual(T.simplify("Prior to utilising the service, users are required to authenticate and verify that sufficient funds are available."),
                         "Before using the service, users need to sign in and check that enough funds are available.")
        friendly = T.retone("Please be advised that you must confirm your address. Unable to schedule the courier. We cannot hold the parcel.", "friendly")
        self.assertIn("You'll need to", friendly)
        self.assertIn("We couldn't", friendly)
        self.assertIn("can't", friendly)
        self.assertNotIn("be advised", friendly)

    def test_friendly_errors(self):
        text = T.friendly_error("Error: operation failed due to invalid input parameters.", "Check the highlighted fields and try again.")
        self.assertTrue(text.startswith("We couldn't finish that"))
        self.assertNotIn("Error", text)
        self.assertTrue(text.endswith("try again."))

    def test_decisions_carry_owner_and_due_date(self):
        thread = [{"author": "Mira", "content": "Can we ship Friday?"}, {"author": "Ana", "content": "Agreed to defer. I will add a banner."},
                  {"author": "Mira", "content": "Great. Decision: ship Friday without dedupe, Jonas owns the follow-up for the 14th."}]
        found = T.decisions(thread)
        self.assertEqual([d["owner"] for d in found], ["Ana", "Jonas"])
        self.assertEqual(found[1]["due"], "the 14th")
        self.assertTrue(found[1]["decision"].startswith("Ship Friday"))

    def test_entities(self):
        kinds = {e["kind"]: e["text"] for e in PA.entities("Globex Marine paid $12,400 on 14 November 2026 after Jonas Weber called their Rotterdam office.")}
        self.assertEqual(kinds, {"money": "$12,400", "date": "14 November 2026", "organization": "Globex Marine", "place": "Rotterdam", "person": "Jonas Weber"})

    # -- data -------------------------------------------------------------
    def test_anomalies_survive_a_trend(self):
        revenue = [182000, 188500, 197200, 205400, 214100, 221800, 229300, 301700, 242600, 176900, 256400, 268900]
        found = D.anomalies(revenue, "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())
        self.assertEqual([(a["label"], a["direction"]) for a in found], [("Aug", "high"), ("Oct", "low")])
        self.assertEqual(D.anomalies([1, 2, 3, 4, 5, 6, 7, 8]), [], "a clean trend has no outliers")
        self.assertEqual(D.anomalies([10, 11, 10, 12, 11, 10, 11, 12, 10, 11]), [], "ordinary noise is not an anomaly")
        self.assertEqual(D.anomalies([5, 5, 5]), [], "too few points to judge")

    def test_plain_language_query(self):
        out = self.ask("data.query", {"question": "overdue over 5000, largest first", "rows": support.INVOICES})
        self.assertEqual([r["invoice"] for r in out["rows"]], ["INV-1", "INV-3"])
        self.assertEqual(out["matched"], 2)

    def test_forecast_follows_the_trend(self):
        points = self.ask("data.forecast", {"values": [10, 20, 30, 40, 50], "horizon": 2})["points"]
        self.assertEqual([round(p["value"]) for p in points], [60, 70])
        self.assertLessEqual(points[0]["low"], points[0]["value"])

    def test_formulas(self):
        self.assertEqual(D.formula_from_text("amount plus 20% tax", ["amount"])["expression"], "amount * 1.2")
        self.assertEqual(D.formula_from_text("price times quantity", ["price", "quantity"])["expression"], "price * quantity")
        self.assertEqual(self.ask("data.formula", {"description": "price times quantity", "columns": ["price", "quantity"], "rows": [{"price": 3, "quantity": 4}]})["preview"], [12.0])

    def test_column_types(self):
        types = {c["key"]: c["type"] for c in self.ask("data.column_types", {"rows": [{"amount": 12400, "status": "Overdue", "due": "2026-10-28"},
                                                                                       {"amount": 3150, "status": "Paid", "due": "2026-11-02"}]})["columns"]}
        self.assertEqual(types["due"], "date")
        self.assertIn(types["amount"], ("currency", "number"))

    # -- command and flow ---------------------------------------------------
    def test_routing_extracts_typed_arguments(self):
        hit = B.route("create an invoice for Globex Marine for $1,200 due next friday", support.ACTIONS)
        self.assertEqual(hit["action"], "create_invoice")
        self.assertEqual(hit["args"]["customer"], "Globex Marine")
        self.assertEqual(hit["args"]["amount"], 1200)
        self.assertEqual(B.route("send a reminder for INV-2041", support.ACTIONS)["args"], {"invoice": "INV-2041"})
        self.assertEqual(B.route("what is the weather", support.ACTIONS)["action"], "none")

    def test_plans_keep_amounts_and_names_intact(self):
        plan = B.plan("create an invoice for Globex Marine for $1,200 due next friday then send a reminder for INV-2041", support.ACTIONS)
        self.assertEqual([s["action"] for s in plan["steps"]], ["create_invoice", "send_reminder"])
        self.assertEqual(plan["steps"][0]["args"]["amount"], 1200)
        self.assertIn("Globex Marine", plan["steps"][0]["title"])
        self.assertEqual(plan["steps"][1]["risk"], "high")
        self.assertEqual(plan["summary"], "2 steps; 1 needs approval.")

    def test_rules_from_sentences(self):
        rule = B.parse_rule("when an invoice is overdue by 7 days, send a reminder to the customer", support.ACTIONS)
        self.assertEqual((rule["trigger"], rule["action"]), ("invoice", "send_reminder"))
        self.assertEqual(rule["conditions"], [{"field": "days_overdue", "op": "gte", "value": "7"}])
        self.assertEqual(B.parse_rule("do something", support.ACTIONS)["action"], "none")

    def test_frustration_detection(self):
        events = [{"t": t, "kind": k, "target": target} for t, k, target in [(0, "click", "save"), (180, "click", "save"), (340, "click", "save"),
                                                                             (520, "click", "save"), (2400, "error", "amount"), (5200, "error", "amount")]]
        self.assertEqual(B.frustration(events)["state"], "frustrated")
        self.assertEqual(B.frustration([{"t": 0, "kind": "click", "target": "save"}])["state"], "calm")

    # -- composition --------------------------------------------------------
    def test_intent_archetypes(self):
        def types(intent):
            scene, _ = SC.compose_intent(intent)
            return [n["type"] for n, _, _ in __import__("fluidian.components", fromlist=["walk"]).walk(scene)]
        self.assertIn("Rating", types("Collect feedback after a support call"))
        self.assertEqual(len([s for s in SC.compose_intent("Onboard a new customer in four steps")[0]["children"][0]["props"]["items"]]), 4)
        self.assertIn("Chart", types("Sales dashboard for the leadership team"))
        self.assertIn("Board", types("Kanban board for the sprint"))
        self.assertEqual(types("Login page")[0], "Page")
        self.assertEqual(SC.compose_intent("Onboard a new customer in four steps")[0]["props"]["title"], "Onboard a New Customer in Four Steps")

    def test_html_import_keeps_labelled_controls(self):
        html = ('<form><h2>Stay in the loop</h2><label>Name <input name="name" required></label><label>Email <input type="email" name="email"></label>'
                '<label><input type="checkbox" name="ok"> Remember me</label><select name="topic"><option>News</option><option>Blog</option></select>'
                '<script>alert(1)</script><button type="submit">Subscribe</button></form>')
        scene, _ = SC.html_import(html)
        self.assertEqual(scene["props"]["title"], "Stay in the loop")
        controls = [(n["type"], n["props"].get("label")) for n in scene["children"][0]["children"]]
        self.assertEqual(controls, [("Input", "Name"), ("Input", "Email"), ("Checkbox", "Remember me"), ("Select", None), ("Button", "Subscribe")])
        self.assertNotIn("alert", str(scene))

    def test_empty_state_names_the_thing(self):
        node = SC.empty_state("a list of projects for a design team", ["create_project", "import_projects"])
        self.assertEqual(node["props"]["title"], "No projects yet")
        self.assertEqual([b["props"]["label"] for b in node["children"][0]["children"]], ["Create project", "Import projects"])


if __name__ == "__main__":
    unittest.main()
