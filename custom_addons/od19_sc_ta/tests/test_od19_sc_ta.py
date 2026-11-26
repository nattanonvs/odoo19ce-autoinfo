# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

TEMPLATE_XMLID = "od19_sc_ta.template_ta_01"


class TestOd19ScTa(TransactionCase):
    """Template 01 (TA): โหลดครบ 5 มิติ + apply แล้วกลายเป็นของจริง (idempotent)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env.ref(TEMPLATE_XMLID)

    def test_template_loaded_with_five_dimensions(self):
        tpl = self.template
        self.assertEqual(tpl.code, "TA-01")
        self.assertEqual(tpl.department, "TA")
        self.assertEqual(tpl.header_title, "TA Service & Equipment Workload Monitoring")
        self.assertEqual(len(tpl.menu_node_ids), 8)
        self.assertEqual(len(tpl.field_def_ids), 8)
        self.assertEqual(len(tpl.design_token_ids), 8)
        self.assertEqual(len(tpl.formula_ids), 2)
        self.assertEqual(len(tpl.integration_ids), 2)

    def test_menu_tree_has_parents_and_children(self):
        groups = self.template.menu_node_ids.filtered(lambda n: not n.parent_id)
        self.assertEqual(len(groups), 3)
        child = self.template.menu_node_ids.filtered(lambda n: n.name == "Equipment Register")
        self.assertEqual(child.target_model, "maintenance.equipment")
        self.assertEqual(child.parent_id.name, "TA Service")

    def test_apply_materializes_menu(self):
        self.template.action_apply()
        for node in self.template.menu_node_ids:
            self.assertTrue(node.ir_menu_id, "menu node %s not materialized" % node.name)
            self.assertTrue(node.ir_menu_id.exists())
        designer = self.template.menu_node_ids.filtered(lambda n: n.menu_type == "client")
        self.assertEqual(len(designer), 1)
        self.assertEqual(designer.client_tag, "od19_sc.designer")

    def test_apply_materializes_new_fields(self):
        self.template.action_apply()
        created = self.template.field_def_ids.filtered(lambda f: f.mode == "create")
        self.assertTrue(created)
        for fdef in created:
            self.assertTrue(fdef.ir_field_id, "field %s not materialized" % fdef.name)
            self.assertTrue(fdef.ir_field_id.name.startswith("x_"))
            self.assertEqual(fdef.ir_field_id.state, "manual")
        points = self.template.field_def_ids.filtered(
            lambda f: f.name == "x_ta_workload_points")
        self.assertEqual(points.ir_field_id.ttype, "integer")
        self.assertTrue(points.ir_field_id.readonly)

    def test_apply_materializes_existing_field_override(self):
        self.template.action_apply()
        override = self.template.field_def_ids.filtered(
            lambda f: f.mode == "existing" and f.name == "priority")
        self.assertEqual(len(override), 1)
        self.assertTrue(override.ir_view_id, "priority override view not created")
        self.assertIn('name="string"', override.ir_view_id.arch)

    def test_apply_materializes_theme_asset(self):
        self.template.action_apply()
        asset = self.env["ir.asset"].search([("name", "=", "od19_sc_theme")], limit=1)
        self.assertTrue(asset)
        self.assertEqual(asset.bundle, "web.assets_backend")

    def test_apply_materializes_formula_cron(self):
        self.template.action_apply()
        for formula in self.template.formula_ids:
            self.assertEqual(formula.trigger, "cron")
            self.assertTrue(formula.ir_cron_id, "formula %s has no cron" % formula.name)
            self.assertTrue(formula.ir_cron_id.exists())

    def test_formulas_target_existing_manual_fields(self):
        names = self.template.field_def_ids.mapped("name")
        for formula in self.template.formula_ids:
            self.assertIn(formula.target_field, names)

    def test_apply_is_idempotent(self):
        self.template.action_apply()
        first_menus = set(self.template.menu_node_ids.mapped("ir_menu_id").ids)
        first_fields = set(
            self.template.field_def_ids.filtered(lambda f: f.mode == "create")
            .mapped("ir_field_id").ids)
        self.template.action_apply()
        second_menus = set(self.template.menu_node_ids.mapped("ir_menu_id").ids)
        second_fields = set(
            self.template.field_def_ids.filtered(lambda f: f.mode == "create")
            .mapped("ir_field_id").ids)
        self.assertEqual(first_menus, second_menus)
        self.assertEqual(first_fields, second_fields)
