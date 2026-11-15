# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""อนุกรมเวลาของผลการตรวจ (time series) + นโยบายการเก็บ (retention).

ทุกครั้งที่ ``od19.health.check`` รัน จะเกิด 1 แถวที่นี่ ใช้เป็นข้อมูลให้
dashboard (trend) และงาน retention จะลบแถวที่เก่ากว่าระยะที่กำหนด
(ค่าเริ่มต้น 90 วัน ตามข้อเสนอ D6)
"""

import logging
from datetime import timedelta

from odoo import api, fields, models

from .od19_health_common import CHECK_STATES, PARAM_RETENTION_DAYS, SEVERITIES

_logger = logging.getLogger(__name__)


class Od19HealthResult(models.Model):
    """ผลการตรวจสุขภาพระบบ 1 ครั้ง (บันทึกเป็นอนุกรมเวลา)."""

    _name = "od19.health.result"
    _description = "ผลการตรวจสุขภาพระบบ (OD19)"
    _order = "run_at desc, id desc"

    check_id = fields.Many2one(
        "od19.health.check", required=True, ondelete="cascade", index=True
    )
    check_code = fields.Char(related="check_id.code", store=True, index=True)
    category = fields.Selection(related="check_id.category", store=True)
    run_at = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    state = fields.Selection(CHECK_STATES, default="unknown", required=True, index=True)
    severity = fields.Selection(SEVERITIES, default="info", required=True)
    value = fields.Float(digits=(16, 2))
    value_label = fields.Char()
    message = fields.Char()
    details = fields.Json()
    duration_ms = fields.Integer(help="เวลาที่ใช้ตรวจ (มิลลิวินาที)")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    @api.model
    def _cutoff(self):
        """คืนวันหมดอายุตามค่า retention (คืน None ถ้าตั้งเป็น 0 = เก็บตลอด)."""
        days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(PARAM_RETENTION_DAYS, 90)
            or 0
        )
        if days <= 0:
            return None
        return fields.Datetime.now() - timedelta(days=days)

    @api.model
    def _cron_prune(self):
        """ลบผลการตรวจที่เก่ากว่าระยะเก็บ เพื่อไม่ให้ตารางโตไม่จำกัด."""
        cutoff = self._cutoff()
        if cutoff is None:
            return 0
        stale = self.search([("run_at", "<", cutoff)])
        count = len(stale)
        if count:
            stale.unlink()
            _logger.info("ลบผลการตรวจเก่า %d รายการ (ก่อน %s)", count, cutoff)
        return count
