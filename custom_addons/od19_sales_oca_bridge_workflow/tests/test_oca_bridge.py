import ast
from pathlib import Path

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, new_test_user


class TestOcaBridge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order_model = cls.env["sale.order"]
        cls.bridge_view = cls.env.ref(
            "od19_sales_oca_bridge_workflow.view_order_form_inherit_od19_oca_bridge"
        )
        manifest_path = Path(__file__).resolve().parents[1] / "__manifest__.py"
        cls.bridge_manifest = ast.literal_eval(manifest_path.read_text())

        cls.customer = cls.env["res.partner"].create({"name": "Tier Test Customer"})
        cls.product = cls.env["product.product"].create(
            {"name": "Tier Test Product", "type": "service", "list_price": 100.0}
        )
        cls.sales_manager = new_test_user(
            cls.env,
            login="od19_tier_sales_manager",
            groups="sales_team.group_sale_salesman,sales_team.group_sale_manager",
        )
        cls.sales_director = new_test_user(
            cls.env,
            login="od19_tier_sales_director",
            groups="sales_team.group_sale_salesman,"
            "od19_sales_oca_bridge_workflow.group_sale_director",
        )

    def _create_order(self, amount):
        qty = max(1, int(amount // 100))
        price_unit = amount / qty if qty else amount
        return self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                        }
                    )
                ],
            }
        )

    def test_deferred_integration_points_remain_available(self):
        self.assertIn("od19_requires_tier_validation", self.order_model._fields)
        self.assertIn("od19_invoice_plan_mode", self.order_model._fields)

    def test_required_now_bridge_fields_are_registered(self):
        self.assertIn("od19_delivery_state_bridge_ready", self.order_model._fields)
        self.assertIn("od19_revision_bridge_ready", self.order_model._fields)
        self.assertIn("od19_exception_bridge_ready", self.order_model._fields)
        self.assertIn("od19_blanket_bridge_ready", self.order_model._fields)

    def test_required_now_bridge_capabilities_match_oca_modules(self):
        capabilities = self.order_model._od19_required_now_bridge_capabilities()
        self.assertTrue(capabilities["delivery"])
        self.assertTrue(capabilities["revision"])
        self.assertTrue(capabilities["exception"])
        self.assertTrue(capabilities["blanket"])
        self.assertIn("delivery_status", self.order_model._fields)
        self.assertIn("force_delivery_state", self.order_model._fields)
        self.assertIn("current_revision_id", self.order_model._fields)
        self.assertIn("old_revision_ids", self.order_model._fields)
        self.assertIn("exception_ids", self.order_model._fields)
        self.assertIn("main_exception_id", self.order_model._fields)
        self.assertIn("exceptions_summary", self.order_model._fields)
        self.assertIn("blanket_order_id", self.order_model._fields)
        self.assertTrue(hasattr(type(self.order_model), "action_force_delivery_state"))
        self.assertTrue(hasattr(type(self.order_model), "create_revision"))
        self.assertTrue(hasattr(type(self.order_model), "detect_exceptions"))

    def test_required_now_bridge_fields_compute_ready_state(self):
        order = self.order_model.new({})
        self.assertTrue(order.od19_delivery_state_bridge_ready)
        self.assertTrue(order.od19_revision_bridge_ready)
        self.assertTrue(order.od19_exception_bridge_ready)
        self.assertTrue(order.od19_blanket_bridge_ready)

    def test_manifest_keeps_only_oca_required_now_dependencies(self):
        manifest_depends = self.bridge_manifest["depends"]
        self.assertNotIn("od19_sales_project_context", manifest_depends)
        self.assertNotIn("od19_sales_contract_core", manifest_depends)
        self.assertNotIn("od19_sales_billing_evidence", manifest_depends)
        self.assertNotIn("od19_sales_reporting", manifest_depends)
        self.assertNotIn("base_user_role", manifest_depends)
        self.assertIn("base_tier_validation", manifest_depends)

    def test_bridge_view_separates_required_now_and_deferred_sections(self):
        arch = self.bridge_view.arch_db
        self.assertIn('separator string="OCA Bridge (Required Now)"', arch)
        self.assertIn('field name="delivery_status"', arch)
        self.assertIn('field name="current_revision_id"', arch)
        self.assertIn('field name="main_exception_id"', arch)
        self.assertIn('field name="exceptions_summary"', arch)
        self.assertIn('field name="blanket_order_id"', arch)
        self.assertNotIn('field name="od19_delivery_state_bridge_ready"', arch)
        self.assertNotIn('field name="od19_revision_bridge_ready"', arch)
        self.assertNotIn('field name="od19_exception_bridge_ready"', arch)
        self.assertNotIn('field name="od19_blanket_bridge_ready"', arch)
        self.assertNotIn('field name="ignore_exception"', arch)
        self.assertNotIn('field name="od19_requires_tier_validation"', arch)
        self.assertNotIn('field name="od19_invoice_plan_mode"', arch)
        self.assertNotIn('separator string="OCA Bridge (Deferred Integration Points)"', arch)

    def test_tier_validation_fields_registered(self):
        self.assertIn("review_ids", self.order_model._fields)
        self.assertIn("need_validation", self.order_model._fields)
        self.assertIn("validation_status", self.order_model._fields)
        self.assertIn("reviewer_ids", self.order_model._fields)
        self.assertIn("can_review", self.order_model._fields)

    def test_sale_order_state_includes_waiting_approval(self):
        state_field = self.order_model._fields["state"]
        selection = dict(state_field.selection)
        self.assertIn("waiting_approval", selection)

    def test_low_amount_order_confirms_without_approval(self):
        order = self._create_order(50000)
        self.assertFalse(order.need_validation)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_manager_threshold_order_waits_for_approval(self):
        order = self._create_order(200000)
        self.assertTrue(order.need_validation)
        order.action_confirm()
        self.assertEqual(order.state, "waiting_approval")
        self.assertTrue(order.review_ids)
        self.assertIn(order.validation_status, ("pending", "waiting"))
        # Cannot confirm before validation
        with self.assertRaises(ValidationError):
            order.action_confirm()

    def test_director_threshold_order_waits_for_approval(self):
        order = self._create_order(600000)
        self.assertTrue(order.need_validation)
        order.action_confirm()
        self.assertEqual(order.state, "waiting_approval")
        self.assertTrue(order.review_ids)

    def test_manager_approval_allows_confirm(self):
        order = self._create_order(200000)
        order.action_confirm()
        self.assertEqual(order.state, "waiting_approval")
        order.with_user(self.sales_manager).validate_tier()
        self.assertEqual(order.validation_status, "validated")
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_director_approval_allows_confirm(self):
        order = self._create_order(600000)
        order.action_confirm()
        self.assertEqual(order.state, "waiting_approval")
        order.with_user(self.sales_director).validate_tier()
        self.assertEqual(order.validation_status, "validated")
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_manager_cannot_approve_director_tier(self):
        order = self._create_order(600000)
        order.action_confirm()
        self.assertEqual(order.state, "waiting_approval")
        order.with_user(self.sales_manager).validate_tier()
        self.assertNotEqual(order.validation_status, "validated")

    def test_tier_definition_model_names_include_sale_order(self):
        names = self.env["tier.definition"]._get_tier_validation_model_names()
        self.assertIn("sale.order", names)
