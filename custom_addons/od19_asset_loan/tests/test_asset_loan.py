from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestAssetLoan(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Loan = cls.env["asset.loan"]
        cls.Line = cls.env["asset.loan.line"]
        cls.Equipment = cls.env["maintenance.equipment"]
        cls.Partner = cls.env["res.partner"]

        cls.partner = cls.env.company.partner_id
        cls.equipment = cls.Equipment.create(
            {
                "name": "Test Laptop",
                "category_id": cls.env["maintenance.equipment.category"]
                .create({"name": "Test Category"})
                .id,
            }
        )

    def _create_loan(self, **overrides):
        vals = {
            "borrower_id": self.partner.id,
            "loan_date": fields.Date.today(),
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "equipment_id": self.equipment.id,
                        "quantity": 1,
                    },
                )
            ],
        }
        vals.update(overrides)
        return self.Loan.create(vals)

    # ------------------------------------------------------------------
    # Basic flow
    # ------------------------------------------------------------------
    def test_create_loan_defaults_to_draft(self):
        loan = self._create_loan()
        self.assertEqual(loan.state, "draft")

    def test_sequence_generated(self):
        loan = self._create_loan()
        self.assertTrue(loan.name)
        self.assertNotEqual(loan.name, "New")

    def test_confirm_without_lines_raises(self):
        loan = self.Loan.create(
            {
                "borrower_id": self.partner.id,
                "loan_date": fields.Date.today(),
            }
        )
        with self.assertRaises(UserError):
            loan.action_confirm()

    def test_confirm_sets_borrowed(self):
        loan = self._create_loan()
        loan.action_confirm()
        self.assertEqual(loan.state, "borrowed")
        self.assertEqual(loan.line_ids.state, "borrowed")

    def test_return_sets_returned(self):
        loan = self._create_loan()
        loan.action_confirm()
        loan.action_return()
        self.assertEqual(loan.state, "returned")
        self.assertTrue(loan.actual_return_date)
        self.assertEqual(loan.line_ids.returned_quantity, 1)

    def test_lost_sets_lost(self):
        loan = self._create_loan()
        loan.action_confirm()
        loan.action_lost()
        self.assertEqual(loan.state, "lost")

    def test_cancel_sets_cancelled(self):
        loan = self._create_loan()
        loan.action_cancel()
        self.assertEqual(loan.state, "cancelled")

    def test_cancel_then_draft(self):
        loan = self._create_loan()
        loan.action_cancel()
        loan.action_draft()
        self.assertEqual(loan.state, "draft")

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    def test_expected_return_before_loan_raises(self):
        with self.assertRaises(UserError):
            self._create_loan(
                loan_date=fields.Date.today(),
                expected_return_date=fields.Date.today() - timedelta(days=1),
            )

    def test_quantity_zero_raises(self):
        with self.assertRaises(UserError):
            self._create_loan(
                line_ids=[(0, 0, {"equipment_id": self.equipment.id, "quantity": 0})]
            )

    def test_returned_quantity_exceeds_raises(self):
        loan = self._create_loan()
        line = loan.line_ids
        with self.assertRaises(UserError):
            line.returned_quantity = 2

    # ------------------------------------------------------------------
    # Equipment link
    # ------------------------------------------------------------------
    def test_equipment_loan_count(self):
        loan = self._create_loan()
        loan.action_confirm()
        self.assertEqual(self.equipment.loan_count, 1)

    def test_equipment_current_loan(self):
        loan = self._create_loan()
        loan.action_confirm()
        self.assertTrue(self.equipment.current_loan_line_id)
        self.assertEqual(self.equipment.current_loan_line_id.loan_id, loan)

    # ------------------------------------------------------------------
    # Notifications (cron)
    # ------------------------------------------------------------------
    @patch("requests.post")
    def test_cron_due_reminder_sends_notification(self, mock_post):
        mock_post.return_value.status_code = 200
        loan = self._create_loan(
            expected_return_date=fields.Date.today(),
        )
        loan.action_confirm()
        self.Loan._cron_send_due_reminders(days=1)

    @patch("requests.post")
    def test_cron_overdue_alert_sends_notification(self, mock_post):
        mock_post.return_value.status_code = 200
        loan = self._create_loan(
            loan_date=fields.Date.today() - timedelta(days=5),
            expected_return_date=fields.Date.today() - timedelta(days=1),
        )
        loan.action_confirm()
        self.Loan._cron_send_overdue_alerts()

    @patch("requests.post")
    def test_cron_calibration_reminder(self, mock_post):
        mock_post.return_value.status_code = 200
        self.equipment.calibration_date = fields.Date.today()
        self.Equipment._cron_send_calibration_reminders(days=7)

    # ------------------------------------------------------------------
    # Double-borrow guard
    # ------------------------------------------------------------------
    def test_cannot_borrow_same_equipment_twice(self):
        loan1 = self._create_loan()
        loan1.action_confirm()
        # Second loan with the same equipment should fail on confirm.
        loan2 = self._create_loan()
        with self.assertRaises(UserError):
            loan2.action_confirm()

    def test_can_borrow_again_after_return(self):
        loan1 = self._create_loan()
        loan1.action_confirm()
        loan1.action_return()
        # After return, the equipment should be borrowable again.
        loan2 = self._create_loan()
        loan2.action_confirm()
        self.assertEqual(loan2.state, "borrowed")

    # ------------------------------------------------------------------
    # Returned quantity uses borrowed quantity (not hardcoded 1)
    # ------------------------------------------------------------------
    def test_returned_quantity_equals_borrowed_quantity(self):
        loan = self._create_loan(
            line_ids=[
                (0, 0, {"equipment_id": self.equipment.id, "quantity": 3})
            ]
        )
        loan.action_confirm()
        loan.action_return()
        self.assertEqual(loan.line_ids.returned_quantity, 3)

    def test_returned_quantity_cannot_exceed_borrowed(self):
        loan = self._create_loan()
        line = loan.line_ids
        with self.assertRaises(UserError):
            line.returned_quantity = 2

    # ------------------------------------------------------------------
    # Overdue detection
    # ------------------------------------------------------------------
    def test_overdue_flag_when_past_due(self):
        loan = self._create_loan(
            loan_date=fields.Date.today() - timedelta(days=5),
            expected_return_date=fields.Date.today() - timedelta(days=1),
        )
        loan.action_confirm()
        self.assertTrue(loan.is_overdue)

    def test_not_overdue_when_future_due(self):
        loan = self._create_loan(
            expected_return_date=fields.Date.today() + timedelta(days=5),
        )
        loan.action_confirm()
        self.assertFalse(loan.is_overdue)

    def test_not_overdue_when_returned(self):
        loan = self._create_loan(
            loan_date=fields.Date.today() - timedelta(days=5),
            expected_return_date=fields.Date.today() - timedelta(days=1),
        )
        loan.action_confirm()
        loan.action_return()
        self.assertFalse(loan.is_overdue)

