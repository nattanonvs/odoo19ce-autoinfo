# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""เกณฑ์สุขภาพระบบ: นิยามว่า "ค่าแบบไหน = ความรุนแรงระดับใด" (P3).

กฎ (rule) ผูกกับการตรวจ 1 รายการ (``od19.health.check``) และเป็นตัวตัดสินว่า
ผลการวัดจะกลายเป็นความรุนแรง Info/Warning/Critical/Emergency พร้อมกำหนด
หน้าต่าง dedup, การยกระดับ และผู้รับแจ้งเตือน
"""

import logging

from odoo import api, fields, models

from .od19_health_common import (
    METRICS,
    OPERATORS,
    SEVERITIES,
    SEVERITY_RANK,
    compare,
)

_logger = logging.getLogger(__name__)


class Od19HealthRule(models.Model):
    """เกณฑ์ตัดสินความรุนแรงของผลการตรวจ 1 รายการ."""

    _name = "od19.health.rule"
    _description = "เกณฑ์สุขภาพระบบ (OD19)"
    _order = "check_id, sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)

    check_id = fields.Many2one(
        "od19.health.check",
        string="การตรวจ",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )

    # ------------------------- เงื่อนไข -------------------------
    metric = fields.Selection(
        METRICS,
        default="value",
        required=True,
        help="ค่าที่จะนำมาเทียบกับเกณฑ์: ตัวเลข / สถานะ / ข้อความ",
    )
    operator = fields.Selection(OPERATORS, default="gt", required=True)
    threshold = fields.Float(digits=(16, 2), help="เกณฑ์ตัวเลข")
    threshold_text = fields.Char(help="เกณฑ์ข้อความ (ใช้กับ 'มีคำว่า' หรือเทียบสถานะ)")

    # ------------------------- ผลลัพธ์ -------------------------
    severity = fields.Selection(SEVERITIES, default="warning", required=True)
    check_state = fields.Selection(
        [
            ("ok", "ปกติ"),
            ("warning", "เตือน"),
            ("critical", "วิกฤต"),
        ],
        default="warning",
        required=True,
        help="สถานะที่จะแสดงบน dashboard เมื่อกฎนี้ตรง",
    )

    # --------------------- dedup / escalation ---------------------
    fingerprint_window_minutes = fields.Integer(
        default=60,
        help="หน้าต่างเวลา (นาที) สำหรับกันสัญญาณซ้ำ: ถ้าเหตุเดิมยังไม่ครบหน้าต่าง "
        "ระบบจะรวมเป็นเหตุเดิมและนับจำนวนครั้งเพิ่ม",
    )
    escalate_after_minutes = fields.Integer(
        default=0,
        help="ถ้าไม่มีการรับทราบภายในกี่นาทีจึงยกระดับ (0 = ไม่ยกระดับ)",
    )
    escalate_severity = fields.Selection(SEVERITIES)

    # ------------------------- ผู้รับ -------------------------
    notify_event = fields.Char(
        default="od19_health_alert",
        required=True,
        help="event key ที่ส่งให้ notification.service",
    )
    notify_group_ids = fields.Many2many(
        "res.groups",
        "od19_health_rule_group_rel",
        "rule_id",
        "group_id",
        string="กลุ่มผู้รับ",
    )
    notify_user_ids = fields.Many2many(
        "res.users",
        "od19_health_rule_user_rel",
        "rule_id",
        "user_id",
        string="ผู้รับเพิ่มเติม",
    )

    _severity_required_on_escalate = models.Constraint(
        "CHECK (escalate_after_minutes <= 0 OR escalate_severity IS NOT NULL)",
        "ต้องระบุความรุนแรงปลายทางเมื่อเปิดใช้การยกระดับ",
    )

    # ------------------------------------------------------------------
    # การตัดสิน
    # ------------------------------------------------------------------
    def _matches(self, measure):
        """True เมื่อ ``measure`` (ผลการวัด) ตรงกับเงื่อนไขของกฎนี้."""
        self.ensure_one()
        if self.metric == "always":
            return True
        if self.metric == "value":
            return compare(self.operator, measure.get("value"), self.threshold)
        if self.metric == "status":
            return compare(self.operator, measure.get("status"), self.threshold_text)
        if self.metric == "message":
            return compare(self.operator, measure.get("message"), self.threshold_text)
        return False

    def _rank(self):
        """ลำดับตัวเลขของความรุนแรง (ใช้เลือกกฎที่รุนแรงสุด)."""
        self.ensure_one()
        return SEVERITY_RANK.get(self.severity, 0)

    def _partners(self):
        """คืน res.partner ของผู้รับทั้งหมด (จากกลุ่ม + ผู้ใช้ที่ระบุ)."""
        self.ensure_one()
        users = self.notify_user_ids
        group_users = self.env["res.users"].search(
            [("group_ids", "in", self.notify_group_ids.ids)]
        )
        users |= group_users
        return users.mapped("partner_id").filtered("active")

    @api.model
    def _pick_rule(self, check, measure):
        """เลือกกฎที่รุนแรงที่สุดที่ตรงกับผลการวัด (หรือว่างถ้าไม่มี)."""
        matched = check.rule_ids.filtered(lambda rule: rule._matches(measure))
        if not matched:
            return self.browse()
        return matched.sorted(lambda rule: rule._rank(), reverse=True)[:1]
