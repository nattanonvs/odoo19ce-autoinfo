# -*- coding: utf-8 -*-
import ast
import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from odoo.tests.common import TransactionCase

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "dashboard_data.xml"


class TestDashboardSeedData(TransactionCase):
    """Guard the sample data shipped with the module.

    ``data/dashboard_data.xml`` is loaded with ``noupdate="1"``: it is applied on
    a fresh install only, because an upgrade must not overwrite the widgets a
    user customised. The database of an already installed instance therefore
    cannot be used to verify the four original widgets, so their rule tables are
    read straight from the XML. ``dashboard_owner_revenue_goal`` is new in
    19.0.2.0.0 and is created on every install, so it is asserted through the
    ORM to prove the seeded formula really runs.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tree = ElementTree.parse(str(DATA_FILE))
        cls.records = {
            node.get("id"): node for node in tree.getroot() if node.tag == "record"
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @classmethod
    def _field(cls, xmlid, name):
        for node in cls.records[xmlid]:
            if node.tag == "field" and node.get("name") == name:
                return node
        raise AssertionError("%s has no field %s" % (xmlid, name))

    @classmethod
    def _value(cls, xmlid, name):
        """Return a field value, reading ``eval`` when the field has one."""
        field = cls._field(xmlid, name)
        raw = field.get("eval")
        if raw is not None:
            return ast.literal_eval(raw)
        return (field.text or "").strip()

    @classmethod
    def _rule_specs(cls, xmlid):
        """Return the ``rule_ids`` commands of a widget as plain dictionaries."""
        raw = cls._field(xmlid, "rule_ids").get("eval")
        # The eval holds a python literal: one ``(0, 0, {...})`` command per rule.
        return [command[2] for command in ast.literal_eval(raw)]

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_seeded_rule_tables_match_the_retired_thresholds(self):
        # xmlid, red operator/value, yellow operator/value.
        expected = [
            ("dashboard_owner_revenue", "<=", 200000.0, "<=", 500000.0),
            ("dashboard_owner_receivables", ">=", 800000.0, ">=", 300000.0),
            ("dashboard_owner_late_delivery", ">=", 10.0, ">=", 3.0),
            ("dashboard_operational_late", ">=", 10.0, ">=", 3.0),
        ]
        for xmlid, red_operator, red_value, yellow_operator, yellow_value in expected:
            message = "seeded rule table of %s" % xmlid
            specs = self._rule_specs(xmlid)
            self.assertEqual(len(specs), 2, message)
            self.assertEqual(specs[0]["status"], "red", message)
            self.assertEqual(specs[0]["operator"], red_operator, message)
            self.assertEqual(specs[0]["compare_type"], "constant", message)
            self.assertEqual(specs[0]["compare_value"], red_value, message)
            self.assertEqual(specs[1]["status"], "yellow", message)
            self.assertEqual(specs[1]["operator"], yellow_operator, message)
            self.assertEqual(specs[1]["compare_value"], yellow_value, message)
            # The red band has to be tested before the yellow one.
            self.assertLess(specs[0]["sequence"], specs[1]["sequence"], message)

    def test_seeded_formula_widget_definition(self):
        xmlid = "dashboard_owner_revenue_goal"
        self.assertEqual(self._value(xmlid, "widget_type"), "kpi")
        self.assertEqual(self._value(xmlid, "value_format"), "percent")
        self.assertEqual(self._value(xmlid, "formula_mode"), "preset")
        self.assertEqual(self._value(xmlid, "formula_type"), "percent_of_goal")
        self.assertGreater(self._value(xmlid, "goal_value"), 0.0)
        # ``formula_slots`` holds raw JSON, not an evaluated python literal.
        self.assertEqual(json.loads(self._value(xmlid, "formula_slots")), {"a": "amount_total"})

        # ``percent_of_goal`` returns a percentage, so the thresholds stay on the
        # same scale as the value instead of the currency of the goal.
        specs = self._rule_specs(xmlid)
        self.assertEqual([spec["status"] for spec in specs], ["red", "yellow"])
        self.assertEqual([spec["compare_value"] for spec in specs], [80.0, 100.0])
        self.assertTrue(all(spec["compare_type"] == "constant" for spec in specs))

    def test_seeded_formula_widget_runs_in_the_database(self):
        widget = self.env.ref("od19_dashboard.dashboard_owner_revenue_goal")
        self.assertEqual(widget.formula_type, "percent_of_goal")
        self.assertIn("goal", widget._effective_expression())

        # value, expected status, expected status source.
        cases = [(50.0, "red", "rule"), (90.0, "yellow", "rule"), (120.0, "green", "default")]
        for value, expected_status, expected_source in cases:
            status, source = widget._evaluate_rules({"value": value})
            message = "Revenue vs Goal at %s" % value
            self.assertEqual(status, expected_status, message)
            # "green" is never seeded as a rule, it is the default fallback.
            self.assertEqual(source, expected_source, message)
