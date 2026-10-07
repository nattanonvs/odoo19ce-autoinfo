from lxml import etree

from odoo import api
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestAccountingCashReconciliation(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.move_form_view = cls.env.ref("account.view_move_form")

    def _fresh_move(self, move):
        fresh_env = api.Environment(self.env.cr, self.env.uid, dict(self.env.context))
        return fresh_env["account.move"].browse(move.id)

    def _create_misc_entry(self, **vals):
        return self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Expense",
                            "account_id": self.company_data["default_account_expense"].id,
                            "debit": 50.0,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Revenue",
                            "account_id": self.company_data["default_account_revenue"].id,
                            "debit": 0.0,
                            "credit": 50.0,
                        },
                    ),
                ],
                **vals,
            }
        )

    def _get_move_form_arch(self):
        view_data = self.env["account.move"].get_view(
            view_id=self.move_form_view.id, view_type="form"
        )
        return etree.fromstring(view_data["arch"])

    def test_customer_invoice_moves_from_posted_to_paid(self):
        invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=100.0)
            ],
        )
        invoice = self._fresh_move(invoice)
        self.assertEqual(invoice.od19_operational_flow, "customer")
        self.assertEqual(invoice.od19_operational_closure_state, "posted")

        self._register_payment(invoice, amount=invoice.amount_total)

        invoice = self._fresh_move(invoice)
        self.assertEqual(invoice.payment_state, "paid")
        self.assertEqual(invoice.od19_operational_closure_state, "paid")

    def test_vendor_bill_can_be_partially_paid(self):
        bill = self._create_invoice(
            move_type="in_invoice",
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=200.0)
            ],
        )

        self._register_payment(bill, amount=bill.amount_total / 2)

        bill = self._fresh_move(bill)
        self.assertEqual(bill.od19_operational_flow, "vendor")
        self.assertEqual(bill.payment_state, "partial")
        self.assertEqual(bill.od19_operational_closure_state, "partially_paid")

    def test_reversed_invoice_is_treated_as_operationally_closed(self):
        invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=150.0)
            ],
        )

        self._reverse_invoice(invoice, is_modify=True, post=True)

        invoice = self._fresh_move(invoice)
        self.assertEqual(invoice.payment_state, "reversed")
        self.assertEqual(invoice.od19_operational_closure_state, "paid")

    def test_blocked_invoice_stays_open_in_operational_closure(self):
        invoice = self._create_invoice(
            move_type="out_invoice",
            partner_id=self.partner_a,
            post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=180.0)
            ],
        )

        invoice.action_toggle_block_payment()

        invoice = self._fresh_move(invoice)
        self.assertEqual(invoice.payment_state, "blocked")
        self.assertEqual(invoice.od19_operational_closure_state, "posted")

    def test_operational_flow_classifies_journal_entries_as_other(self):
        move = self._fresh_move(self._create_misc_entry(ref="MISC-FLOW-001"))
        self.assertEqual(move.od19_operational_flow, "other")

    def test_source_document_falls_back_from_origin_to_ref_to_name(self):
        invoice = self._fresh_move(
            self._create_invoice(
                move_type="out_invoice",
                partner_id=self.partner_a,
                post=True,
                invoice_origin="SO-ORIGIN-001",
                invoice_line_ids=[
                    self._prepare_invoice_line(
                        product_id=self.product_a, price_unit=120.0
                    )
                ],
            )
        )
        entry_with_ref = self._fresh_move(self._create_misc_entry(ref="MISC-REF-001"))
        entry_with_name = self._create_misc_entry()
        entry_with_name.action_post()
        entry_with_name = self._fresh_move(entry_with_name)

        self.assertEqual(invoice.od19_source_document, "SO-ORIGIN-001")
        self.assertEqual(entry_with_ref.od19_source_document, "MISC-REF-001")
        self.assertEqual(entry_with_name.od19_source_document, entry_with_name.name)

    def test_account_move_form_places_operational_fields_once(self):
        arch = self._get_move_form_arch()
        flow_fields = arch.xpath(
            "//group[@id='header_right_group']"
            "/div[@name='due_date']/following-sibling::field[@name='od19_operational_flow']"
        )
        closure_fields = arch.xpath(
            "//group[@id='header_right_group']"
            "/div[@name='due_date']/following-sibling::field[@name='od19_operational_closure_state']"
        )
        source_fields = arch.xpath(
            "//group[@id='header_right_group']"
            "/div[@name='due_date']/following-sibling::field[@name='od19_source_document']"
        )
        self.assertEqual(len(flow_fields), 1)
        self.assertEqual(len(closure_fields), 1)
        self.assertEqual(len(source_fields), 1)
