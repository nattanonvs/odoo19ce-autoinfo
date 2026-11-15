# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""หน้าต่างซ่อมบำรุง (maintenance window).

ใช้ "ระงับการแจ้งเตือน" ของการตรวจที่เลือกไว้ในช่วงเวลาที่วางแผนซ่อม
เพื่อกัน alert fatigue จากงานที่รู้อยู่แล้ว (ตามข้อเสนอโครงการ P3)
ถ้าไม่ได้เลือกการตรวจใดไว้ = มีผลกับการตรวจทั้งหมด

ข้อจำกัดด้านความปลอดภัย: โมดูลนี้ **ไม่** ปิด/รีสตาร์ทบริการใด ๆ
(สอดคล้อง AGENTS.md Tier 3 ข้อ 7 และ D5) เพียงระงับการแจ้งเตือนเท่านั้น
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

MAINTENANCE_STATES = [
    ("scheduled", "กำหนดไว้"),
    ("running", "กำลังดำเนินการ"),
    ("done", "เสร็จสิ้น"),
]


class Od19HealthMaintenance(models.Model):
    """หน้าต่างซ่อมบำรุง 1 ช่วง (ใช้ระงับการแจ้งเตือน)."""

    _name = "od19.health.maintenance"
    _description = "หน้าต่างซ่อมบำรุง (OD19)"
    _order = "start_datetime desc, id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()

    start_datetime = fields.Datetime(required=True, default=fields.Datetime.now)
    end_datetime = fields.Datetime(required=True)

    user_id = fields.Many2one(
        "res.users",
        string="ผู้รับผิดชอบ",
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    check_ids = fields.Many2many(
        "od19.health.check",
        "od19_health_maintenance_check_rel",
        "maintenance_id",
        "check_id",
        string="การตรวจที่ระงับ",
        help="ถ้าเว้นว่าง = ระงับการแจ้งเตือนของการตรวจทั้งหมด",
    )
    suppress_notifications = fields.Boolean(
        default=True, help="งดส่งการแจ้งเตือนระหว่างหน้าต่างนี้"
    )
    state = fields.Selection(MAINTENANCE_STATES, compute="_compute_state")

    @api.depends("start_datetime", "end_datetime")
    def _compute_state(self):
        now = fields.Datetime.now()
        for window in self:
            if not window.start_datetime or not window.end_datetime:
                window.state = "scheduled"
            elif now < window.start_datetime:
                window.state = "scheduled"
            elif window.start_datetime <= now <= window.end_datetime:
                window.state = "running"
            else:
                window.state = "done"

    @api.model
    def is_suppressed(self, check, at=None):
        """True ถ้าการตรวจ ``check`` ถูกระงับการแจ้งเตือนที่เวลา ``at``."""
        at = at or fields.Datetime.now()
        now_windows = self.search(
            [
                ("active", "=", True),
                ("suppress_notifications", "=", True),
                ("start_datetime", "<=", at),
                ("end_datetime", ">=", at),
            ]
        )
        for window in now_windows:
            if not window.check_ids or check in window.check_ids:
                return True
        return False
