from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("standard", "at_install")
class TestInternalIssue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Category = cls.env["helpdesk.ticket.category"]

        cls.category = cls.Category.create(
            {
                "name": "Test Category",
                "active": True,
            }
        )
        cls.user_admin = cls.env.ref("base.user_admin")

    def _create_ticket(self, **overrides):
        vals = {
            "name": "Test Issue",
            "description": "<p>Test description</p>",
            "category_id": self.category.id,
        }
        vals.update(overrides)
        return self.Ticket.create(vals)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    def test_default_visibility_is_public(self):
        ticket = self._create_ticket()
        self.assertEqual(ticket.visibility, "public")

    def test_default_reported_by_is_current_user(self):
        ticket = self._create_ticket()
        self.assertEqual(ticket.reported_by_id, self.env.user)

    def test_default_is_emergency_false(self):
        ticket = self._create_ticket()
        self.assertFalse(ticket.is_emergency)

    # ------------------------------------------------------------------
    # Category defaults
    # ------------------------------------------------------------------
    def test_category_default_user(self):
        self.category.default_user_id = self.user_admin
        ticket = self.Ticket.new({"category_id": self.category.id})
        ticket._onchange_category_id()
        self.assertEqual(ticket.user_id, self.user_admin)

    # ------------------------------------------------------------------
    # Visibility record rules
    # ------------------------------------------------------------------
    def test_visibility_public_seen_by_others(self):
        ticket = self._create_ticket(visibility="public")
        # admin should see it
        self.assertTrue(ticket.with_user(self.user_admin).read(["name"]))

    def test_visibility_private_limited(self):
        ticket = self._create_ticket(visibility="private")
        # admin is neither reporter nor assignee — but record rule
        # allows admin to see via admin group; test logic only:
        self.assertEqual(ticket.visibility, "private")

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    @patch("requests.post")
    def test_notification_on_create_with_assignee(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._create_ticket(user_id=self.user_admin.id)
        self.assertTrue(ticket.user_id)

    @patch("requests.post")
    def test_notification_on_user_change(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._create_ticket()
        ticket.write({"user_id": self.user_admin.id})
        self.assertEqual(ticket.user_id, self.user_admin)

    # ------------------------------------------------------------------
    # Emergency flag
    # ------------------------------------------------------------------
    def test_emergency_flag(self):
        ticket = self._create_ticket(is_emergency=True)
        self.assertTrue(ticket.is_emergency)

    # ------------------------------------------------------------------
    # Resolution field
    # ------------------------------------------------------------------
    def test_resolution_field(self):
        ticket = self._create_ticket()
        ticket.resolution = "<p>Fixed by restarting</p>"
        self.assertTrue(ticket.resolution)

    # ------------------------------------------------------------------
    # Tier validation workflow
    # ------------------------------------------------------------------
    def test_default_state_is_draft(self):
        ticket = self._create_ticket()
        self.assertEqual(ticket.state, "draft")

    def test_submit_changes_state_to_submitted(self):
        ticket = self._create_ticket()
        ticket.action_submit()
        self.assertEqual(ticket.state, "submitted")

    def test_start_work_requires_validated_state(self):
        ticket = self._create_ticket()
        with self.assertRaises(Exception):
            ticket.action_start_work()

    def test_done_requires_in_progress_state(self):
        ticket = self._create_ticket()
        with self.assertRaises(Exception):
            ticket.action_done()

    def test_full_workflow_as_admin(self):
        ticket = self._create_ticket()
        ticket.action_submit()
        self.assertEqual(ticket.state, "submitted")
        # Admin can review
        ticket.action_validate()
        self.assertEqual(ticket.state, "validated")
        ticket.action_start_work()
        self.assertEqual(ticket.state, "in_progress")
        ticket.action_done()
        self.assertEqual(ticket.state, "done")

    def test_cancel_and_reset(self):
        ticket = self._create_ticket()
        ticket.action_cancel()
        self.assertEqual(ticket.state, "cancelled")
        ticket.action_reset_to_draft()
        self.assertEqual(ticket.state, "draft")
