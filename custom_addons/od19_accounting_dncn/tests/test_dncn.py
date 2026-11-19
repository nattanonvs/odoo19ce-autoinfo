# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged("od19_accounting_dncn")
class TestDNCN(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.vendor = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.product = cls.env["product.product"].create({
            "name": "Test Product",
            "type": "service",
            "list_price": 100,
        })
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.purchase_journal = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.reason = cls.env["account.move.dncn.reason"].create({
            "name": "Test Reason",
        })

    def _create_vendor_bill(self, price_unit=100):
        return self.env["account.move"].create({
            "move_type": "in_invoice",
            "partner_id": self.vendor.id,
            "journal_id": self.purchase_journal.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": price_unit,
                "tax_ids": [(6, 0, [])],
            })],
        })

    def _create_invoice(self):
        return self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 100,
            })],
        })

    def test_dn_requires_reason(self):
        invoice = self._create_invoice()
        invoice.action_post()
        # Create DN without reason
        dn = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "dn",
            "parent_id": invoice.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
            })],
        })
        with self.assertRaises(ValidationError):
            dn.action_post()

    def test_dn_with_reason_posts(self):
        invoice = self._create_invoice()
        invoice.action_post()
        dn = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "dn",
            "parent_id": invoice.id,
            "reason_id": self.reason.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
            })],
        })
        dn.action_post()
        self.assertEqual(dn.state, "posted")

    def test_credit_note_creates_draft_with_copied_lines(self):
        """The button must create a Credit Note that already carries the
        original lines and links back to the source invoice."""
        invoice = self._create_invoice()
        invoice.action_post()

        action = invoice.action_create_credit_note()
        self.assertEqual(action.get("res_model"), "account.move")
        self.assertTrue(action.get("res_id"))

        cn = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(cn.move_type, "out_refund")
        self.assertEqual(cn.dncn, "cn")
        self.assertEqual(cn.parent_id, invoice)
        self.assertEqual(cn.reversed_entry_id, invoice)
        self.assertEqual(cn.invoice_origin, invoice.name)
        self.assertEqual(cn.state, "draft")
        self.assertEqual(len(cn.invoice_line_ids), 1)
        self.assertEqual(cn.invoice_line_ids.price_unit, 100)

    def test_credit_note_button_reconciles_with_parent(self):
        invoice = self._create_invoice()
        invoice.action_post()

        cn = self.env["account.move"].browse(
            invoice.action_create_credit_note()["res_id"]
        )
        cn.reason_id = self.reason.id
        cn.action_post()

        receivable = self.partner.property_account_receivable_id
        lines = (invoice.line_ids + cn.line_ids).filtered(
            lambda line: line.account_id == receivable
        )
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(lines.mapped("reconciled")))
        self.assertEqual(len(lines.mapped("full_reconcile_id")), 1)
        self.assertEqual(sum(lines.mapped("amount_residual")), 0.0)

    def test_vendor_credit_note_creates_in_refund_and_reconciles(self):
        bill = self._create_vendor_bill()
        bill.action_post()

        cn = self.env["account.move"].browse(
            bill.action_create_credit_note()["res_id"]
        )
        self.assertEqual(cn.move_type, "in_refund")
        self.assertEqual(cn.parent_id, bill)
        self.assertEqual(len(cn.invoice_line_ids), 1)

        cn.reason_id = self.reason.id
        cn.action_post()

        payable = self.vendor.property_account_payable_id
        lines = (bill.line_ids + cn.line_ids).filtered(
            lambda line: line.account_id == payable
        )
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(lines.mapped("reconciled")))
        self.assertEqual(sum(lines.mapped("amount_residual")), 0.0)

    def test_partial_credit_note_leaves_parent_residual(self):
        invoice = self._create_invoice()
        invoice.action_post()

        cn = self.env["account.move"].browse(
            invoice.action_create_credit_note()["res_id"]
        )
        cn.invoice_line_ids.write({"price_unit": 40})
        cn.reason_id = self.reason.id
        cn.action_post()

        receivable = self.partner.property_account_receivable_id
        inv_line = invoice.line_ids.filtered(
            lambda line: line.account_id == receivable
        )
        # Only part of the invoice was credited: the residual must equal the
        # difference between both totals (VAT included when applicable).
        expected = invoice.amount_total - cn.amount_total
        self.assertAlmostEqual(inv_line.amount_residual, expected, 2)

    def test_credit_note_requires_reason_before_post(self):
        invoice = self._create_invoice()
        invoice.action_post()

        cn = self.env["account.move"].browse(
            invoice.action_create_credit_note()["res_id"]
        )
        self.assertFalse(cn.reason_id)
        with self.assertRaises(ValidationError):
            cn.action_post()

    def test_remaster_invoice_copies_lines(self):
        invoice = self._create_invoice()
        invoice.action_post()
        action = invoice.action_remaster_invoice()
        remaster = self.env["account.move"].browse(action["res_id"])
        self.assertEqual(remaster.dncn, "re")
        self.assertEqual(remaster.parent_id, invoice)
        self.assertEqual(len(remaster.invoice_line_ids), 1)
        self.assertEqual(remaster.invoice_line_ids.price_unit, 100)

    def _create_credit_note(self, invoice, price_unit=100):
        return self.env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "cn",
            "parent_id": invoice.id,
            "reversed_entry_id": invoice.id,
            "reason_id": self.reason.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": price_unit,
            })],
        })

    def test_credit_note_reconciles_with_parent(self):
        invoice = self._create_invoice()
        invoice.action_post()
        cn = self._create_credit_note(invoice)

        cn.action_post()

        receivable = self.partner.property_account_receivable_id
        lines = (invoice.line_ids + cn.line_ids).filtered(
            lambda line: line.account_id == receivable
        )
        self.assertEqual(len(lines), 2)
        self.assertTrue(all(lines.mapped("reconciled")))
        self.assertEqual(len(lines.mapped("full_reconcile_id")), 1)
        self.assertEqual(sum(lines.mapped("amount_residual")), 0.0)

    def test_debit_note_does_not_settle_parent(self):
        invoice = self._create_invoice()
        invoice.action_post()
        dn = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.journal.id,
            "dncn": "dn",
            "parent_id": invoice.id,
            "reason_id": self.reason.id,
            "invoice_line_ids": [(0, 0, {
                "product_id": self.product.id,
                "quantity": 1,
                "price_unit": 50,
            })],
        })

        dn.action_post()

        receivable = self.partner.property_account_receivable_id
        dn_line = dn.line_ids.filtered(lambda line: line.account_id == receivable)
        self.assertFalse(dn_line.reconciled)
