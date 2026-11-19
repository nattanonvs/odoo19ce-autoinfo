from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

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
        comodel_name="res.users",
        string="หัวหน้าแผนกผู้แจ้ง",
        compute="_compute_approvers",
        store=True,
        readonly=False,
        help="ค่าเริ่มต้นจากหัวหน้าแผนกต้นสังกัดผู้แจ้ง; ถ้าไม่มีให้ใช้หัวหน้าทีมเจ้าของคิว",
    )
    approver_team_head_id = fields.Many2one(
        comodel_name="res.users",
        string="หัวหน้าทีมเจ้าของคิว",
        compute="_compute_approvers",
        store=True,
        readonly=False,
        help="ค่าเริ่มต้นจากหัวหน้า (Team Leader) ของทีมเจ้าของคิว",
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
    # Compute
    # ------------------------------------------------------------------
    @api.depends(
        "ticket_id",
        "ticket_id.team_id",
        "ticket_id.reported_by_id",
        "requested_by",
    )
    def _compute_approvers(self):
        for rec in self:
            team_head = rec.ticket_id.team_id.user_id
            reporter = rec.ticket_id.reported_by_id or rec.requested_by
            department = reporter.od19_department_id
            reporter_head = department.manager_id.user_id if department else False
            rec.approver_team_head_id = team_head
            # Edge case: ผู้แจ้งไม่มีแผนก/หัวหน้าแผนก -> ใช้หัวหน้าทีมเจ้าของคิวชั้นแรก
            rec.approver_reporter_head_id = reporter_head or team_head

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def _check_approval_right(self, *approvers):
        """ยืนยันว่าผู้ใช้ปัจจุบันเป็นผู้อนุมัติที่กำหนด หรือเป็นผู้จัดการ Helpdesk.

        superuser (``env.su``) ผ่านเสมอ เพื่อไม่ให้กระทบสคริปต์ระบบ/การทดสอบ
        """
        self.ensure_one()
        if self.env.su:
            return
        if any(approver and self.env.user == approver for approver in approvers):
            return
        if self.env.user.has_group("helpdesk_mgmt.group_helpdesk_manager"):
            return
        raise AccessError(
            _(
                "เฉพาะผู้อนุมัติที่กำหนดไว้ (หรือผู้จัดการ Helpdesk) "
                "เท่านั้นที่อนุมัติ/ปฏิเสธคำขอแซงคิวได้"
            )
        )

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("ส่งได้เฉพาะคำขอสถานะร่างเท่านั้น"))
            if not rec.deadline:
                hours = float(
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("od19_internal_issue.jump_window_hours", 24)
                )
                rec.deadline = fields.Datetime.now() + timedelta(hours=hours)
            rec.state = "waiting_reporter_head"
            rec.ticket_id.consent_state = "jump_requested"
            rec._notify_approvers()

    def action_approve_reporter_head(self):
        for rec in self:
            if rec.state != "waiting_reporter_head":
                raise UserError(_("คำขอนี้ยังไม่พร้อมให้หัวหน้าแผนกอนุมัติ"))
            rec._check_approval_right(rec.approver_reporter_head_id)
            rec.reporter_head_approved = True
            rec.state = "waiting_team_head"
            rec._notify_approvers()

    def action_approve_team_head(self):
        for rec in self:
            if rec.state != "waiting_team_head":
                raise UserError(_("คำขอนี้ยังไม่พร้อมให้หัวหน้าทีมอนุมัติ"))
            rec._check_approval_right(rec.approver_team_head_id)
            rec.team_head_approved = True
            rec.state = "approved"
            rec._apply_insertion()
            rec._notify_outcome()

    def action_reject(self):
        for rec in self:
            if rec.state not in (
                "draft",
                "waiting_reporter_head",
                "waiting_team_head",
            ):
                raise UserError(_("ไม่อนุญาตให้ปฏิเสธคำขอในสถานะนี้"))
            if not self.env.su and self.env.user != rec.requested_by:
                rec._check_approval_right(
                    rec.approver_reporter_head_id,
                    rec.approver_team_head_id,
                )
            rec.state = "rejected"
            rec.ticket_id.consent_state = "accepted"
            rec._notify_outcome()

    @api.constrains("insert_before_id")
    def _check_insert_before(self):
        for rec in self:
            if not rec.insert_before_id or not rec.ticket_id:
                continue
            if rec.insert_before_id == rec.ticket_id:
                raise ValidationError(_("ไม่สามารถแทรกเรื่องก่อนตัวเองได้"))
            if (
                rec.ticket_id.team_id
                and rec.insert_before_id.team_id
                and rec.ticket_id.team_id != rec.insert_before_id.team_id
            ):
                raise ValidationError(
                    _("ตำแหน่งแทรกต้องอยู่ในคิวของทีมเดียวกับเรื่องที่ขอแซง")
                )

    def _apply_insertion(self):
        self.ensure_one()
        ticket = self.ticket_id
        if not ticket:
            return
        if self.insert_before_id:
            # clamp ไม่ให้ค่าติดลบสะสมเมื่อแทรกซ้ำหลายครั้ง
            ticket.queue_sequence = max(self.insert_before_id.queue_sequence - 1, 0)
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
