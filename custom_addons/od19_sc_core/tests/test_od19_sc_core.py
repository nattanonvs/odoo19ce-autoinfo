# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestOd19ScCore(TransactionCase):
    """Smoke tests: engine materializes to real Odoo records, with revisions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Template = cls.env["od19.sc.template"]

    def _make_template(self, **extra):
        vals = {
            "name": "Test Template",
            "code": "TEST-01",
            "department": "QA",
            "header_title": "QA Monitoring",
        }
        vals.update(extra)
        return self.Template.create(vals)

    def test_apply_creates_revision(self):
        template = self._make_template()
        self.assertFalse(template.revision_ids)
        template.action_apply()
        self.assertEqual(len(template.revision_ids), 1)

    def test_revision_restore(self):
        template = self._make_template()
        self.env["od19.sc.menu.node"].create({
            "template_id": template.id,
            "name": "Root Menu",
            "menu_type": "group",
        })
        template.action_apply()
        before = self.env["od19.sc.menu.node"].search_count(
            [("template_id", "=", template.id)])
        self.assertEqual(before, 1)
        # snapshot was taken before apply time; restoring must not crash
        template.action_rollback_last()
        self.assertTrue(template.exists())

    def test_menu_node_materialized(self):
        template = self._make_template()
        node = self.env["od19.sc.menu.node"].create({
            "template_id": template.id,
            "name": "QA Workbench",
            "menu_type": "group",
        })
        node._materialize()
        self.assertTrue(node.ir_menu_id)
        self.assertEqual(node.ir_menu_id.name, "QA Workbench")

    def test_menu_window_creates_action(self):
        template = self._make_template()
        node = self.env["od19.sc.menu.node"].create({
            "template_id": template.id,
            "name": "Partners",
            "menu_type": "window",
            "target_model": "res.partner",
            "view_mode": "list,form",
        })
        node._materialize()
        self.assertTrue(node.ir_action_id)
        model_name, action_id = node.ir_action_id.split(",")
        self.assertEqual(model_name, "ir.actions.act_window")
        action = self.env["ir.actions.act_window"].browse(int(action_id))
        self.assertEqual(action.res_model, "res.partner")

    def test_theme_asset_created(self):
        template = self._make_template()
        self.env["od19.sc.design.token"].create({
            "template_id": template.id,
            "key": "--sc-primary",
            "value": "#123456",
        })
        template._materialize_theme()
        asset = self.env["ir.asset"].search([("name", "=", "od19_sc_theme")], limit=1)
        self.assertTrue(asset)
        self.assertEqual(asset.bundle, "web.assets_backend")

    def test_field_def_creates_manual_field(self):
        template = self._make_template()
        field_def = self.env["od19.sc.field.def"].create({
            "template_id": template.id,
            "mode": "create",
            "target_model": "res.partner",
            "name": "qa_note",
            "field_description": "QA Note",
            "ttype": "char",
        })
        field_def._materialize()
        self.assertTrue(field_def.ir_field_id)
        self.assertEqual(field_def.ir_field_id.name, "x_qa_note")
        self.assertEqual(field_def.ir_field_id.state, "manual")

    def test_selection_field_values(self):
        template = self._make_template()
        field_def = self.env["od19.sc.field.def"].create({
            "template_id": template.id,
            "mode": "create",
            "target_model": "res.partner",
            "name": "qa_stage",
            "field_description": "QA Stage",
            "ttype": "selection",
            "selection_values": "draft|Draft\ndone|Done",
        })
        field_def._materialize()
        values = field_def.ir_field_id.selection_ids.mapped("value")
        self.assertIn("draft", values)
        self.assertIn("done", values)
