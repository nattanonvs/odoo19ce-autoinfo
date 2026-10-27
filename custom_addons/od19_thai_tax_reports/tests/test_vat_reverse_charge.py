# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Tests for Section 83/6 - reverse charge VAT self-assessment (ภ.พ.36)."""
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestVatReverseCharge(TransactionCase):
    """Cover the PP36 reverse-charge tax, its repartition lines and the report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.tax = cls.env.ref(
            "od19_thai_tax_reports.tax_input_vat_reverse_charge"
        )
        cls.tax_group = cls.env.ref("od19_thai_tax_reports.tax_group_vat_pp36")
        # Make sure the repartition lines are built even if the module was
        # installed before the company's Thai chart of accounts was loaded.
        cls.env["account.tax"]._od19_setup_reverse_charge_taxes()
        cls.tax.invalidate_recordset()

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Foreign Service Provider",
                "company_type": "company",
                "vat": "FR12345678901",
            }
        )
        cls.expense_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls._seq = 0

    def _create_bill(self, amount=1000.0):
        self.__class__._seq += 1
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.from_string("2026-02-15"),
                "ref": "INV-FOREIGN-%03d" % self.__class__._seq,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Overseas service (reverse charge)",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.expense_account.id,
                            "tax_ids": [(6, 0, [self.tax.id])],
                        },
                    )
                ],
            }
        )

    def _post_bill(self, bill):
        unique = "TEST-PP36-%03d" % self.__class__._seq
        if "tax_invoice_ids" in bill._fields:
            bill.tax_invoice_ids.write(
                {
                    "tax_invoice_number": unique,
                    "tax_invoice_date": bill.invoice_date or fields.Date.today(),
                }
            )
        bill.action_post()
        return bill

    def _tax_lines(self, bill):
        return bill.line_ids.filtered(
            lambda line: line.tax_repartition_line_id
            and line.tax_repartition_line_id.tax_id == self.tax
        )

    # ------------------------------------------------------------------
    # Tax configuration
    # ------------------------------------------------------------------
    def test_reverse_charge_tax_configuration(self):
        tax = self.tax
        self.assertEqual(tax.type_tax_use, "purchase")
        self.assertEqual(tax.amount_type, "percent")
        self.assertEqual(tax.amount, 7.0)
        self.assertEqual(tax.tax_group_id, self.tax_group)
        self.assertTrue(tax.has_negative_factor)

    def test_repartition_lines_are_reverse_charge(self):
        """base (100) + tax (+100) + tax (-100) with both accounts set."""
        repartition = self.tax.invoice_repartition_line_ids
        self.assertEqual(
            len(repartition.filtered(lambda r: r.repartition_type == "base")), 1
        )
        tax_reps = repartition.filtered(lambda r: r.repartition_type == "tax")
        self.assertEqual(len(tax_reps), 2)

        positive = tax_reps.filtered(lambda r: r.factor_percent > 0.0)
        negative = tax_reps.filtered(lambda r: r.factor_percent < 0.0)
        self.assertEqual(len(positive), 1)
        self.assertEqual(len(negative), 1)
        self.assertEqual(positive.factor_percent, 100.0)
        self.assertEqual(negative.factor_percent, -100.0)
        self.assertTrue(positive.account_id)
        self.assertTrue(negative.account_id)
        self.assertNotEqual(positive.account_id, negative.account_id)

        # ภาษีขาย (output) และภาษีซื้อ (input) ของผังบัญชีไทย
        self.assertEqual(positive.account_id.code, "213200")
        self.assertEqual(negative.account_id.code, "114200")

        # refund side must mirror the invoice side
        refund_repartition = self.tax.refund_repartition_line_ids
        self.assertEqual(
            len(refund_repartition.filtered(lambda r: r.repartition_type == "base")), 1
        )
        refund_tax_reps = refund_repartition.filtered(
            lambda r: r.repartition_type == "tax"
        )
        self.assertEqual(len(refund_tax_reps), 2)
        self.assertEqual(
            sorted(refund_tax_reps.mapped("factor_percent")), sorted([100.0, -100.0])
        )

    # ------------------------------------------------------------------
    # Accounting impact
    # ------------------------------------------------------------------
    def test_posted_bill_self_assesses_both_vat_sides(self):
        bill = self._create_bill(amount=1000.0)
        tax_lines = self._tax_lines(bill)
        output_line = tax_lines.filtered(
            lambda line: line.tax_repartition_line_id.factor_percent > 0.0
        )
        input_line = tax_lines.filtered(
            lambda line: line.tax_repartition_line_id.factor_percent < 0.0
        )

        self.assertTrue(output_line, "Expected a self-assessed output VAT line")
        self.assertTrue(input_line, "Expected a claimable input VAT line")
        # not posted yet: check the tax line amounts computed on the fly
        self.assertAlmostEqual(abs(output_line.balance), 70.0, 2)
        self.assertAlmostEqual(abs(input_line.balance), 70.0, 2)

        self._post_bill(bill)
        self.tax.invalidate_recordset()

        # ยอดรวมเอกสารไม่เปลี่ยน เพราะภาษีขาย/ภาษีซื้อหักกลบกัน
        self.assertAlmostEqual(bill.amount_untaxed, 1000.0, 2)
        self.assertAlmostEqual(bill.amount_tax, 0.0, 2)
        self.assertAlmostEqual(bill.amount_total, 1000.0, 2)

        output_line = self._tax_lines(bill).filtered(
            lambda line: line.tax_repartition_line_id.factor_percent > 0.0
        )
        input_line = self._tax_lines(bill).filtered(
            lambda line: line.tax_repartition_line_id.factor_percent < 0.0
        )
        self.assertAlmostEqual(abs(output_line.balance), 70.0, 2)
        self.assertAlmostEqual(abs(input_line.balance), 70.0, 2)
        self.assertEqual(output_line.account_id.code, "213200")
        self.assertEqual(input_line.account_id.code, "114200")

    # ------------------------------------------------------------------
    # PP36 register
    # ------------------------------------------------------------------
    def test_pp36_report_lists_reverse_charge_bills(self):
        bill = self._create_bill(amount=2000.0)
        self._post_bill(bill)

        values = (
            self.env["report.od19_thai_tax_reports.pp36_register"]
            .with_context(
                date_from="2026-02-01",
                date_to="2026-02-28",
                company_id=self.company.id,
            )
            ._get_report_values(bill.ids)
        )
        row = next(
            (line for line in values["lines"] if line["name"] == bill.name), None
        )
        self.assertTrue(row, "The reverse-charge bill must appear in the PP36 report")
        self.assertAlmostEqual(row["tax_base"], 2000.0, 2)
        self.assertAlmostEqual(row["vat_amount"], 140.0, 2)
        self.assertGreaterEqual(values["total_vat_amount"], 140.0)

    def test_pp36_report_ignores_regular_bills(self):
        standard_tax = self.env["account.tax"].create(
            {
                "name": "Test Standard Input VAT 7%",
                "amount_type": "percent",
                "amount": 7.0,
                "type_tax_use": "purchase",
                "company_id": self.company.id,
            }
        )
        self.__class__._seq += 1
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.from_string("2026-02-16"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Regular local purchase",
                            "quantity": 1.0,
                            "price_unit": 500.0,
                            "account_id": self.expense_account.id,
                            "tax_ids": [(6, 0, [standard_tax.id])],
                        },
                    )
                ],
            }
        )
        self._post_bill(bill)

        values = (
            self.env["report.od19_thai_tax_reports.pp36_register"]
            .with_context(
                date_from="2026-02-01",
                date_to="2026-02-28",
                company_id=self.company.id,
            )
            ._get_report_values(bill.ids)
        )
        names = [line["name"] for line in values["lines"]]
        self.assertNotIn(bill.name, names)
