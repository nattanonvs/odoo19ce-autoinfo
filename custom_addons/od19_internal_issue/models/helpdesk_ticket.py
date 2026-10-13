from odoo import _, api, fields, models
from odoo.exceptions import UserError


TICKET_STATE = [
    ("draft", "ร่าง"),
    ("submitted", "ส่งตรวจสอบแล้ว"),
    ("validated", "ตรวจสอบผ่าน"),
    ("in_progress", "กำลังดำเนินการ"),
    ("done", "เสร็จสิ้น"),
    ("cancelled", "ยกเลิก"),
]


class HelpdeskTicket(models.Model):
    _inherit = ["helpdesk.ticket", "tier.validation"]

    _state_field = "state"
    _state_from = ["draft"]
    _state_to = ["validated"]

    visibility = fields.Selection(
        selection=[
            ("public", "Public"),
            ("department", "Department"),
            ("private", "Private"),
        ],
        string="Visibility",
        default="public",
        required=True,
        tracking=True,
        index=True,
        help="Who can see this issue: everyone, same department, or only reporter/assignee.",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        index=True,
    )
    reported_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Reported By",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    is_emergency = fields.Boolean(
        string="Emergency",
        default=False,
        tracking=True,
        index=True,
    )
    resolution = fields.Html(
        string="Resolution",
        sanitize_style=True,
        help="Root cause and solution — can be converted to a knowledge article.",
    )
    state = fields.Selection(
        TICKET_STATE,
        string="สถานะ",
        default="draft",
        tracking=True,
        copy=False,
        index=True,
    )

    @api.depends("state", "review_ids")
    def _compute_need_validation(self):
        """Tickets in draft state that have tier definitions need validation."""
        for rec in self:
            if rec.state in self._state_from:
                td = self.env["tier.definition"].search(
                    [("model", "=", self._name)]
                )
                rec.need_validation = any(
                    rec.evaluate_tier(t) for t in td
                )
            else:
                rec.need_validation = False

    @api.onchange("category_id")
    def _onchange_category_id(self):
        if self.category_id and self.category_id.default_user_id:
            self.user_id = self.category_id.default_user_id
        if self.category_id and self.category_id.default_team_id:
            self.team_id = self.category_id.default_team_id

    def write(self, vals):
        # Block state transition draft -> validated unless validation passed.
        if "state" in vals:
            for rec in self:
                if (
                    rec.state in self._state_from
                    and vals["state"] in self._state_to
                    and not rec.validation_status == "validated"
                ):
                    raise UserError(
                        _("ไม่สามารถเปลี่ยนสถานะเป็น 'ตรวจสอบผ่าน' ได้ "
                          "จนกว่าจะผ่านการตรวจสอบ (tier validation)")
                    )
        res = super().write(vals)
        if "user_id" in vals and vals["user_id"]:
            for record in self:
                record._notify_assigned()
        if "state" in vals:
            for record in self:
                record._notify_state_changed(vals["state"])
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.user_id:
                record._notify_assigned()
        return records

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------
    def action_submit(self):
        """Submit the ticket for tier validation."""
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("เฉพาะปัญหาสถานะ 'ร่าง' เท่านั้นที่สามารถส่งตรวจสอบได้"))
            rec.request_validation()
            rec.state = "submitted"
            rec._notify_updated(
                _("ปัญหา %(number)s ถูกส่งตรวจสอบแล้ว") % {"number": rec.number}
            )

    def action_validate(self):
        """Approve the current tier review."""
        for rec in self:
            if not rec.can_review:
                raise UserError(_("คุณไม่มีสิทธิ์ตรวจสอบปัญหานี้"))
            rec.validate_tier()
            if rec.validation_status == "validated":
                rec.state = "validated"
                rec._notify_updated(
                    _("ปัญหา %(number)s ตรวจสอบผ่านแล้ว") % {"number": rec.number}
                )

    def action_reject(self):
        """Reject the current tier review."""
        for rec in self:
            if not rec.can_review:
                raise UserError(_("คุณไม่มีสิทธิ์ปฏิเสธปัญหานี้"))
            rec.reject_tier()
            rec.state = "draft"

    def action_start_work(self):
        """Move from validated to in_progress."""
        for rec in self:
            if rec.state != "validated":
                raise UserError(
                    _("เฉพาะปัญหาที่ตรวจสอบผ่านแล้วเท่านั้นที่สามารถเริ่มดำเนินการได้")
                )
            rec.state = "in_progress"

    def action_done(self):
        """Mark the issue as done."""
        for rec in self:
            if rec.state != "in_progress":
                raise UserError(
                    _("เฉพาะปัญหาที่กำลังดำเนินการเท่านั้นที่สามารถปิดได้")
                )
            rec.state = "done"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = "draft"

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify_assigned(self):
        self.ensure_one()
        assignee = self.user_id
        if not assignee:
            return
        partners = assignee.partner_id
        message = _(
            "You have been assigned to issue %(number)s: %(title)s.",
            number=self.number,
            title=self.name,
        )
        self.env["notification.service"].notify(
            partners,
            message,
            event="issue_assigned",
            subject=_("New Issue Assigned"),
        )

    def _notify_state_changed(self, new_state):
        """Notify followers and create a mail.activity on state change."""
        self.ensure_one()
        state_label = dict(TICKET_STATE).get(new_state, new_state)
        body = _(
            "สถานะปัญหา %(number)s เปลี่ยนเป็น '%(state)s' โดย %(user)s"
        ) % {
            "number": self.number,
            "state": state_label,
            "user": self.env.user.name,
        }
        self.message_post(body=body)
        # Create a reminder activity for the assignee on in_progress.
        if new_state == "in_progress" and self.user_id:
            self.env["mail.activity"].sudo().create(
                {
                    "activity_type_id": self.env.ref(
                        "mail.mail_activity_data_todo",
                        raise_if_not_found=False,
                    ).id
                    or False,
                    "summary": _("ดำเนินการปัญหา: %s") % self.name,
                    "note": _(
                        "ปัญหา %(number)s ได้รับการอนุมัติแล้ว "
                        "กรุณาดำเนินการให้เสร็จสิ้น"
                    ) % {"number": self.number},
                    "user_id": self.user_id.id,
                    "res_model_id": self.env["ir.model"]._get_id(
                        "helpdesk.ticket"
                    ),
                    "res_id": self.id,
                    "date_deadline": fields.Date.today(),
                }
            )

    def _notify_updated(self, message_text):
        """Notify partners and post a chatter message on ticket update."""
        self.ensure_one()
        partners = self._get_notification_partners()
        if partners:
            self.env["notification.service"].notify(
                partners,
                message_text,
                event="issue_updated",
                subject=_("Issue Updated: %s") % self.name,
            )
        self.message_post(body=message_text)

    def _get_notification_partners(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        if self.user_id:
            partners |= self.user_id.partner_id
        if self.reported_by_id:
            partners |= self.reported_by_id.partner_id
        if self.partner_id:
            partners |= self.partner_id
        return partners
