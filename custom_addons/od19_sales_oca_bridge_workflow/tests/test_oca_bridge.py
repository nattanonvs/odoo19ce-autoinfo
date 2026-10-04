import ast
from pathlib import Path

from odoo.tests.common import TransactionCase


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

    def test_bridge_view_separates_required_now_and_deferred_sections(self):
        arch = self.bridge_view.arch_db
        self.assertIn('separator string="OCA Bridge (Required Now)"', arch)
        self.assertIn('field name="od19_delivery_state_bridge_ready"', arch)
        self.assertIn('field name="delivery_status"', arch)
        self.assertIn('field name="od19_revision_bridge_ready"', arch)
        self.assertIn('field name="od19_exception_bridge_ready"', arch)
        self.assertIn('field name="od19_blanket_bridge_ready"', arch)
        self.assertIn('field name="current_revision_id"', arch)
        self.assertIn('field name="main_exception_id"', arch)
        self.assertIn('field name="exceptions_summary"', arch)
        self.assertNotIn('field name="ignore_exception"', arch)
        self.assertIn('field name="blanket_order_id"', arch)
        self.assertIn('separator string="OCA Bridge (Deferred Integration Points)"', arch)
