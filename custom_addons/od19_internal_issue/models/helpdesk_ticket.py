from datetime import timedelta

from odoo import _, api, fields, models

from .internal_issue_common import (
    CONSENT_SELECTION,
    IMPACT_SELECTION,
    ISSUE_STREAM_SELECTION,
    PRIORITY_LABEL,
    URGENCY_SELECTION,
    VISIBILITY_SELECTION,
    score_to_priority,
)


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    # --- การจัดประเภท (ผู้แจ้งเลือก) ---
    issue_stream = fields.Selection(
        ISSUE_STREAM_SELECTION,
        string="ประเภทเรื่อง",
        default="unsure",
        required=True,
        tracking=True,
        index=True,
        help="หมวดใหญ่ที่ผู้แจ้งเลือก ใช้ route เรื่องเข้าทีมที่ถูกต้อง",
    )

    # --- Fair priority: Impact x Urgency ---
    impact = fields.Selection(
        IMPACT_SELECTION,
        string="ผลกระทบ",
        default="I1",
        required=True,
        tracking=True,
    )
    urgency = fields.Selection(
        URGENCY_SELECTION,
        string="ความเร่งด่วน",
        default="U1",
        required=True,
        tracking=True,
    )
    priority = fields.Selection(
        compute="_compute_priority",
        store=True,
        readonly=False,
        # ปิด default ที่สืบทอดมาจาก OCA ("1") เพื่อให้ compute ทำงานตอน create
        # (default ที่สืบทอดมาจะถูก protect กันไม่ให้ compute เขียนทับ ทำให้ค่าเป็น "1" เสมอ)
        default=None,
        tracking=True,
        help="คำนวณอัตโนมัติจาก Impact x Urgency (ผู้จัดการปรับได้ มี audit)",
    )
    emergency = fields.Boolean(
        string="ฉุกเฉิน",
        default=False,
        tracking=True,
        index=True,
        help="แจ้งเตือนทุกช่องทางทันที แต่การแทรกคิวยังต้องอนุมัติแซงคิว",
    )

    # --- ความเป็นส่วนตัว ---
    visibility = fields.Selection(
        VISIBILITY_SELECTION,
        string="การมองเห็น",
        default="public",
        required=True,
        tracking=True,
        index=True,
    )
    visibility_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="แผนกที่มองเห็น",
        tracking=True,
        index=True,
    )
    reported_by_id = fields.Many2one(
        comodel_name="res.users",
        string="ผู้แจ้ง",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )

    # --- คิว ---
    queue_sequence = fields.Integer(
        string="ลำดับคิว",
        default=10,
        copy=False,
        index=True,
        help="ใช้เป็นตัวตัดสิน FIFO ภายใน priority เดียวกัน (ค่าน้อย = ก่อน)",
    )
    queue_position = fields.Integer(
        compute="_compute_queue_position",
        string="ตำแหน่งในคิว",
    )
    queue_ahead_count = fields.Integer(
        compute="_compute_queue_position",
        string="งานก่อนหน้า",
    )
    is_priority_inserted = fields.Boolean(
        string="ถูกแทรกคิว",
        default=False,
        copy=False,
        tracking=True,
    )
    insert_before_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="แทรกก่อนเรื่อง",
        copy=False,
    )

    # --- การยินยอม / หน้าต่างขอแซงคิว ---
    consent_state = fields.Selection(
        CONSENT_SELECTION,
        string="สถานะการยินยอม",
        default="accepted",
        tracking=True,
        help="ค่าเริ่มต้น = ยินยอมเข้าคิวอัตโนมัติ",
    )
    jump_window_deadline = fields.Datetime(
        string="เปิดให้ขอแซงคิวถึง",
        copy=False,
        help="หลังเวลานี้ ปุ่ม 'ขอแซงคิว' ปิด",
    )

    # --- Handoff -> Knowledge Base (Phase 2) ---
    kb_converted = fields.Boolean(string="แปลงเป็น KB แล้ว", default=False, copy=False)
    kb_article_ref = fields.Char(string="อ้างอิงบทความ KB", copy=False)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("impact", "urgency")
    def _compute_priority(self):
        for rec in self:
            rec.priority = score_to_priority(rec.impact, rec.urgency)

    @api.depends("team_id", "priority", "queue_sequence", "stage_id")
    def _compute_queue_position(self):
        for rec in self:
            rec.queue_position = 0
            rec.queue_ahead_count = 0
            if not rec.team_id or not rec.id:
                continue
            tickets = self.search(
                [
                    ("team_id", "=", rec.team_id.id),
                    ("stage_id.closed", "=", False),
                ],
                order="priority desc, queue_sequence asc, id asc",
            )
            ids = tickets.ids
            if rec.id in ids:
                position = ids.index(rec.id) + 1
                rec.queue_position = position
                rec.queue_ahead_count = position - 1

    # ------------------------------------------------------------------
    # Create / helper
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_routing(vals)
        records = super().create(vals_list)
        for rec in records:
            rec._set_jump_window()
            rec._notify_created()
        return records

    def _set_jump_window(self):
        self.ensure_one()
        if self.jump_window_deadline:
            return
        hours = float(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_internal_issue.jump_window_hours", 24)
        )
        self.jump_window_deadline = fields.Datetime.now() + timedelta(hours=hours)

    def action_request_jump(self):
        """เปิดคำขอแซงคิว (ถูกเรียกจากปุ่มบนฟอร์ม)."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "helpdesk.queue.request",
            "view_mode": "form",
            "target": "current",
            "context": {"default_ticket_id": self.id},
        }

    def _apply_routing(self, vals):
        """เติม team_id/category_id/issue_stream อัตโนมัติจาก issue_stream + routing rules.

        ลำดับ:
        1) ผู้ส่งตั้ง team_id เอง -> เคารพ
        2) issue_stream -> ทีมที่ผูก stream นั้น
        3) 'unsure' -> ทีม Triage
        4) helpdesk.routing.rule (keyword) ที่ match -> ทีมของกฎชนะการ assign
           จาก stream/triage (เพราะเป็นเงื่อนไขเฉพาะเจาะจงกว่า) + เสริม category
        """
        if vals.get("team_id"):
            return vals

        Team = self.env["helpdesk.ticket.team"]
        stream = vals.get("issue_stream") or "unsure"

        team = Team.browse()
        if stream == "unsure":
            team = Team.search([("is_triage_team", "=", True)], limit=1)
        else:
            team = Team.search([("issue_stream", "=", stream)], limit=1)

        # keyword rules: กฎที่ match กำหนดทีมปลายทางได้ (ชนะค่า stream/triage)
        text = "%s %s" % (vals.get("name") or "", vals.get("description") or "")
        rule = self.env["helpdesk.routing.rule"]._match_text(text, stream)
        if rule:
            if rule.team_id:
                team = rule.team_id
            if not vals.get("category_id") and rule.category_id:
                vals["category_id"] = rule.category_id.id

        if team:
            vals["team_id"] = team.id
        return vals

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
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

    def _notify_created(self):
        self.ensure_one()
        partners = self._get_notification_partners()
        if not partners:
            return
        subject = (
            _("เรื่องฉุกเฉิน: %s") % self.name
            if self.emergency
            else _("สร้างเรื่องใหม่: %s") % self.name
        )
        self.env["notification.service"].notify(
            partners,
            _("เรื่อง %(number)s ถูกสร้างแล้ว") % {"number": self.number},
            event="issue_updated",
            subject=subject,
        )

    def _notify_assigned(self):
        self.ensure_one()
        if not self.user_id:
            return
        self.env["notification.service"].notify(
            self.user_id.partner_id,
            _("คุณได้รับมอบหมายเรื่อง %(number)s: %(title)s")
            % {"number": self.number, "title": self.name},
            event="issue_assigned",
            subject=_("มอบหมายเรื่องใหม่"),
        )

    def write(self, vals):
        res = super().write(vals)
        if "user_id" in vals and vals["user_id"]:
            for record in self:
                record._notify_assigned()
        if "priority" in vals:
            for record in self:
                record.message_post(
                    body=_("ปรับความสำคัญเป็น %s") % record._priority_label()
                )
        return res

    # ------------------------------------------------------------------
    # Display helper
    # ------------------------------------------------------------------
    def _priority_label(self):
        self.ensure_one()
        return PRIORITY_LABEL.get(self.priority, self.priority or "")
