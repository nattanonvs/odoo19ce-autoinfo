from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestBringForward(TransactionCase):
    """Tests for the bring forward (ยกยอดปิดงวด) workflow.

    Acceptance criteria:

    * a bring forward document receives its number from the
      ``account.bring.forward`` sequence;
    * the Chart of Accounts tab is pre-filled with every account of the
      company;
    * ``action_compute`` aggregates the debit/credit of the linked posted
      documents into the matching chart lines (manual mode);
    * ``action_gather`` links the posted documents of the period
      (automatic mode);
    * ``action_post`` creates a balanced journal entry for the difference
      between the target totals and the computed amounts.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bring Forward Journal TEST",
                "code": "BFT",
                "type": "general",
            }
        )
        cls.company.bring_forward_journal_id = cls.journal

        # A pair of accounts used to build a balanced posted entry.
        cls.debit_account = cls.env["account.account"].create(
            {
                "name": "Bring Forward Debit TEST",
                "code": "599901",
                "account_type": "expense",
            }
        )
        cls.credit_account = cls.env["account.account"].create(
            {
                "name": "Bring Forward Credit TEST",
                "code": "299901",
                "account_type": "liability_current",
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_bring_forward(self, **vals):
        values = {"journal_id": self.journal.id, "company_id": self.company.id}
        values.update(vals)
        return self.env["od19.bring.forward"].create(values)

    def _line_for(self, bring_forward, account):
        lines = bring_forward.line_ids.filtered(lambda l: l.account_id == account)
        self.assertEqual(len(lines), 1, "expected exactly one chart line per account")
        return lines

    def _create_posted_move(self, debit=500.0, credit=500.0):
        move = self.env["account.move"].create(
            {
                "journal_id": self.journal.id,
                "date": self.company_bring_forward_date(),
                "line_ids": [
                    Command.create(
                        {"account_id": self.debit_account.id, "debit": debit, "credit": 0.0}
                    ),
                    Command.create(
                        {"account_id": self.credit_account.id, "debit": 0.0, "credit": credit}
                    ),
                ],
            }
        )
        move.action_post()
        self.assertEqual(move.state, "posted")
        return move

    @staticmethod
    def company_bring_forward_date():
        return "2026-01-15"

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_document_number_from_sequence(self):
        bf = self._create_bring_forward()
        self.assertNotEqual(bf.doc_no, "New")
        self.assertTrue(bf.doc_no)

    def test_default_lines_prefilled_with_company_accounts(self):
        bf = self._create_bring_forward()
        # Both accounts created for the company must be present.
        self.assertTrue(bf.line_ids.filtered(lambda l: l.account_id == self.debit_account))
        self.assertTrue(bf.line_ids.filtered(lambda l: l.account_id == self.credit_account))
        # Default lines are marked as non manually created.
        self.assertFalse(bf.line_ids[0].is_create_manual)

    def test_manual_compute_aggregates_linked_documents(self):
        bf = self._create_bring_forward(mode="manual")
        move = self._create_posted_move()
        move.od19_customer_bf_id = bf.id

        bf.action_compute()

        self.assertEqual(bf.state, "computed")
        self.assertAlmostEqual(self._line_for(bf, self.debit_account).compute_debit, 500.0)
        self.assertAlmostEqual(self._line_for(bf, self.credit_account).compute_credit, 500.0)

    def test_auto_gather_links_period_documents(self):
        bf = self._create_bring_forward(
            mode="auto", date_from="2026-01-01", date_to="2026-01-31"
        )
        partner = self.env["res.partner"].create({"name": "BF Test Customer"})
        sale_journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.company.id)], limit=1
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": sale_journal.id,
                "invoice_date": self.company_bring_forward_date(),
                "date": self.company_bring_forward_date(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "BF Test Line",
                            "quantity": 1,
                            "price_unit": 250.0,
                            "account_id": self.credit_account.id,
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        bf.action_gather()

        self.assertIn(invoice, bf.customer_invoice_ids)
        self.assertEqual(invoice.od19_customer_bf_id, bf)
        self.assertGreaterEqual(bf.customer_invoice_count, 1)

    def test_auto_gather_requires_period(self):
        bf = self._create_bring_forward(mode="auto")
        with self.assertRaises(UserError):
            bf.action_gather()

    def test_post_creates_balanced_journal_entry(self):
        bf = self._create_bring_forward(mode="manual")
        move = self._create_posted_move(debit=500.0, credit=500.0)
        move.od19_customer_bf_id = bf.id
        bf.action_compute()

        # Ask for an extra 100 on both sides so the entry is balanced and
        # non-empty.
        self._line_for(bf, self.debit_account).target_total_debit = 600.0
        self._line_for(bf, self.credit_account).target_total_credit = 600.0

        bf.action_post()

        self.assertEqual(bf.state, "posted")
        self.assertTrue(bf.move_id)
        self.assertEqual(bf.move_id.state, "posted")
        self.assertAlmostEqual(sum(bf.move_id.line_ids.mapped("debit")), 100.0)
        self.assertAlmostEqual(sum(bf.move_id.line_ids.mapped("credit")), 100.0)

    def test_post_requires_balanced_difference(self):
        bf = self._create_bring_forward(mode="manual")
        move = self._create_posted_move(debit=500.0, credit=500.0)
        move.od19_customer_bf_id = bf.id
        bf.action_compute()

        # Unbalanced target: only the debit side gets an extra amount.
        self._line_for(bf, self.debit_account).target_total_debit = 600.0

        with self.assertRaises(ValidationError):
            bf._validate_post()
