from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import CreditGateCommon


@tagged("post_install", "-at_install")
class TestCreditWorkflow(CreditGateCommon):
    def test_defaults_are_non_credit(self):
        self.assertEqual(self.customer.od19_blacklist_status, "normal")
        self.assertEqual(self.customer.od19_credit_request_state, "not_requested")
        self.assertFalse(self.customer.od19_credit_sale_allowed)

    def test_sales_can_request_credit(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "pending")
        self.assertEqual(self.customer.od19_credit_requested_by, self.sales_user)
        self.assertTrue(self.customer.od19_credit_request_date)

    def test_request_schedules_activity_for_review_owner(self):
        self.customer.od19_credit_review_owner_id = self.reviewer
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.assertTrue(
            self.customer.activity_ids.filtered(lambda a: a.user_id == self.reviewer)
        )

    def test_sales_cannot_approve_or_edit_protected_fields(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        with self.assertRaises(AccessError):
            self.customer.with_user(self.sales_user).action_od19_approve_credit()
        with self.assertRaises(AccessError):
            self.customer.with_user(self.sales_user).write(
                {"od19_credit_request_state": "approved"}
            )
        with self.assertRaises(AccessError):
            self.customer.with_user(self.sales_user).write(
                {"od19_blacklist_status": "blacklisted"}
            )

    def test_reviewer_approves_with_note_and_audit(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.od19_credit_review_note = "Docs complete"
        self.customer.with_user(self.reviewer).action_od19_approve_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "approved")
        self.assertTrue(self.customer.od19_credit_sale_allowed)
        self.assertEqual(self.customer.od19_credit_review_owner_id, self.reviewer)
        self.assertTrue(self.customer.od19_credit_review_date)

    def test_approve_requires_review_note(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        with self.assertRaises(UserError):
            self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def test_reject_then_rerequest(self):
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.od19_credit_review_note = "Missing docs"
        self.customer.with_user(self.reviewer).action_od19_reject_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "rejected")
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.assertEqual(self.customer.od19_credit_request_state, "pending")

    def test_only_pending_can_be_reviewed(self):
        with self.assertRaises(UserError):
            self.customer.with_user(self.reviewer).action_od19_approve_credit()

    def test_blacklist_requires_reason_and_reviewer(self):
        with self.assertRaises(UserError):
            self.customer.with_user(self.reviewer).action_od19_set_blacklist()
        self.customer.with_user(self.reviewer).write({"od19_blacklist_reason": "Fraud"})
        self.customer.with_user(self.reviewer).action_od19_set_blacklist()
        self.assertEqual(self.customer.od19_blacklist_status, "blacklisted")

    def test_child_contact_reads_commercial_partner_state(self):
        self.customer.od19_credit_review_note = "ok"
        self.customer.with_user(self.sales_user).action_od19_request_credit()
        self.customer.with_user(self.reviewer).action_od19_approve_credit()
        self.assertTrue(self.contact.commercial_partner_id.od19_credit_sale_allowed)
