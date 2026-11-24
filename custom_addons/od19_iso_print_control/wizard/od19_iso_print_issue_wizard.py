# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError

ACTION_ISSUE = "issue"
ACTION_RETURN = "return"
ACTION_CHANGE = "change"

ACTION_TYPE = [
    (ACTION_ISSUE, "จ่ายสำเนา (Issue)"),
    (ACTION_RETURN, "รับคืนสำเนา (Return)"),
    (ACTION_CHANGE, "เปลี่ยนฉบับ (Replace)"),
]


class Od19IsoPrintIssueWizard(models.TransientModel):
    """Wizard จ่าย/คืน/เปลี่ยนสำเนาควบคุม."""

    _name = "od19.iso.print.issue.wizard"
    _description = "ISO Print Copy Issue Wizard"

    action_type = fields.Selection(
        ACTION_TYPE, string="การดำเนินการ", default=ACTION_ISSUE, required=True
    )
    copy_ids = fields.Many2many(
        "od19.iso.print.copy",
        string="สำเนา",
        default=lambda self: self._default_copy_ids(),
    )
    holder_id = fields.Many2one("res.users", string="ผู้ถือครอง (ภายใน)")
    holder_name = fields.Char(string="ชื่อผู้ถือครอง (ภายนอก)")
    holder_dept_id = fields.Many2one("hr.department", string="แผนกผู้ถือครอง")
    issue_date = fields.Date(string="วันจ่ายสำเนา", default=fields.Date.today)
    return_due_date = fields.Date(string="กำหนดคืน")
    reason = fields.Text(string="เหตุผล (เปลี่ยนฉบับ)")

    def _default_copy_ids(self):
        active_ids = self.env.context.get("active_ids")
        if active_ids:
            return [(6, 0, active_ids)]
        default_ids = self.env.context.get("default_copy_ids")
        return default_ids or [(6, 0, [])]

    def action_apply(self):
        self.ensure_one()
        if not self.copy_ids:
            raise UserError(_("กรุณาเลือกสำเนาอย่างน้อย 1 ใบ"))
        if self.action_type == ACTION_ISSUE:
            return self._apply_issue()
        if self.action_type == ACTION_RETURN:
            return self._apply_return()
        return self._apply_change()

    # ------------------------------------------------------------------
    def _apply_issue(self):
        self.copy_ids.action_issue()
        values = {
            "holder_id": self.holder_id.id or False,
            "holder_name": self.holder_name,
            "holder_dept_id": self.holder_dept_id.id or False,
            "issue_date": self.issue_date,
        }
        if self.return_due_date:
            values["return_due_date"] = self.return_due_date
        self.copy_ids.write(values)
        self.copy_ids.message_post(
            body=_("จ่ายสำเนาโดย %s") % self.env.user.name
        )
        return {"type": "ir.actions.act_window_close"}

    def _apply_return(self):
        self.copy_ids.action_return()
        return {"type": "ir.actions.act_window_close"}

    def _apply_change(self):
        issued = self.copy_ids.filtered(lambda c: c.state == "issued")
        if not issued:
            raise UserError(_("เปลี่ยนฉบับได้เฉพาะสำเนาที่จ่ายแล้วเท่านั้น"))
        for copy in issued:
            copy.write({"state": "replaced", "reason": self.reason})
            copy.message_post(
                body=_("เปลี่ยนฉบับสำเนา %s — %s") % (copy.name, self.reason or "")
            )
        return {"type": "ir.actions.act_window_close"}
