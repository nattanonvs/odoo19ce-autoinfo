# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Style B: bill the quantities that actually moved.

The receipt / delivery only decides *which* order lines are billable; the
money still comes from the order line, never from the picking. The picking
is recorded on the invoice line so the link can be listed and removed later.
"""

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullPicking(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Confirming an order creates a receipt / delivery. The
        # delivery-label module installed in this database requires a DEPT
        # department code, resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "Pull Picking Test", "code": "PPT"}
        )
        cls.env["hr.employee"].sudo().create(
            {
                "name": "Pull Picking Test Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.partner = cls.partner_a
        cls.product = cls.env["product.product"].create(
            {
                "name": "Pick Product",
                "type": "consu",
                "is_storable": True,
                # Bill what actually moved, so the picking drives the
                # billable quantity on both the purchase and the sale side.
                "purchase_method": "receive",
                "invoice_policy": "delivery",
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _confirmed_po(self, qty=3.0):
        po = (
            self.env["purchase.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "product_qty": qty,
                                "price_unit": 70.0,
                                "name": self.product.name,
                                "date_planned": "2026-01-01",
                            },
                        )
                    ],
                }
            )
        )
        po.action_od19_submit_for_approval()
        po.action_od19_approve()
        po.button_confirm()
        return po

    def _received_po(self, qty=3.0):
        """Confirm a purchase order and receive it in full."""
        po = self._confirmed_po(qty)
        picking = po.picking_ids
        picking.move_ids.write({"quantity": qty, "picked": True})
        picking.button_validate()
        return po, picking

    def _delivered_so(self, qty=3.0):
        """Confirm a sale order and deliver it in full."""
        so = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": qty,
                                "price_unit": 90.0,
                                "name": self.product.name,
                            },
                        )
                    ],
                }
            )
        )
        so.action_confirm()
        picking = so.picking_ids
        picking.move_ids.write({"quantity": qty, "picked": True})
        picking.button_validate()
        return so, picking

    def _draft_move(self, move_type):
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner.id,
                "invoice_date": "2026-02-01",
            }
        )

    def _pull(self, document, picking):
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": document.id,
                "source_ref": "stock.picking,%s" % picking.id,
            }
        )
        wizard._onchange_source_ref()
        return wizard

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_pull_by_receipt_sets_source_picking(self):
        po, picking = self._received_po()
        bill = self._draft_move("in_invoice")
        wizard = self._pull(bill, picking)
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.od19_source_picking_id, picking)
        self.assertEqual(bill.invoice_line_ids.purchase_line_id, po.order_line)
        self.assertIn((picking, 1), bill._od19_pull_bound_sources())

        # Managing the source removes the lines pulled from that receipt.
        self.assertEqual(bill._od19_pull_remove(picking), 1)
        self.assertFalse(bill.invoice_line_ids)

    def test_pull_by_receipt_skips_when_receipt_not_done(self):
        po = self._confirmed_po()
        bill = self._draft_move("in_invoice")
        self.assertFalse(
            bill._od19_pull_candidate_lines(po.picking_ids),
            "lines must not be pullable from a receipt that is not done",
        )

    def test_pull_by_delivery_sets_source_picking(self):
        so, picking = self._delivered_so()
        invoice = self._draft_move("out_invoice")
        wizard = self._pull(invoice, picking)
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(
            invoice.invoice_line_ids.od19_source_picking_id, picking
        )
        self.assertEqual(invoice.invoice_line_ids.sale_line_ids, so.order_line)
