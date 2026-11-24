# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
from odoo import fields
from odoo.tests import tagged, TransactionCase


@tagged("post_install", "-at_install")
class TestPaymentWhtVat(TransactionCase):
    """T7 (WHT lines book on the WHT account, net correct) and K9 (VAT lines
    are detail-only, not deducted from the net, with an editable VAT date)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env["res.partner"].create({"name": "WHT Customer"})
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create({
                "name": "WHT Bank",
                "code": "WHTB",
                "type": "bank",
                "company_id": cls.company.id,
            })
        cls.wht_account = cls.env["account.account"].create({
            "name": "OD19 WHT Payable",
            "code": "999192",
            "account_type": "liability_current",
            "wht_account": True,
        })
        cls.wht_tax = cls.env["account.withholding.tax"].create({
            "name": "OD19 WHT 3%",
            "account_id": cls.wht_account.id,
            "amount": 3.0,
            "company_id": cls.company.id,
        })
        cls.vat_tax = cls.env["account.tax"].create({
            "name": "OD19 VAT 7%",
            "amount": 7.0,
            "type_tax_use": "sale",
            "company_id": cls.company.id,
        })

    def _create_payment(self, amount=1000, wht_lines=None, vat_lines=None):
        vals = {
            "partner_id": self.partner.id,
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": amount,
            "journal_id": self.bank_journal.id,
        }
        if wht_lines is not None:
            vals["od19_wht_line_ids"] = wht_lines
        if vat_lines is not None:
            vals["od19_vat_line_ids"] = vat_lines
        return self.env["account.payment"].create(vals)

    # ------------------------------------------------------------------
    # T7: WHT detail line -> journal line on the WHT account, net correct
    # ------------------------------------------------------------------
    def test_wht_line_computes_amount_and_net(self):
        payment = self._create_payment(amount=1000, wht_lines=[
            (0, 0, {"tax_id": self.wht_tax.id, "pay_amount": 1000}),
        ])
        self.assertEqual(payment.od19_wht_amount, 30.0)  # 1000 * 3%
        self.assertEqual(payment.od19_amount_net, 970.0)  # 1000 - 30

    def test_wht_line_books_on_wht_account(self):
        payment = self._create_payment(amount=1000, wht_lines=[
            (0, 0, {"tax_id": self.wht_tax.id, "pay_amount": 1000}),
        ])
        payment.action_post()
        move = payment.move_id
        wht_lines = move.line_ids.filtered(
            lambda line: line.account_id == self.wht_account
        )
        self.assertEqual(sum(wht_lines.mapped("debit")), 30.0)
        self.assertEqual(sum(wht_lines.mapped("credit")), 0.0)
        # The liquidity line only receives the net, so the entry balances.
        liquidity = move.line_ids.filtered(
            lambda line: line.account_id == payment.outstanding_account_id
        )
        self.assertEqual(sum(liquidity.mapped("debit")), 970.0)
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0, places=2)

    # ------------------------------------------------------------------
    # K9: VAT lines are detail-only and the VAT date is editable
    # ------------------------------------------------------------------
    def test_vat_not_deducted_from_net(self):
        payment = self._create_payment(amount=1000, vat_lines=[
            (0, 0, {"tax_id": self.vat_tax.id, "base_amount": 1000}),
        ])
        self.assertEqual(payment.od19_vat_amount, 70.0)  # 1000 * 7%
        self.assertEqual(payment.od19_amount_net, 1000.0)  # VAT not deducted (K9)

    def test_vat_date_is_editable(self):
        payment = self._create_payment(amount=1000, vat_lines=[
            (0, 0, {"tax_id": self.vat_tax.id, "base_amount": 1000}),
        ])
        line = payment.od19_vat_line_ids
        self.assertEqual(len(line), 1)
        self.assertTrue(line.vat_date, "VAT date defaults to today")
        line.vat_date = "2026-01-31"
        self.assertEqual(line.vat_date, fields.Date.to_date("2026-01-31"))
