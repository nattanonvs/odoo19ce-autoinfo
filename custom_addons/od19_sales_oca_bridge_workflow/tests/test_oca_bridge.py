from odoo.tests.common import TransactionCase


class TestOcaBridge(TransactionCase):
    def test_sale_order_has_deferred_bridge_fields(self):
        order = self.env["sale.order"]
        self.assertIn("od19_requires_tier_validation", order._fields)
        self.assertIn("od19_invoice_plan_mode", order._fields)

    def test_sale_order_has_required_now_bridge_fields(self):
        order = self.env["sale.order"]
        self.assertIn("od19_enable_revision", order._fields)
        self.assertIn("od19_use_exception_rules", order._fields)
        self.assertIn("od19_use_blanket_order", order._fields)
