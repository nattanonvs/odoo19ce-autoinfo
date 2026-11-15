# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""สถานะที่ "ตัวเฝ้าชั้นนอก" (ชั้น 2) รายงานเข้ามา + การเฝ้าซึ่งกันและกัน.

สคริปต์ `od19-health-watch.ps1` (P1) ทำงานนอกกระบวนการ Odoo แล้วรายงาน
heartbeat เข้ามาผ่านคอนโทรลเลอร์ `/od19/health/heartbeat` ระบบชั้นในเก็บ
สถานะล่าสุดไว้ที่นี่ และการตรวจประเภท ``watchdog_heartbeat`` จะนำความสดของ
heartbeat ไปตัดสินความรุนแรง (mutual watchdog ตามข้อเสนอโครงการ ข้อ 4)
"""

import logging

from odoo import api, fields, models

from .od19_health_common import CHECK_STATES, STATE_TO_COLOR

_logger = logging.getLogger(__name__)

WATCHDOG_STATES = [
    ("ok", "ปกติ"),
    ("warning", "เตือน"),
    ("critical", "วิกฤต"),
    ("unknown", "ไม่ทราบ"),
]


class Od19HealthWatchdog(models.Model):
    """ตัวเฝ้าชั้นนอก 1 ตัว (มี dead-man switch = heartbeat)."""

    _name = "od19.health.watchdog"
    _description = "ตัวเฝ้าชั้นนอก (OD19)"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(
        required=True,
        index=True,
        help="รหัสอ้างอิงที่สคริปต์ชั้น 2 ใช้ตอนรายงาน heartbeat",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    source = fields.Char(
        help="ที่มาของสัญญาณ เช่น Odoo19 Health Watch (Task Scheduler)"
    )

    expected_interval_minutes = fields.Integer(
        default=15, help="ความถี่ที่คาดว่าตัวเฝ้าจะรายงาน (นาที)"
    )
    max_age_minutes = fields.Integer(
        default=30, help="อายุ heartbeat สูงสุดที่ยอมรับได้ก่อนแจ้งเตือน (นาที)"
    )

    last_heartbeat = fields.Datetime(readonly=True)
    last_status = fields.Selection(WATCHDOG_STATES, default="unknown", readonly=True)
    last_message = fields.Char(readonly=True)
    last_payload = fields.Json(readonly=True)
    heartbeat_count = fields.Integer(default=0, readonly=True)

    heartbeat_age_minutes = fields.Integer(compute="_compute_heartbeat_age")
    state = fields.Selection(CHECK_STATES, compute="_compute_state")
    state_color = fields.Char(compute="_compute_state")

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    _code_unique = models.Constraint(
        "unique(code)", "รหัสตัวเฝ้าชั้นนอกต้องไม่ซ้ำกัน"
    )

    # ------------------------------------------------------------------
    # compute
    # ------------------------------------------------------------------
    @api.depends("last_heartbeat")
    def _compute_heartbeat_age(self):
        now = fields.Datetime.now()
        for watchdog in self:
            if not watchdog.last_heartbeat:
                watchdog.heartbeat_age_minutes = -1
                continue
            delta = now - watchdog.last_heartbeat
            watchdog.heartbeat_age_minutes = int(delta.total_seconds() // 60)

    @api.depends("last_heartbeat", "max_age_minutes")
    def _compute_state(self):
        for watchdog in self:
            watchdog.state = watchdog._heartbeat_state()
            watchdog.state_color = STATE_TO_COLOR.get(watchdog.state, "grey")

    def _heartbeat_state(self):
        """สถานะจากความสดของ heartbeat: ปกติ / เตือน / วิกฤต / ไม่ทราบ."""
        self.ensure_one()
        if not self.last_heartbeat:
            return "unknown"
        limit = self.max_age_minutes or 0
        if not limit:
            return "ok"
        age = self.heartbeat_age_minutes
        if age > limit * 2:
            return "critical"
        if age > limit:
            return "warning"
        return "ok"

    # ------------------------------------------------------------------
    # การรับสัญญาณ
    # ------------------------------------------------------------------
    @api.model
    def register_heartbeat(self, code, status="ok", message=None, payload=None):
        """บันทึกสัญญาณที่ชั้น 2 รายงานเข้ามา (เรียกจากคอนโทรลเลอร์/XML-RPC)."""
        watchdog = self.search([("code", "=", code)], limit=1)
        if not watchdog:
            watchdog = self.create({"name": code, "code": code})
        if status not in dict(WATCHDOG_STATES):
            status = "unknown"
        watchdog.write(
            {
                "last_heartbeat": fields.Datetime.now(),
                "last_status": status,
                "last_message": (message or "")[:255],
                "last_payload": payload or {},
                "heartbeat_count": watchdog.heartbeat_count + 1,
            }
        )
        return watchdog

    def action_report_ping(self):
        """ปุ่มจำลองสัญญาณ (ใช้ทดสอบ/ยืนยันการเชื่อมต่อ)."""
        for watchdog in self:
            watchdog.register_heartbeat(
                watchdog.code, status="ok", message="manual ping"
            )
        return True

    # ------------------------------------------------------------------
    # สรุปสำหรับการตรวจ watchdog_heartbeat
    # ------------------------------------------------------------------
    @api.model
    def _heartbeat_summary(self):
        """สรุปความสดของ heartbeat ทุกตัว: อายุมากสุด / จำนวนที่ขาดตอน / สถานะแย่สุด."""
        watchdogs = self.search([("active", "=", True)])
        ages = [w.heartbeat_age_minutes for w in watchdogs if w.heartbeat_age_minutes >= 0]
        worst_age = max(ages) if ages else 0
        stale = [w for w in watchdogs if w._heartbeat_state() in ("warning", "critical")]
        stale_codes = [w.code for w in stale]
        return {
            "count": len(watchdogs),
            "never_seen": len([w for w in watchdogs if not w.last_heartbeat]),
            "worst_age_minutes": worst_age,
            "stale_count": len(stale),
            "stale_codes": stale_codes,
        }
