# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""The create-vendor-bill wizard must skip lines with nothing left to bill."""

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCreateVendorBillFilter(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Confirming the purchase order creates a receipt. The delivery-label
        # module installed in this database requires a DEPT department code,
        # resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "Vendor Bill Filter Test", "code": "VBFT"}
        )
        cls.env["hr.employee"].sudo().create(
            {
                "name": "Vendor Bill Filter Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        # Bill on ordered quantities so a confirmed order is billable straight
        # away (the default "on received quantities" policy needs a receipt).
        cls.product.purchase_method = "purchase"

    def _confirmed_po(self, quantity=2.0):
        """Create and confirm a purchase order carrying a single line."""
        po = (
            self.env["purchase.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.vendor.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "product_qty": quantity,
                                "price_unit": 50.0,
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

    def _create_bill(self, po):
        wizard = self.env["od19.purchase.create.vendor.bill"].create(
            {"purchase_order_id": po.id, "bill_date": "2026-02-01"}
        )
        action = wizard.action_create_bill()
        return self.env["account.move"].browse(action["res_id"])

    def test_fully_billed_order_produces_no_line(self):
        """A line already covered by a bill must not be billed a second time."""
        po = self._confirmed_po()
        first = self._create_bill(po)
        self.assertEqual(len(first.invoice_line_ids), 1)

        # The (draft) first bill already covers the ordered quantity.
        self.assertEqual(po.order_line.qty_to_invoice, 0.0)

        second = self._create_bill(po)
        self.assertFalse(second.invoice_line_ids)
