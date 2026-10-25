# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""GRNI report: purchase lines received but not yet billed."""

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestGrniReport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Confirming the purchase order creates a receipt. The delivery-label
        # module installed in this database requires a DEPT department code,
        # resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "GRNI Test", "code": "GRNI"}
        )
        cls.env["hr.employee"].sudo().create(
            {
                "name": "GRNI Test Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.vendor = cls.partner_a
        cls.product = cls.env["product.product"].create(
            {
                "name": "GRNI Product",
                "purchase_ok": True,
                "is_storable": True,
                # Bill on received quantities, so a received but unbilled line
                # has something left to invoice and straddles the report.
                "purchase_method": "receive",
            }
        )

    def _received_po(self, qty=3.0):
        """Create, confirm and fully receive a single-line purchase order."""
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
        picking = po.picking_ids
        picking.move_ids.write({"quantity": qty, "picked": True})
        picking.button_validate()
        return po

    def test_grni_action_exists(self):
        action = self.env.ref(
            "od19_document_pull.action_od19_grni_report", raise_if_not_found=False
        )
        self.assertTrue(action, "GRNI action must be defined")
        self.assertEqual(action.res_model, "purchase.order.line")

    def test_grni_domain_returns_received_not_billed(self):
        po = self._received_po()
        domain = self.env["purchase.order.line"]._od19_grni_domain()
        lines = self.env["purchase.order.line"].search(domain)
        # Received, nothing billed yet: the line belongs to GRNI.
        self.assertIn(po.order_line, lines)

        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "invoice_date": "2026-02-01",
            }
        )
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": bill.id,
                "source_ref": "purchase.order,%s" % po.id,
            }
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        # The Thai tax module (l10n_th_account_tax) blocks posting a purchase
        # bill with VAT until its tax invoice number and date are filled in.
        if bill.tax_invoice_ids:
            bill.tax_invoice_ids.write(
                {
                    "tax_invoice_number": "TEST-TINV-001",
                    "tax_invoice_date": fields.Date.today(),
                }
            )
        bill.action_post()

        lines = self.env["purchase.order.line"].search(domain)
        # Once billed, the line has left GRNI.
        self.assertNotIn(po.order_line, lines)
