# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Tests for Section 82/5 - non-deductible input VAT (ภาษีซื้อต้องห้าม)."""
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestVatNonDeductible(TransactionCase):
    """Cover the non-deductible input VAT tax, the line flag and the report."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.non_deductible_tax = cls.env.ref(
            "od19_thai_tax_reports.tax_input_vat_non_deductible"
        )
        cls.non_deductible_group = cls.env.ref(
            "od19_thai_tax_reports.tax_group_vat_non_deductible"
        )
        # A stand-in for the standard deductible input VAT so the onchange
        # can be exercised without depending on the localization data.
        cls.standard_tax = cls.env["account.tax"].create(
            {
                "name": "Test Input VAT 7%",
                "amount_type": "percent",
                "amount": 7.0,
                "type_tax_use": "purchase",
                "company_id": cls.company.id,
            }
        )
        cls.company.account_purchase_tax_id = cls.standard_tax
        cls.partner = cls.env["res.partner"].create(
            {"name": "Non-Deductible Vendor", "company_type": "company"}
        )
        cls.expense_account = cls.env["account.account"].search(
            [
                ("account_type", "=", "expense"),
                ("company_ids", "in", cls.company.id),
            ],
            limit=1,
        )
        cls._seq = 0

    def _create_bill(self, taxes=None, amount=1000.0):
        self.__class__._seq += 1
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.from_string("2026-01-15"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Entertainment / non-deductible expense",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self.expense_account.id,
                            "tax_ids": [(6, 0, [tax.id for tax in (taxes or [])])],
                        },
                    )
                ],
            }
        )

    def _post_bill(self, bill):
        unique = "TEST-NONDUCT-%03d" % self.__class__._seq
        if "tax_invoice_ids" in bill._fields:
            bill.tax_invoice_ids.write(
                {
                    "tax_invoice_number": unique,
                    "tax_invoice_date": bill.invoice_date or fields.Date.today(),
                }
            )
        bill.action_post()
        return bill

    # ------------------------------------------------------------------
    # Tax configuration
    # ------------------------------------------------------------------
    def test_non_deductible_tax_configuration(self):
        tax = self.non_deductible_tax
        self.assertEqual(tax.type_tax_use, "purchase")
        self.assertEqual(tax.amount_type, "percent")
        self.assertEqual(tax.amount, 7.0)
        self.assertEqual(tax.tax_group_id, self.non_deductible_group)

    def test_non_deductible_tax_has_no_target_account_or_tag(self):
        """The VAT must be capitalised on the base line (expense) and never
        reported as a claimable input VAT, so no repartition account and no
        tax tag may be configured."""
        tax = self.non_deductible_tax
        for rep in tax.invoice_repartition_line_ids | tax.refund_repartition_line_ids:
            self.assertFalse(rep.account_id)
        tax_reps = tax.invoice_repartition_line_ids.filtered(
            lambda rep: rep.repartition_type == "tax"
        )
        self.assertTrue(tax_reps)
        self.assertFalse(tax_reps.tag_ids)

    # ------------------------------------------------------------------
    # Line flag
    # ------------------------------------------------------------------
    def test_flag_false_when_non_deductible_tax_used(self):
        bill = self._create_bill(taxes=[self.non_deductible_tax])
        self.assertFalse(bill.invoice_line_ids[:1].od19_vat_deductible)

    def test_flag_true_with_standard_tax(self):
        bill = self._create_bill(taxes=[self.standard_tax])
        self.assertTrue(bill.invoice_line_ids[:1].od19_vat_deductible)

    def test_flag_true_without_tax(self):
        bill = self._create_bill(taxes=[])
        self.assertTrue(bill.invoice_line_ids[:1].od19_vat_deductible)

    def test_onchange_swaps_tax_both_ways(self):
        bill = self._create_bill(taxes=[self.standard_tax])
        line = bill.invoice_line_ids[:1]
        self.assertTrue(line.od19_vat_deductible)

        line.od19_vat_deductible = False
        line._onchange_od19_vat_deductible()
        self.assertEqual(line.tax_ids, self.non_deductible_tax)

        line.od19_vat_deductible = True
        line._onchange_od19_vat_deductible()
        self.assertEqual(line.tax_ids, self.standard_tax)

    # ------------------------------------------------------------------
    # Accounting impact
    # ------------------------------------------------------------------
    def test_posted_vat_is_capitalised_on_the_expense_account(self):
        bill = self._create_bill(taxes=[self.non_deductible_tax], amount=1000.0)
        base_line = bill.invoice_line_ids[:1]
        self._post_bill(bill)

        tax_lines = bill.line_ids.filtered(
            lambda line: line.tax_line_id == self.non_deductible_tax
        )
        self.assertEqual(len(tax_lines), 1)
        self.assertEqual(tax_lines.account_id, base_line.account_id)
        self.assertAlmostEqual(tax_lines.balance, 70.0, 2)
        self.assertAlmostEqual(bill.amount_total, 1070.0, 2)

    # ------------------------------------------------------------------
    # VAT Purchase Register
    # ------------------------------------------------------------------
    def test_report_separates_non_deductible_amount(self):
        bill = self._create_bill(taxes=[self.non_deductible_tax], amount=1000.0)
        self._post_bill(bill)

        values = (
            self.env["report.od19_thai_tax_reports.vat_purchase_register"]
            .with_context(
                date_from="2026-01-01",
                date_to="2026-01-31",
                company_id=self.company.id,
            )
            ._get_report_values(bill.ids)
        )
        row = next(
            (line for line in values["lines"] if line["name"] == bill.name), None
        )
        self.assertTrue(row, "The posted bill must appear in the purchase register")
        self.assertAlmostEqual(row["non_deductible_amount"], 70.0, 2)
        self.assertAlmostEqual(row["tax_amount"], 0.0, 2)
        self.assertAlmostEqual(row["amount_total"], 1070.0, 2)
        self.assertGreaterEqual(values["total_non_deductible_amount"], 70.0)
