# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


# ``res.partner`` carries fields made required by other installed modules (for
# instance ``group_rfq`` from ``purchase_stock``). While this module is being
# installed the registry does not carry them yet, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestPaymentFee(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.bank_journal = cls.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if not cls.bank_journal:
            cls.bank_journal = cls.env["account.journal"].create({
                "name": "Test Bank",
                "code": "TBK",
                "type": "bank",
                "company_id": cls.company.id,
            })
        cls.fee_account = cls.env["account.account"].search(
            [("account_type", "=", "expense"), ("company_ids", "in", cls.company.id)],
            limit=1,
        )
        # A WHT type to exercise the combined net (T4) and WHT booking (T7).
        cls.wht_account = cls.env["account.account"].create({
            "name": "OD19 WHT Payable",
            "code": "999191",
            "account_type": "liability_current",
            "wht_account": True,
        })
        cls.wht_tax = cls.env["account.withholding.tax"].create({
            "name": "OD19 WHT 3%",
            "account_id": cls.wht_account.id,
            "amount": 3.0,
            "company_id": cls.company.id,
        })

    def _create_payment(self, amount=1000, fee=50):
        return self.env["account.payment"].create({
            "partner_id": self.partner.id,
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": amount,
            "fee_amount": fee,
            "fee_account_id": self.fee_account.id,
            "journal_id": self.bank_journal.id,
        })

    def test_payment_fee_creates_fee_line(self):
        payment = self._create_payment(amount=1000, fee=50)
        payment.action_post()
        move = payment.move_id
        fee_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.fee_account
        )
        self.assertTrue(fee_lines, "Fee line should be created")
        self.assertEqual(sum(fee_lines.mapped("debit")), 50.0)

    def test_fee_without_account_raises(self):
        payment = self._create_payment(amount=1000, fee=50)
        payment.fee_account_id = False
        with self.assertRaises(ValidationError):
            payment.action_post()

    def test_negative_fee_raises(self):
        with self.assertRaises(ValidationError):
            self.env["account.payment"].create({
                "partner_id": self.partner.id,
                "payment_type": "inbound",
                "partner_type": "customer",
                "amount": 1000,
                "fee_amount": -50,
                "fee_account_id": self.fee_account.id,
                "journal_id": self.bank_journal.id,
            })

    def test_no_fee_normal_payment(self):
        payment = self._create_payment(amount=1000, fee=0)
        payment.action_post()
        move = payment.move_id
        fee_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.fee_account
        )
        self.assertFalse(fee_lines, "No fee line when fee is zero")

    # ------------------------------------------------------------------
    # K2/K3 detail lines: several fees, each on its own line (T6)
    # ------------------------------------------------------------------
    def _create_payment_with_fee_lines(self, amount=1000, fees=(30, 20)):
        return self.env["account.payment"].create({
            "partner_id": self.partner.id,
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": amount,
            "journal_id": self.bank_journal.id,
            "od19_fee_ids": [
                (0, 0, {
                    "name": f"Fee {i + 1}",
                    "account_id": self.fee_account.id,
                    "amount": fee_amount,
                })
                for i, fee_amount in enumerate(fees)
            ],
        })

    def test_fee_ids_multiple_lines_adjust_journal(self):
        payment = self._create_payment_with_fee_lines(amount=1000, fees=(30, 20))
        self.assertEqual(payment.od19_fee_amount, 50.0)
        payment.action_post()
        move = payment.move_id
        fee_lines = move.line_ids.filtered(
            lambda l: l.account_id == self.fee_account
        )
        self.assertEqual(sum(fee_lines.mapped("balance")), 50.0)
        liquidity = move.line_ids.filtered(
            lambda l: l.account_id == payment.outstanding_account_id
        )
        self.assertEqual(sum(liquidity.mapped("balance")), 950.0)
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0, places=2)

    def test_fee_ids_total_and_net(self):
        payment = self._create_payment_with_fee_lines(amount=1000, fees=(30, 20))
        self.assertEqual(payment.od19_fee_amount, 50.0)
        self.assertEqual(payment.od19_amount_net, 950.0)

    # ------------------------------------------------------------------
    # T4: net = amount - WHT - Fees (inbound sign)
    # ------------------------------------------------------------------
    def test_net_includes_wht_and_fees(self):
        payment = self.env["account.payment"].create({
            "partner_id": self.partner.id,
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": 1000,
            "journal_id": self.bank_journal.id,
            "od19_wht_line_ids": [
                (0, 0, {"tax_id": self.wht_tax.id, "pay_amount": 1000}),
            ],
            "od19_fee_ids": [
                (0, 0, {
                    "name": "Fee A",
                    "account_id": self.fee_account.id,
                    "amount": 30,
                }),
            ],
        })
        self.assertEqual(payment.od19_wht_amount, 30.0)  # 1000 * 3%
        self.assertEqual(payment.od19_fee_amount, 30.0)
        self.assertEqual(payment.od19_amount_net, 940.0)  # 1000 - 30 - 30
