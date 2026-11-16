from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueQueueRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Request = cls.env["helpdesk.queue.request"]
        cls.team = cls.Team.create({"name": "QR Team (test)", "is_triage_team": True})
        # สร้าง stage เอง (ไม่พึ่ง demo data) เพื่อความ deterministic
        cls.stage = cls.env["helpdesk.ticket.stage"].create(
            {"name": "Open (test)", "closed": False}
        )
        cls.reporter = cls.env["res.users"].create(
            {"name": "Reporter", "login": "reporter_issue_test"}
        )
        cls.head_a = cls.env["res.users"].create(
            {"name": "Head A", "login": "head_a_issue_test"}
        )
        cls.head_b = cls.env["res.users"].create(
            {"name": "Head B", "login": "head_b_issue_test"}
        )

    def _ticket(self, name, queue_sequence=10):
        return self.Ticket.create(
            {
                "name": name,
                "description": "<p>t</p>",
                "team_id": self.team.id,
                "stage_id": self.stage.id,
                "queue_sequence": queue_sequence,
                "reported_by_id": self.reporter.id,
            }
        )

    @patch("requests.post")
    def test_two_layer_approval_inserts_ticket(self, mock_post):
        mock_post.return_value.status_code = 200
        target = self._ticket("target")
        ticket = self._ticket("jumper", queue_sequence=50)

        request = self.Request.create(
            {
                "ticket_id": ticket.id,
                "requested_by": self.reporter.id,
                "reason": "ลูกค้ารออยู่",
                "approver_reporter_head_id": self.head_a.id,
                "approver_team_head_id": self.head_b.id,
                "insert_before_id": target.id,
            }
        )
        request.action_submit()
        self.assertEqual(request.state, "waiting_reporter_head")

        request.action_approve_reporter_head()
        self.assertEqual(request.state, "waiting_team_head")

        request.action_approve_team_head()
        self.assertEqual(request.state, "approved")
        ticket.invalidate_recordset()
        self.assertTrue(ticket.is_priority_inserted)
        self.assertEqual(ticket.insert_before_id, target)
        self.assertLess(ticket.queue_sequence, target.queue_sequence)

    @patch("requests.post")
    def test_expiry_when_deadline_passed(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("expire-me")
        request = self.Request.create(
            {
                "ticket_id": ticket.id,
                "requested_by": self.reporter.id,
                "reason": "urgent",
                "approver_reporter_head_id": self.head_a.id,
                "approver_team_head_id": self.head_b.id,
                "deadline": fields.Datetime.now() - timedelta(hours=1),
            }
        )
        request.action_submit()
        self.Request._cron_expire_stale_requests()
        request.invalidate_recordset()
        self.assertEqual(request.state, "expired")
