# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the e-Withholding Tax (e-WHT) submission channel.

Covered: the mockable bank gateway adapter, the submission state machine, the
retry history and the company switch that guards the feature.
"""

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..lib import ewht_gateway

ENDPOINT = "https://ewht.bank.example/api"
PROVIDER_ID = "TEST-BANK-PROVIDER"


@tagged("post_install", "-at_install")
class TestOd19EwhtSubmission(TransactionCase):
    """Basic tests for the e-Withholding Tax submission flow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write(
            {
                "od19_ewht_enabled": True,
                "od19_ewht_mode": "mock",
                "od19_ewht_endpoint": ENDPOINT,
                "od19_ewht_provider_id": PROVIDER_ID,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "e-WHT Vendor Test",
                "vat": "0105558000014",
            }
        )
        cls.wht_account = cls.env["account.account"].create(
            {
                "code": "X992001",
                "name": "WHT Payable e-WHT Test",
                "account_type": "asset_current",
                "wht_account": True,
            }
        )
        cls.base_account = cls.env["account.account"].create(
            {
                "code": "X992002",
                "name": "e-WHT Base Test",
                "account_type": "expense",
            }
        )
        cls.wht_tax = cls.env["account.withholding.tax"].create(
            {
                "name": "WHT e-WHT Test 3%",
                "account_id": cls.wht_account.id,
                "amount": 3.0,
            }
        )

    def setUp(self):
        super().setUp()
        # Every test starts from a fully configured mock channel.
        self.company.write(
            {
                "od19_ewht_enabled": True,
                "od19_ewht_mode": "mock",
                "od19_ewht_endpoint": ENDPOINT,
                "od19_ewht_provider_id": PROVIDER_ID,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_wht_move(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Base",
                            "debit": 1000.0,
                            "account_id": self.base_account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "WHT",
                            "credit": 1000.0,
                            "account_id": self.wht_account.id,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        return self.env["account.withholding.move"].create(
            {
                "move_id": move.id,
                "partner_id": self.partner.id,
                "amount_income": 1000.0,
                "amount_wht": 30.0,
                "wht_tax_id": self.wht_tax.id,
                "company_id": self.company.id,
            }
        )

    def _create_submission(self, *wht_moves):
        return self.env["od19.ewht.submission"].create(
            {
                "company_id": self.company.id,
                "move_ids": [(6, 0, [m.id for m in wht_moves])],
            }
        )

    # ------------------------------------------------------------------
    # Gateway adapter
    # ------------------------------------------------------------------
    def test_gateway_selection(self):
        self.assertIsInstance(
            ewht_gateway.get_gateway(self.company), ewht_gateway.MockEwhtGateway
        )
        self.company.od19_ewht_mode = "live"
        self.assertIsInstance(
            ewht_gateway.get_gateway(self.company), ewht_gateway.LiveEwhtGateway
        )

    def test_mock_gateway_accepts_wht_move(self):
        wht_move = self._create_wht_move()
        response = ewht_gateway.get_gateway(self.company).submit(wht_move)
        self.assertEqual(response["response_code"], "0")
        self.assertTrue(response["ref"].startswith("MOCK-EWHT-%s-" % wht_move.id))

    # ------------------------------------------------------------------
    # Submission flow
    # ------------------------------------------------------------------
    def test_submission_is_accepted(self):
        wht_move = self._create_wht_move()
        submission = self._create_submission(wht_move)
        self.assertTrue(submission.name.startswith("EWHT/"))
        submission.action_submit()
        self.assertEqual(submission.state, "accepted")
        self.assertEqual(submission.channel, "mock")
        self.assertEqual(submission.attempt_count, 1)
        self.assertEqual(submission.response_code, "0")
        self.assertTrue(submission.reference.startswith("MOCK-EWHT-"))
        self.assertIn(wht_move, submission.move_ids)

    def test_missing_endpoint_marks_submission_failed(self):
        self.company.od19_ewht_endpoint = False
        wht_move = self._create_wht_move()
        submission = self._create_submission(wht_move)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")
        self.assertEqual(submission.attempt_count, 1)
        self.assertIn("Endpoint", submission.response_message)

    def test_missing_provider_id_marks_submission_failed(self):
        self.company.od19_ewht_provider_id = False
        wht_move = self._create_wht_move()
        submission = self._create_submission(wht_move)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")
        self.assertIn("Provider", submission.response_message)

    def test_live_channel_is_not_implemented_yet(self):
        self.company.od19_ewht_mode = "live"
        wht_move = self._create_wht_move()
        submission = self._create_submission(wht_move)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")
        self.assertEqual(submission.channel, "live")
        self.assertIn("ยังไม่รองรับ", submission.response_message)

    def test_retry_resends_failed_submission(self):
        self.company.od19_ewht_endpoint = False
        wht_move = self._create_wht_move()
        submission = self._create_submission(wht_move)
        submission.action_submit()
        self.assertEqual(submission.state, "failed")

        self.company.od19_ewht_endpoint = ENDPOINT
        submission.action_retry()
        self.assertEqual(submission.state, "accepted")
        self.assertEqual(submission.attempt_count, 2)

    def test_submission_requires_records(self):
        submission = self.env["od19.ewht.submission"].create(
            {"company_id": self.company.id}
        )
        with self.assertRaises(UserError):
            submission.action_submit()

    def test_disabled_company_blocks_filing(self):
        wht_move = self._create_wht_move()
        submission = self._create_submission(wht_move)
        self.company.od19_ewht_enabled = False
        with self.assertRaises(UserError):
            submission.action_submit()
