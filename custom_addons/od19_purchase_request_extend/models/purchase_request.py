from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    od19_request_reason = fields.Text(
        string="เหตุผลในการขอซื้อ / Request Reason",
        tracking=True,
    )
    od19_priority = fields.Selection(
        [
            ("normal", "ปกติ / Normal"),
            ("urgent", "ด่วน / Urgent"),
            ("emergency", "ด่วนพิเศษ / Emergency"),
        ],
        string="ความเร่งด่วน / Priority",
        default="normal",
        required=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="หน่วยงานที่ขอ / Requesting Department",
        compute="_compute_department_id",
        store=True,
        readonly=False,
        index=True,
        tracking=True,
    )
    od19_budget_year = fields.Char(
        string="ปีงบประมาณ / Budget Year",
        default=lambda self: str(fields.Date.context_today(self).year + 543),
        tracking=True,
    )
    od19_issue_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="แหล่งที่มาจากแจ้งปัญหา / Source Issue",
        ondelete="set null",
        tracking=True,
    )
    od19_justification_required = fields.Boolean(
        string="ต้องระบุเหตุผล",
        compute="_compute_od19_justification_required",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get("department_id"):
            user = self.env["res.users"].browse(self.env.uid)
            if user.employee_id and user.employee_id.department_id:
                res["department_id"] = user.employee_id.department_id.id
        return res

    @api.depends("od19_priority")
    def _compute_od19_justification_required(self):
        for rec in self:
            rec.od19_justification_required = rec.od19_priority in (
                "urgent",
                "emergency",
            )

    @api.depends("requested_by")
    def _compute_department_id(self):
        for rec in self:
            if rec.requested_by and rec.requested_by.employee_id:
                rec.department_id = rec.requested_by.employee_id.department_id
            else:
                rec.department_id = False

    def button_to_approve(self):
        for rec in self:
            if (
                rec.od19_priority in ("urgent", "emergency")
                and not rec.od19_request_reason
            ):
                raise UserError(
                    _(
                        "กรุณาระบุเหตุผลในการขอซื้อ (Request Reason) "
                        "สำหรับคำขอที่มีความเร่งด่วน Urgent หรือ Emergency"
                    )
                )
        result = super().button_to_approve()
        self._od19_notify_approver()
        return result

    def button_approved(self):
        result = super().button_approved()
        self._od19_notify_requester("approved")
        return result

    def button_rejected(self):
        result = super().button_rejected()
        self._od19_notify_requester("rejected")
        return result

    def _od19_notify_approver(self):
        """Notify the assigned approver via multi-channel notification."""
        for rec in self:
            approver = rec.assigned_to
            if not approver or not approver.partner_id:
                continue
            message = _(
                "มีใบคำขอซื้อรอการอนุมัติ: %s\n"
                "ผู้ขอ: %s\n"
                "ความเร่งด่วน: %s\n"
                "ประมาณการ: %s %s"
            ) % (
                rec.name,
                rec.requested_by.name,
                rec.od19_priority,
                rec.currency_id.symbol if rec.currency_id else "",
                rec.estimated_cost,
            )
            self.env["notification.service"].notify(
                partners=approver.partner_id,
                message=message,
                event="purchase_request_approval",
                subject=_(
                    "คำขอซื้อรออนุมัติ / Purchase Request for Approval: %s"
                )
                % rec.name,
            )

    def _od19_notify_requester(self, decision):
        """Notify the requester about the approval decision."""
        for rec in self:
            requester = rec.requested_by
            if not requester or not requester.partner_id:
                continue
            if decision == "approved":
                subject = _("คำขอซื้อได้รับการอนุมัติแล้ว / Approved: %s") % rec.name
                message = _(
                    "คำขอซื้อ %s ของคุณได้รับการอนุมัติแล้ว"
                ) % rec.name
            else:
                subject = _("คำขอซื้อถูกปฏิเสธ / Rejected: %s") % rec.name
                message = _("คำขอซื้อ %s ของคุณถูกปฏิเสธ") % rec.name
            self.env["notification.service"].notify(
                partners=requester.partner_id,
                message=message,
                event="purchase_request_decision",
                subject=subject,
            )
