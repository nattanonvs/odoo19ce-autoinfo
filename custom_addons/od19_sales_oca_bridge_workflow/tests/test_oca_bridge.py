from odoo.tests.common import TransactionCase


class TestOcaBridge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.order_model = cls.env["sale.order"]
        cls.bridge_view = cls.env.ref(
            "od19_sales_oca_bridge_workflow.view_order_form_inherit_od19_oca_bridge"
        )

    def test_deferred_integration_points_remain_available(self):
        self.assertIn("od19_requires_tier_validation", self.order_model._fields)
        self.assertIn("od19_invoice_plan_mode", self.order_model._fields)

    def test_required_now_bridge_fields_are_registered(self):
        self.assertIn("od19_revision_bridge_ready", self.order_model._fields)
        self.assertIn("od19_exception_bridge_ready", self.order_model._fields)
        self.assertIn("od19_blanket_bridge_ready", self.order_model._fields)

    def test_required_now_bridge_capabilities_match_oca_modules(self):
        capabilities = self.order_model._od19_required_now_bridge_capabilities()
        self.assertTrue(capabilities["revision"])
        self.assertTrue(capabilities["exception"])
        self.assertTrue(capabilities["blanket"])
        self.assertIn("current_revision_id", self.order_model._fields)
        self.assertIn("old_revision_ids", self.order_model._fields)
        self.assertIn("exception_ids", self.order_model._fields)
        self.assertIn("ignore_exception", self.order_model._fields)
        self.assertIn("blanket_order_id", self.order_model._fields)
        self.assertTrue(hasattr(type(self.order_model), "create_revision"))
        self.assertTrue(hasattr(type(self.order_model), "detect_exceptions"))

    def test_required_now_bridge_fields_compute_ready_state(self):
        order = self.order_model.new({})
        self.assertTrue(order.od19_revision_bridge_ready)
        self.assertTrue(order.od19_exception_bridge_ready)
        self.assertTrue(order.od19_blanket_bridge_ready)

    def test_bridge_view_separates_required_now_and_deferred_sections(self):
        arch = self.bridge_view.arch_db
        self.assertIn('separator string="OCA Bridge (Required Now)"', arch)
        self.assertIn('field name="od19_revision_bridge_ready"', arch)
        self.assertIn('field name="od19_exception_bridge_ready"', arch)
        self.assertIn('field name="od19_blanket_bridge_ready"', arch)
        self.assertIn('field name="current_revision_id"', arch)
        self.assertIn('field name="ignore_exception"', arch)
        self.assertIn('field name="blanket_order_id"', arch)
        self.assertIn('separator string="OCA Bridge (Deferred Integration Points)"', arch)
