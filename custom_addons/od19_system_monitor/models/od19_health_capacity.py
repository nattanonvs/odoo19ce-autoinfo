# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""พยากรณ์ความจุระบบ (P5) — ดิสก์ของฐานข้อมูลและ filestore.

อ่านผลการตรวจย้อนหลังของ ``db_size`` และ ``filestore_size`` แล้วประมาณ
อัตราการเติบโตต่อวัน เพื่อคาดการณ์ล่วงหน้าว่าอีก ``forecast_days`` วัน
ทรัพยากรจะโตถึงเท่าใด — เป็น "อ่านอย่างเดียว" ไม่แก้ข้อมูลใด ๆ
"""

import logging

from odoo import api, fields, models

from .od19_health_common import human_bytes

_logger = logging.getLogger(__name__)

CAPACITY_STATES = [
    ("ok", "ปกติ"),
    ("warning", "เตือน"),
    ("critical", "วิกฤต"),
]


class Od19HealthCapacityWizard(models.TransientModel):
    """หน้าต่างพยากรณ์ความจุ (คำนวณจากผลการตรวจที่เก็บไว้)."""

    _name = "od19.health.capacity.wizard"
    _description = "พยากรณ์ความจุระบบ (OD19)"

    forecast_days = fields.Integer(string="คาดการณ์ล่วงหน้า (วัน)", default=30, required=True)
    generated_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    state = fields.Selection(CAPACITY_STATES, default="ok", readonly=True)

    db_current = fields.Float(digits=(16, 0), readonly=True)
    db_per_day = fields.Float(digits=(16, 0), readonly=True)
    db_forecast = fields.Float(digits=(16, 0), readonly=True)
    db_current_label = fields.Char(readonly=True)
    db_per_day_label = fields.Char(readonly=True)
    db_forecast_label = fields.Char(readonly=True)

    filestore_current = fields.Float(digits=(16, 0), readonly=True)
    filestore_per_day = fields.Float(digits=(16, 0), readonly=True)
    filestore_forecast = fields.Float(digits=(16, 0), readonly=True)
    filestore_current_label = fields.Char(readonly=True)
    filestore_per_day_label = fields.Char(readonly=True)
    filestore_forecast_label = fields.Char(readonly=True)

    sample_days = fields.Integer(readonly=True)
    summary = fields.Text(readonly=True)

    # ------------------------------------------------------------------
    # การคำนวณ
    # ------------------------------------------------------------------
    @api.model
    def _forecast(self, code, days):
        """ประมาณการเติบโตของทรัพยากร ``code`` จากผลการตรวจย้อนหลัง."""
        check = self.env["od19.health.check"].sudo().search(
            [("code", "=", code)], limit=1
        )
        empty = {"current": 0.0, "per_day": 0.0, "forecast": 0.0, "span_days": 0}
        if not check:
            return empty
        results = (
            self.env["od19.health.result"]
            .sudo()
            .search(
                [("check_id", "=", check.id), ("value", ">", 0)],
                order="run_at asc",
            )
        )
        if not results:
            return empty
        current = check.last_value or results[-1].value
        per_day = 0.0
        span_days = 0
        if len(results) >= 2:
            first, last = results[0], results[-1]
            span = (last.run_at - first.run_at).total_seconds() / 86400.0
            span_days = int(round(span))
            if span > 0:
                per_day = (last.value - first.value) / span
        return {
            "current": current,
            "per_day": per_day,
            "forecast": current + per_day * (days or 0),
            "span_days": span_days,
        }

    def _fill(self):
        """คำนวณและเขียนค่าพยากรณ์ลงหน้าต่างปัจจุบัน."""
        self.ensure_one()
        days = self.forecast_days or 30
        db = self._forecast("db_size", days)
        filestore = self._forecast("filestore_size", days)
        self.write(
            {
                "generated_at": fields.Datetime.now(),
                "db_current": db["current"],
                "db_per_day": db["per_day"],
                "db_forecast": db["forecast"],
                "db_current_label": human_bytes(db["current"]),
                "db_per_day_label": "%s/วัน" % human_bytes(db["per_day"]),
                "db_forecast_label": human_bytes(db["forecast"]),
                "filestore_current": filestore["current"],
                "filestore_per_day": filestore["per_day"],
                "filestore_forecast": filestore["forecast"],
                "filestore_current_label": human_bytes(filestore["current"]),
                "filestore_per_day_label": "%s/วัน" % human_bytes(filestore["per_day"]),
                "filestore_forecast_label": human_bytes(filestore["forecast"]),
                "sample_days": max(db["span_days"], filestore["span_days"]),
                "summary": self._summary(db, filestore, days),
                "state": self._state(db, filestore),
            }
        )
        return True

    @api.model
    def _state(self, db, filestore):
        """ประเมินระดับความรุนแรงจากอัตราการเติบโต (เทียบเกณฑ์ประมาณ)."""
        per_day = max(db["per_day"], filestore["per_day"])
        if per_day <= 0:
            return "ok"
        # เกณฑ์หยาบ: โตเกิน 500 MB/วัน = เตือน, เกิน 2 GB/วัน = วิกฤต
        if per_day >= 2 * 1024 ** 3:
            return "critical"
        if per_day >= 500 * 1024 ** 2:
            return "warning"
        return "ok"

    @api.model
    def _summary(self, db, filestore, days):
        lines = [
            "พยากรณ์ล่วงหน้า %s วัน" % days,
            "ฐานข้อมูล: %s -> %s (%.1f MB/วัน)"
            % (
                human_bytes(db["current"]),
                human_bytes(db["forecast"]),
                db["per_day"] / 1024 ** 2,
            ),
            "Filestore: %s -> %s (%.1f MB/วัน)"
            % (
                human_bytes(filestore["current"]),
                human_bytes(filestore["forecast"]),
                filestore["per_day"] / 1024 ** 2,
            ),
        ]
        if not db["span_days"] and not filestore["span_days"]:
            lines.append(
                "หมายเหตุ: ยังมีผลการตรวจไม่พอสำหรับคำนวณอัตราเติบโต "
                "ตัวเลขที่แสดงจึงเป็นค่าปัจจุบันเท่านั้น"
            )
        return "\n".join(lines)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._fill()
        return records

    def action_compute(self):
        """คำนวณใหม่แล้วเปิดหน้าต่างเดิมซ้ำ."""
        self._fill()
        return {
            "type": "ir.actions.act_window",
            "name": "พยากรณ์ความจุระบบ",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
