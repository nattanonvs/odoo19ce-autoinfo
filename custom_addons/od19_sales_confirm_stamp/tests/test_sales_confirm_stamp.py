from odoo import fields
from odoo.tests.common import TransactionCase


class TestSalesConfirmStamp(TransactionCase):
    """Basic tests for the sales confirm stamp extension."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Stamp Customer"})
        cls.product = cls.env["product.product"].create({
            "name": "Test Stamp Product",
            "type": "consu",
        })

    def _create_sale_order(self, **overrides):
        vals = {
            "partner_id": self.partner.id,
            "order_line": [(0, 0, {
                "product_id": self.product.id,
                "product_uom_qty": 1,
                "price_unit": 100.0,
            })],
        }
        vals.update(overrides)
        return self.env["sale.order"].create(vals)

    def test_confirm_sets_confirmed_by(self):
        order = self._create_sale_order()
        self.assertFalse(order.confirmed_by_id)
        order.action_confirm()
        self.assertEqual(order.confirmed_by_id, self.env.user)

    def test_stamp_fields_are_writable(self):
        order = self._create_sale_order({
            "stamp_date": fields.Date.today(),
            "stamp_code": "JOB-001",
        })
        self.assertEqual(order.stamp_date, fields.Date.today())
        self.assertEqual(order.stamp_code, "JOB-001")

    def test_confirmed_by_not_overwritten_on_second_confirm(self):
        order = self._create_sale_order()
        order.action_confirm()
        first_confirmer = order.confirmed_by_id
        # Calling action_confirm again should not change confirmed_by_id
        order.action_confirm()
        self.assertEqual(order.confirmed_by_id, first_confirmer)
