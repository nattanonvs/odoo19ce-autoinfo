from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
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
        cls.team_b = cls.Team.create({"name": "QR Team B (test)"})
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

    def _ticket(self, name, queue_sequence=10, team=None):
        return self.Ticket.create(
            {
                "name": name,
                "description": "<p>t</p>",
                "team_id": (team or self.team).id,
                "stage_id": self.stage.id,
                "queue_sequence": queue_sequence,
                "reported_by_id": self.reporter.id,
            }
        )

    def _request(self, ticket, **overrides):
        vals = {
            "ticket_id": ticket.id,
            "requested_by": self.reporter.id,
            "reason": "urgent",
            "approver_reporter_head_id": self.head_a.id,
            "approver_team_head_id": self.head_b.id,
        }
        vals.update(overrides)
        return self.Request.create(vals)

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

    @patch("requests.post")
    def test_reject_from_active_state(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("reject-active")
        request = self._request(ticket)
        request.action_submit()

        request.action_reject()
        self.assertEqual(request.state, "rejected")
        ticket.invalidate_recordset()
        self.assertEqual(ticket.consent_state, "accepted")

    @patch("requests.post")
    def test_reject_from_terminal_state_raises(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("reject-terminal")
        request = self._request(ticket)
        request.action_submit()
        request.action_approve_reporter_head()
        request.action_approve_team_head()
        self.assertEqual(request.state, "approved")

        with self.assertRaises(UserError):
            request.action_reject()

    @patch("requests.post")
    def test_submit_twice_raises(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("submit-twice")
        request = self._request(ticket)
        request.action_submit()
        self.assertEqual(request.state, "waiting_reporter_head")

        with self.assertRaises(UserError):
            request.action_submit()

    @patch("requests.post")
    def test_approve_team_head_out_of_order_raises(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("out-of-order")
        request = self._request(ticket)
        request.action_submit()
        self.assertEqual(request.state, "waiting_reporter_head")

        with self.assertRaises(UserError):
            request.action_approve_team_head()

    @patch("requests.post")
    def test_approve_without_insert_before_sets_zero(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("no-target", queue_sequence=50)
        request = self._request(ticket)
        request.action_submit()
        request.action_approve_reporter_head()
        request.action_approve_team_head()

        self.assertEqual(request.state, "approved")
        ticket.invalidate_recordset()
        self.assertEqual(ticket.queue_sequence, 0)
        self.assertTrue(ticket.is_priority_inserted)

    @patch("requests.post")
    def test_cron_expire_is_idempotent(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("expire-twice")
        request = self._request(
            ticket, deadline=fields.Datetime.now() - timedelta(hours=1)
        )
        request.action_submit()

        self.Request._cron_expire_stale_requests()
        self.Request._cron_expire_stale_requests()
        request.invalidate_recordset()
        self.assertEqual(request.state, "expired")

    @patch("requests.post")
    def test_constraint_insert_before_self_raises(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("self-insert")
        with self.assertRaises(ValidationError):
            self._request(ticket, insert_before_id=ticket.id)

    @patch("requests.post")
    def test_constraint_insert_before_cross_team_raises(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("team-a-ticket")
        other_team_ticket = self._ticket(
            "team-b-ticket", queue_sequence=10, team=self.team_b
        )
        with self.assertRaises(ValidationError):
            self._request(ticket, insert_before_id=other_team_ticket.id)

    def test_default_approvers_from_team_and_department(self):
        # มีหัวหน้าทีม -> approver_team_head_id = Team Leader
        # ผู้แจ้งไม่มีแผนก -> approver_reporter_head_id fallback ไปหัวหน้าทีม
        self.team.user_id = self.head_b.id
        ticket = self._ticket("defaults-team-head")
        request = self.Request.create(
            {"ticket_id": ticket.id, "requested_by": self.reporter.id, "reason": "x"}
        )
        self.assertEqual(request.approver_team_head_id, self.head_b)
        self.assertEqual(request.approver_reporter_head_id, self.head_b)

    def test_default_reporter_head_from_department_manager(self):
        department = self.env["hr.department"].create({"name": "QR Dept (test)"})
        department.manager_id = self.env["hr.employee"].create(
            {"name": "QR Manager", "user_id": self.head_a.id}
        )
        self.reporter.with_context(od19_skip_department_sync=True).write(
            {"od19_department_id": department.id}
        )
        ticket = self._ticket("defaults-dept-head")
        request = self.Request.create(
            {"ticket_id": ticket.id, "requested_by": self.reporter.id, "reason": "x"}
        )
        self.assertEqual(request.approver_reporter_head_id, self.head_a)

    @patch("requests.post")
    def test_non_approver_cannot_approve(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("auth-guard")
        request = self._request(ticket)
        request.action_submit()

        # head_b เป็นเพียงผู้ใช้ภายใน ไม่ใช่ผู้อนุมัติชั้นแรก และไม่ใช่ manager
        with self.assertRaises(AccessError):
            request.with_user(self.head_b).action_approve_reporter_head()

    @patch("requests.post")
    def test_assigned_approver_can_approve(self, mock_post):
        mock_post.return_value.status_code = 200
        ticket = self._ticket("auth-ok")
        request = self._request(ticket)
        request.action_submit()

        # patch notify เพื่อไม่ให้ทดสอบนี้ผูกกับ ACL ของโมดูลแจ้งเตือน
        with patch.object(type(request), "_notify_approvers"):
            request.with_user(self.head_a).action_approve_reporter_head()
        self.assertEqual(request.state, "waiting_team_head")
