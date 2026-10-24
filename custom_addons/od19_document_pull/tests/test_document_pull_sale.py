# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullSale(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Confirming the sale order creates a delivery. The delivery-label
        # module installed in this database requires a DEPT department code,
        # resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "Pull Sale Test", "code": "PST"}
        )
        cls.env["hr.employee"].sudo().create(
            {
                "name": "Pull Sale Test Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.customer = cls.partner_a
        cls.product = cls.product_a
        # Candidate lines are filtered on ``qty_to_invoice > 0``; bill on
        # ordered quantities so a confirmed order has something to pull.
        cls.product.invoice_policy = "order"

    def _confirmed_so(self, qty=4.0):
        # The test user has no Sales rights, so the order is created with
        # sudo() - the pull mechanism, not the sales ACLs, is under test.
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": 250.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        return so

    def _draft_invoice(self):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": "2026-02-01",
            }
        )

    def test_pull_sale_lines_two_modes(self):
        so = self._confirmed_so()
        invoice = self._draft_invoice()
        wizard = self.env["od19.document.pull.wizard"].create(
            {
                "res_model": "account.move",
                "res_id": invoice.id,
                "source_ref": "sale.order,%s" % so.id,
            }
        )
        wizard._onchange_source_ref()
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.action_pull()
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.sale_line_ids, so.order_line)
        self.assertAlmostEqual(invoice.invoice_line_ids.price_unit, 250.0)

    def test_legacy_get_sale_lines_button_uses_central_mechanism(self):
        so = self._confirmed_so()
        invoice = self._draft_invoice()
        action = invoice.action_open_get_sale_lines()
        self.assertEqual(action["res_model"], "od19.document.pull.wizard")
        self.assertEqual(action["context"]["default_res_id"], invoice.id)
