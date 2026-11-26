# -*- coding: utf-8 -*-
"""Tests for the Service Center Designer RPC bridge (od19.sc.designer)."""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestOd19ScDesigner(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.designer = cls.env["od19.sc.designer"]
        cls.template = cls.env["od19.sc.template"].create({
            "name": "Designer QA Template",
            "code": "QA-01",
            "department": "QA",
            "header_title": "QA Header",
        })

    def test_bootstrap_shape(self):
        data = self.designer.get_bootstrap()
        self.assertIn("templates", data)
        self.assertIn("meta", data)
        self.assertIn(self.template.id, [tpl["id"] for tpl in data["templates"]])
        # every dimension selector must be exposed to the UI
        for key in ("menu_types", "field_modes", "field_types", "formula_triggers",
                    "interval_types", "directions", "http_methods"):
            self.assertTrue(data["meta"][key], "missing meta key: %s" % key)

    def test_get_template_returns_all_dimensions(self):
        data = self.designer.get_template(self.template.id)
        self.assertEqual(data["template"]["code"], "QA-01")
        for model_name in ("od19.sc.menu.node", "od19.sc.field.def", "od19.sc.design.token",
                           "od19.sc.formula", "od19.sc.integration.endpoint"):
            self.assertIn(model_name, data)

    def test_get_template_unknown_raises(self):
        with self.assertRaises(UserError):
            self.designer.get_template(99999999)

    def test_save_record_creates_token(self):
        record = self.designer.save_record(
            "od19.sc.design.token", self.template.id,
            {"key": "--sc-qa", "value": "#123456", "sequence": 5}, False)
        self.assertEqual(record["key"], "--sc-qa")
        token = self.env["od19.sc.design.token"].browse(record["id"])
        self.assertEqual(token.template_id, self.template)

    def test_save_record_ignores_protected_fields(self):
        record = self.designer.save_record(
            "od19.sc.design.token", self.template.id,
            {"key": "--sc-qa", "value": "#fff", "template_id": 999999}, False)
        token = self.env["od19.sc.design.token"].browse(record["id"])
        self.assertEqual(token.template_id, self.template)

    def test_save_record_rejects_unknown_model(self):
        with self.assertRaises(UserError):
            self.designer.save_record("res.partner", self.template.id, {"name": "x"}, False)

    def test_save_record_updates_existing(self):
        record = self.designer.save_record(
            "od19.sc.design.token", self.template.id, {"key": "--sc-qa", "value": "#000"}, False)
        updated = self.designer.save_record(
            "od19.sc.design.token", self.template.id, {"value": "#fff"}, record["id"])
        self.assertEqual(updated["value"], "#fff")

    def test_delete_record(self):
        record = self.designer.save_record(
            "od19.sc.design.token", self.template.id, {"key": "--sc-qa", "value": "#000"}, False)
        self.assertTrue(self.designer.delete_record("od19.sc.design.token", record["id"]))
        self.assertFalse(self.env["od19.sc.design.token"].browse(record["id"]).exists())

    def test_preview_counts(self):
        self.designer.save_record(
            "od19.sc.design.token", self.template.id, {"key": "--sc-qa", "value": "#000"}, False)
        preview = self.designer.preview_template(self.template.id)
        self.assertEqual(preview["design_tokens"], 1)
        self.assertEqual(preview["menu_nodes"], 0)

    def test_apply_creates_revision(self):
        self.designer.save_record(
            "od19.sc.menu.node", self.template.id,
            {"name": "QA Menu", "menu_type": "group", "sequence": 10}, False)
        self.assertTrue(self.designer.apply_template(self.template.id))
        self.assertEqual(len(self.template.revision_ids), 1)
        self.assertTrue(self.template.menu_node_ids.ir_menu_id)

    def test_save_template_header(self):
        self.designer.save_template(self.template.id, {"header_title": "QA Header v2"})
        self.assertEqual(self.template.header_title, "QA Header v2")

    def test_test_formula_evaluates(self):
        formula = self.env["od19.sc.formula"].create({
            "template_id": self.template.id,
            "name": "QA formula",
            "target_model": "res.partner",
            "target_field": "name",
            "expression": "'qa'",
        })
        result = self.designer.test_formula(formula.id)
        self.assertIn("qa", result)

    def test_test_integration_without_url_raises(self):
        endpoint = self.env["od19.sc.integration.endpoint"].create({
            "template_id": self.template.id,
            "name": "QA endpoint",
        })
        with self.assertRaises(UserError):
            self.designer.test_integration(endpoint.id)
