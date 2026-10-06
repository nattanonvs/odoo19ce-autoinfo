from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestProcurementApproval(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Approved Vendor", "company_type": "company"}
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Approval Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )

    def _create_order(self):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
            }
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom_id": self.product.uom_id.id,
            }
        )
        return order

    def test_direct_po_requires_explicit_approval_before_confirm(self):
        order = self._create_order()
        with self.assertRaises(UserError):
            order.button_confirm()
        order.action_od19_submit_for_approval()
        order.action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.od19_approval_state, "approved")

    def test_requisition_requires_explicit_approval_before_confirm(self):
        requisition = self.env["purchase.requisition"].create(
            {
                "vendor_id": self.vendor.id,
                "requisition_type": "blanket_order",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 2,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": 50,
                        },
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            requisition.action_confirm()
        requisition.action_od19_submit_for_approval()
        requisition.action_od19_approve()
        requisition.action_confirm()
        self.assertEqual(requisition.od19_approval_state, "approved")
