from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCheque(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "Test Customer", "is_company": True}
        )
        cls.supplier = cls.env["res.partner"].create(
            {"name": "Test Supplier", "is_company": True}
        )
        cls.bank = cls.env["res.bank"].create(
            {"name": "Test Bank"}
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111001",
                "account_type": "asset_cash",
            }
        )
        cls.cheque_receivable_account = cls.env["account.account"].create(
            {
                "name": "Cheque Receivable",
                "code": "112001",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.cheque_payable_account = cls.env["account.account"].create(
            {
                "name": "Cheque Payable",
                "code": "212001",
                "account_type": "liability_current",
            }
        )
        cls.bank_journal = cls.env["account.journal"].create(
            {
                "name": "Cheque Bank",
                "code": "CHQB",
                "type": "bank",
                "company_id": cls.env.company.id,
                "default_account_id": cls.cash_account.id,
            }
        )
        cls.env.company.write(
            {
                "cheque_received_account_id": cls.cheque_receivable_account.id,
                "cheque_paid_account_id": cls.cheque_payable_account.id,
            }
        )

    def test_create_customer_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ001",
            }
        )
        self.assertEqual(cheque.state, "draft")
        self.assertEqual(cheque.cheque_type, "customer")

    def test_create_supplier_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "supplier",
                "partner_id": self.supplier.id,
                "bank_id": self.bank.id,
                "amount": 50000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ002",
            }
        )
        self.assertEqual(cheque.state, "draft")

    def test_cheque_requires_positive_amount(self):
        with self.assertRaises(ValidationError):
            self.env["account.cheque"].create(
                {
                    "cheque_type": "customer",
                    "partner_id": self.customer.id,
                    "bank_id": self.bank.id,
                    "amount": -100.0,
                    "cheque_date": "2024-01-15",
                    "due_date": "2024-02-15",
                    "name": "CHQ003",
                }
            )

    def test_cheque_due_date_after_cheque_date(self):
        with self.assertRaises(ValidationError):
            self.env["account.cheque"].create(
                {
                    "cheque_type": "customer",
                    "partner_id": self.customer.id,
                    "bank_id": self.bank.id,
                    "amount": 100000.0,
                    "cheque_date": "2024-02-15",
                    "due_date": "2024-01-15",
                    "name": "CHQ004",
                }
            )

    def test_confirm_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ005",
            }
        )
        cheque.action_confirm()
        self.assertEqual(cheque.state, "confirmed")

    def test_deposit_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ006",
            }
        )
        cheque.action_confirm()
        cheque.action_deposit()
        self.assertEqual(cheque.state, "deposited")

    def test_clear_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ007",
            }
        )
        cheque.action_confirm()
        cheque.action_deposit()
        cheque.action_clear()
        self.assertEqual(cheque.state, "cleared")

    def test_bounce_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ008",
            }
        )
        cheque.action_confirm()
        cheque.action_bounce()
        self.assertEqual(cheque.state, "bounced")

    def test_cancel_cheque(self):
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 100000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQ009",
            }
        )
        cheque.action_confirm()
        cheque.action_cancel()
        self.assertEqual(cheque.state, "cancelled")

    def _create_reconcile_account(self, name, code, account_type):
        return self.env["account.account"].create(
            {"name": name, "code": code, "account_type": account_type}
        )

    def _create_open_invoice(self, partner, amount):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "invoice_date": "2024-01-10",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Service",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self._create_reconcile_account(
                                "Test Income", "611001", "income"
                            ).id,
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _create_open_bill(self, partner, amount):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": "2024-01-10",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Service",
                            "quantity": 1.0,
                            "price_unit": amount,
                            "account_id": self._create_reconcile_account(
                                "Test Expense", "511001", "expense"
                            ).id,
                        },
                    )
                ],
            }
        )
        bill.action_post()
        return bill

    def _create_customer_cheque(self, amount, name):
        return self.env["account.cheque"].create(
            {
                "cheque_type": "customer",
                "partner_id": self.customer.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": amount,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": name,
            }
        )

    def test_action_reconcile_customer_cheque_with_invoice(self):
        invoice = self._create_open_invoice(self.customer, 100000.0)
        cheque = self._create_customer_cheque(100000.0, "CHQR01")
        cheque.action_confirm()

        cheque.action_reconcile()

        ar_line = invoice.line_ids.filtered(
            lambda line: line.account_id
            == self.customer.property_account_receivable_id
        )
        self.assertTrue(ar_line.reconciled)
        self.assertEqual(ar_line.amount_residual, 0.0)

    def test_action_reconcile_supplier_cheque_with_bill(self):
        bill = self._create_open_bill(self.supplier, 50000.0)
        cheque = self.env["account.cheque"].create(
            {
                "cheque_type": "supplier",
                "partner_id": self.supplier.id,
                "bank_id": self.bank.id,
                "journal_id": self.bank_journal.id,
                "amount": 50000.0,
                "cheque_date": "2024-01-15",
                "due_date": "2024-02-15",
                "name": "CHQR02",
            }
        )
        cheque.action_confirm()
        cheque.action_to_pay()

        cheque.action_reconcile()

        ap_line = bill.line_ids.filtered(
            lambda line: line.account_id
            == self.supplier.property_account_payable_id
        )
        self.assertTrue(ap_line.reconciled)
        self.assertEqual(ap_line.amount_residual, 0.0)

    def _get_cheque_method_line(self):
        method = self.env.ref(
            "od19_accounting_cheque.payment_method_od19_cheque"
        )
        method_line = self.bank_journal.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == method
        )[:1]
        if not method_line:
            method_line = self.env["account.payment.method.line"].create({
                "name": method.name,
                "payment_method_id": method.id,
                "journal_id": self.bank_journal.id,
            })
        return method_line

    def test_cheque_payment_method_uses_received_account(self):
        """The cheque receipt payment methods park money on Cheque Received."""
        method_line = self._get_cheque_method_line()
        payment = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.customer.id,
            "journal_id": self.bank_journal.id,
            "amount": 100000.0,
            "payment_method_line_id": method_line.id,
        })
        self.assertEqual(payment.outstanding_account_id, self.cheque_receivable_account)

    def test_receive_customer_cheque_through_payment(self):
        """Receiving a customer cheque creates an account.payment posting
        Dr Cheque Received / Cr Accounts Receivable."""
        cheque = self._create_customer_cheque(100000.0, "CHQP01")
        cheque.action_register_payment()

        self.assertEqual(cheque.state, "confirmed")
        self.assertTrue(cheque.payment_id)
        self.assertEqual(cheque.payment_id.payment_method_code, "od19_cheque")
        self.assertEqual(cheque.payment_id.state, "in_process")
        self.assertTrue(cheque.received_move_id)

        move = cheque.received_move_id
        liquidity = move.line_ids.filtered(
            lambda line: line.account_id == self.cheque_receivable_account
        )
        self.assertEqual(sum(liquidity.mapped("debit")), 100000.0)
        receivable = move.line_ids.filtered(
            lambda line: line.account_id
            == self.customer.property_account_receivable_id
        )
        self.assertEqual(sum(receivable.mapped("credit")), 100000.0)

    def test_deposit_received_cheque_through_payment(self):
        """Depositing a cheque received through a payment creates a second
        payment posting Dr Bank / Cr Cheque Received and clears the account."""
        cheque = self._create_customer_cheque(100000.0, "CHQP02")
        cheque.action_register_payment()
        cheque.action_deposit()

        self.assertEqual(cheque.state, "deposited")
        self.assertTrue(cheque.deposit_payment_id)
        self.assertTrue(cheque.deposited_move_id)

        move = cheque.deposited_move_id
        bank_line = move.line_ids.filtered(
            lambda line: line.account_id == self.cash_account
        )
        self.assertEqual(sum(bank_line.mapped("debit")), 100000.0)
        credit_line = move.line_ids.filtered(
            lambda line: line.account_id == self.cheque_receivable_account
        )
        self.assertEqual(sum(credit_line.mapped("credit")), 100000.0)

        # The two Cheque Received lines are reconciled, leaving a zero balance.
        received_line = cheque.received_move_id.line_ids.filtered(
            lambda line: line.account_id == self.cheque_receivable_account
        )
        self.assertEqual(received_line.amount_residual, 0.0)

    # ------------------------------------------------------------------
    # T5: several collecting cheques make up one receipt (F9/R6)
    # ------------------------------------------------------------------
    def test_collecting_cheques_total(self):
        payment = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.customer.id,
            "journal_id": self.bank_journal.id,
            "amount": 350.0,
            "od19_cheque_collect_ids": [
                (0, 0, {
                    "name": "CHQC01",
                    "bank_id": self.bank.id,
                    "amount": 100.0,
                    "journal_id": self.bank_journal.id,
                }),
                (0, 0, {
                    "name": "CHQC02",
                    "bank_id": self.bank.id,
                    "amount": 250.0,
                    "journal_id": self.bank_journal.id,
                }),
            ],
        })
        self.assertEqual(len(payment.od19_cheque_collect_ids), 2)
        self.assertEqual(payment.od19_cheque_collect_amount, 350.0)
