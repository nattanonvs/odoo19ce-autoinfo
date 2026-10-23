# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Remove wizard: the user always confirms before lines are removed."""

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullRemove(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Confirming the purchase order creates a receipt. The delivery-label
        # module installed in this database requires a DEPT department code,
        # resolved from the current user's employee record.
        cls.department = cls.env["hr.department"].sudo().create(
            {"name": "Pull Remove Test", "code": "PRT"}
        )
        cls.env["hr.employee"].sudo().create(
            {
                "name": "Pull Remove Test Employee",
                "user_id": cls.env.uid,
                "department_id": cls.department.id,
            }
        )
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        # Candidate lines are filtered on ``qty_to_invoice > 0``, which stays 0
        # with the default "on received quantities" policy until the receipt is
        # validated. The pull mechanism, not the control policy, is what these
        # tests exercise, so bill on ordered quantities instead.
        cls.product.purchase_method = "purchase"
        cls.po = cls._create_confirmed_po(5.0)

    @classmethod
    def _create_confirmed_po(cls, quantity):
        """Create and confirm a purchase order with a single line.

        ``button_confirm`` is itself gated by the procurement approval flow
        (od19_purchase_procurement_core), hence the submit/approve calls.
        """
        po = (
            cls.env["purchase.order"]
            .sudo()
            .create(
                {
                    "partner_id": cls.vendor.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": cls.product.id,
                                "product_qty": quantity,
                                "price_unit": 100.0,
                                "name": cls.product.name,
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

    def _bill_with_pulled_line(self):
        """Create a vendor bill and pull the PO line onto it."""
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
                "source_ref": "purchase.order,%s" % self.po.id,
            }
        )
        wizard._onchange_source_ref()
        wizard.action_pull()
        return bill

    def _open_remove_wizard(self, bill):
        return self.env["od19.document.pull.remove.wizard"].create(
            {"res_model": "account.move", "res_id": bill.id}
        )

    def test_bound_sources_lists_purchase_order(self):
        bill = self._bill_with_pulled_line()
        bound = bill._od19_pull_bound_sources()
        self.assertEqual(len(bound), 1)
        self.assertEqual(bound[0][0], self.po)
        self.assertEqual(bound[0][1], 1)
        self.assertEqual(
            bill.od19_pull_source_label, "%s (1)" % self.po.display_name
        )

    def test_wizard_builds_bound_sources_on_create(self):
        bill = self._bill_with_pulled_line()
        wizard = self._open_remove_wizard(bill)
        self.assertEqual(wizard.state, "choose")
        self.assertEqual(len(wizard.source_ids), 1)
        self.assertIn(self.po.display_name, wizard.source_ids.name)

    def test_remove_wizard_two_states_and_confirm_removes_lines(self):
        bill = self._bill_with_pulled_line()
        wizard = self._open_remove_wizard(bill)
        self.assertEqual(wizard.state, "choose")
        wizard.source_id = "purchase.order,%s" % self.po.id
        wizard.action_select_source()
        self.assertEqual(wizard.state, "confirm")
        self.assertEqual(len(wizard.source_line_ids), 1)
        wizard.action_remove()
        self.assertFalse(bill.invoice_line_ids)
        self.assertEqual(bill.od19_pull_source_label, False)

    def test_action_back_clears_preview(self):
        bill = self._bill_with_pulled_line()
        wizard = self._open_remove_wizard(bill)
        wizard.source_id = "purchase.order,%s" % self.po.id
        wizard.action_select_source()
        self.assertEqual(wizard.state, "confirm")
        wizard.action_back()
        self.assertEqual(wizard.state, "choose")
        self.assertFalse(wizard.source_line_ids)

    def test_removing_keeps_manually_added_lines(self):
        bill = self._bill_with_pulled_line()
        bill.write(
            {
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Manual line",
                            "quantity": 1.0,
                            "price_unit": 10.0,
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                        },
                    )
                ]
            }
        )
        wizard = self._open_remove_wizard(bill)
        wizard.source_id = "purchase.order,%s" % self.po.id
        wizard.action_select_source()
        wizard.action_remove()
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids.name, "Manual line")

    def test_select_source_raises_without_source(self):
        bill = self._bill_with_pulled_line()
        wizard = self._open_remove_wizard(bill)
        with self.assertRaises(UserError):
            wizard.action_select_source()

    def test_remove_raises_when_posted(self):
        bill = self._bill_with_pulled_line()
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
        wizard = self._open_remove_wizard(bill)
        wizard.source_id = "purchase.order,%s" % self.po.id
        with self.assertRaises(UserError):
            wizard.action_select_source()
