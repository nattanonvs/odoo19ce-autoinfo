from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .internal_issue_common import QUEUE_REQUEST_STATE


class HelpdeskQueueRequest(models.Model):
    _name = "helpdesk.queue.request"
    _description = "Internal Issue Queue Jump Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="เลขที่คำขอ", readonly=True, default="ใหม่")
    ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="เรื่อง",
        required=True,
        ondelete="cascade",
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="ผู้ขอ",
        default=lambda self: self.env.user,
        required=True,
    )
    reason = fields.Text(string="เหตุผลการขอแซงคิว", required=True)
    state = fields.Selection(
        QUEUE_REQUEST_STATE, string="สถานะ", default="draft", tracking=True
    )
    approver_reporter_head_id = fields.Many2one(
        comodel_name="res.users", string="หัวหน้าแผนกผู้แจ้ง"
    )
    approver_team_head_id = fields.Many2one(
        comodel_name="res.users", string="หัวหน้าทีมเจ้าของคิว"
    )
    reporter_head_approved = fields.Boolean(string="หัวหน้าแผนกอนุมัติ")
    team_head_approved = fields.Boolean(string="หัวหน้าทีมอนุมัติ")
    insert_before_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="แทรกก่อนเรื่อง",
        help="ผู้อนุมัติเลือกตำแหน่งแทรกในคิว",
    )
    deadline = fields.Datetime(string="หมดอายุเมื่อ")
    decision_note = fields.Text(string="บันทึกการตัดสินใจ")

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("ส่งได้เฉพาะคำขอสถานะร่างเท่านั้น"))
            if not rec.deadline:
                rec.deadline = fields.Datetime.now() + timedelta(hours=24)
            rec.state = "waiting_reporter_head"
            rec.ticket_id.consent_state = "jump_requested"
            rec._notify_approvers()

    def action_approve_reporter_head(self):
        for rec in self:
            if rec.state != "waiting_reporter_head":
                raise UserError(_("คำขอนี้ยังไม่พร้อมให้หัวหน้าแผนกอนุมัติ"))
            rec.reporter_head_approved = True
            rec.state = "waiting_team_head"
            rec._notify_approvers()

    def action_approve_team_head(self):
        for rec in self:
            if rec.state != "waiting_team_head":
                raise UserError(_("คำขอนี้ยังไม่พร้อมให้หัวหน้าทีมอนุมัติ"))
            rec.team_head_approved = True
            rec.state = "approved"
            rec._apply_insertion()
            rec._notify_outcome()

    def action_reject(self):
        for rec in self:
            rec.state = "rejected"
            rec.ticket_id.consent_state = "accepted"
            rec._notify_outcome()

    def _apply_insertion(self):
        self.ensure_one()
        ticket = self.ticket_id
        if not ticket:
            return
        if self.insert_before_id:
            ticket.queue_sequence = self.insert_before_id.queue_sequence - 1
        else:
            ticket.queue_sequence = 0
        ticket.is_priority_inserted = True
        ticket.insert_before_id = self.insert_before_id
        ticket.message_post(
            body=_("คำขอแซงคิว %(name)s อนุมัติครบแล้ว — ถูกแทรกคิวก่อน '%(before)s'")
            % {
                "name": self.name,
                "before": self.insert_before_id.name or "หัวคิว",
            }
        )

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_expire_stale_requests(self):
        now = fields.Datetime.now()
        stale = self.search(
            [
                ("state", "in", ("waiting_reporter_head", "waiting_team_head")),
                ("deadline", "!=", False),
                ("deadline", "<", now),
            ]
        )
        for rec in stale:
            rec.state = "expired"
            if rec.ticket_id:
                rec.ticket_id.consent_state = "accepted"
            rec._notify_outcome()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify_approvers(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        for user in (self.approver_reporter_head_id, self.approver_team_head_id):
            if user:
                partners |= user.partner_id
        if partners:
            self.env["notification.service"].notify(
                partners,
                _("คำขอแซงคิวเรื่อง %(number)s รอการอนุมัติ")
                % {"number": self.ticket_id.number or ""},
                event="issue_updated",
                subject=_("คำขอแซงคิวรออนุมัติ"),
            )

    def _notify_outcome(self):
        self.ensure_one()
        if not self.requested_by:
            return
        self.env["notification.service"].notify(
            self.requested_by.partner_id,
            _("คำขอแซงคิวเรื่อง %(number)s: %(state)s")
            % {
                "number": self.ticket_id.number or "",
                "state": dict(QUEUE_REQUEST_STATE).get(self.state, self.state),
            },
            event="issue_updated",
            subject=_("ผลการขอแซงคิว"),
        )
