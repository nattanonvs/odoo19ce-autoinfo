from odoo.tests.common import TransactionCase


class TestProcurementBlanketReceipt(TransactionCase):
    """Call-off roll-up of received quantities on a blanket order.

    Core tracks how much an agreement line was ordered through its call-off
    purchase orders (``qty_ordered``). This module adds ``od19_qty_received``
    that mirrors the same call-off roll-up but sums the ``qty_received`` of the
    linked purchase order lines, so a blanket agreement shows how much was
    actually received over its lifetime.
    """

    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Blanket Vendor", "company_type": "company"}
        )
        manager_group = self.env.ref("purchase.group_purchase_manager")
        base_user_group = self.env.ref("base.group_user")
        self.manager = (
            self.env["res.users"]
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": "Blanket Purchase Manager",
                    "login": "blanket.manager@example.com",
                    "email": "blanket.manager@example.com",
                    "company_id": self.env.company.id,
                    "company_ids": [(6, 0, [self.env.company.id])],
                    "group_ids": [(6, 0, [base_user_group.id, manager_group.id])],
                }
            )
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Blanket Goods",
                "purchase_ok": True,
                "type": "consu",
                "is_storable": True,
            }
        )

    def _create_agreement(self):
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
                            "product_qty": 10,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": 25,
                        },
                    )
                ],
            }
        )
        requisition.action_od19_submit_for_approval()
        requisition.with_user(self.manager).action_od19_approve()
        requisition.action_confirm()
        self.assertEqual(requisition.state, "confirmed")
        return requisition

    def _create_call_off_order(self, requisition, qty):
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "requisition_id": requisition.id,
            }
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": qty,
                "price_unit": 25,
                "product_uom_id": self.product.uom_id.id,
                "date_planned": "2026-11-01 00:00:00",
                "tax_ids": False,
            }
        )
        order.action_od19_submit_for_approval()
        order.with_user(self.manager).action_od19_approve()
        order.button_confirm()
        self.assertEqual(order.state, "purchase")
        return order

    def _receive(self, order, qty):
        picking = order.picking_ids.filtered(lambda p: p.state != "done")
        picking.move_ids.quantity = qty
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True).button_validate()

    def test_agreement_tracks_received_quantity(self):
        requisition = self._create_agreement()
        line = requisition.line_ids
        self.assertEqual(line.od19_qty_received, 0.0)

        order = self._create_call_off_order(requisition, 10)
        line.invalidate_recordset()
        self.assertEqual(line.od19_qty_received, 0.0)

        self._receive(order, 4)
        line.invalidate_recordset()
        self.assertEqual(line.od19_qty_received, 4.0)

        self._receive(order, 6)
        line.invalidate_recordset()
        self.assertEqual(line.od19_qty_received, 10.0)

    def test_received_ignores_unconfirmed_orders(self):
        requisition = self._create_agreement()
        line = requisition.line_ids
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "requisition_id": requisition.id,
            }
        )
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 5,
                "price_unit": 25,
                "product_uom_id": self.product.uom_id.id,
                "date_planned": "2026-11-01 00:00:00",
                "tax_ids": False,
            }
        )
        # A draft call-off order must not contribute to the received roll-up.
        self.assertEqual(order.state, "draft")
        line.invalidate_recordset()
        self.assertEqual(line.od19_qty_received, 0.0)
