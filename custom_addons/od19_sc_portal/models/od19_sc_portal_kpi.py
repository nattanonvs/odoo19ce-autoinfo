# -*- coding: utf-8 -*-
"""KPI Card — ค่าการ์ดรายงานที่คำนวณจากข้อมูลจริงโดยไม่ต้องเขียนโค้ด.

ผู้ดูแลกำหนดโมเดลต้นทาง + โดเมน + ชนิดการรวมค่า (count/sum/avg/min/max)
ค่าถูกคำนวณตอนอ่าน (non-stored) ทั้งบนหลังบ้านและบนพอร์ทัล
"""
from odoo import api, fields, models, _
from odoo.exceptions import AccessError
from odoo.tools.safe_eval import (
    safe_eval, datetime as safe_datetime, time as safe_time)

# ชนิดการรวมค่า -> spec ของ _read_group
_AGGREGATE_SPEC = {"sum": "sum", "avg": "avg", "min": "min", "max": "max"}


class Od19ScPortalKpi(models.Model):
    _name = "od19.sc.portal.kpi"
    _description = "Service Center — Portal KPI Card"
    _order = "page_id, sequence, id"

    page_id = fields.Many2one(
        "od19.sc.portal.page", required=True, ondelete="cascade", index=True)
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    target_model = fields.Char(
        required=True, help="โมเดลต้นทาง เช่น maintenance.equipment, helpdesk.ticket")
    domain_filter = fields.Char(
        default="[]", help="โดเมนกรองข้อมูล (Python list) เช่น [('state', '=', 'done')]")
    aggregate = fields.Selection(
        [("count", "Count"), ("sum", "Sum"), ("avg", "Average"),
         ("min", "Minimum"), ("max", "Maximum")],
        default="count", required=True)
    measure_field = fields.Char(
        help="ฟิลด์ที่ใช้วัดค่า — ต้องระบุเมื่อชนิดการรวมไม่ใช่ Count")
    unit = fields.Char(help="หน่วยต่อท้ายค่า เช่น รายการ, ชั่วโมง, %")

    value = fields.Float(compute="_compute_card")
    value_display = fields.Char(compute="_compute_card")
    error = fields.Char(compute="_compute_card")

    # ------------------------------------------------------------------
    # Computation
    # ------------------------------------------------------------------
    @api.depends("target_model", "domain_filter", "aggregate", "measure_field", "unit")
    def _compute_card(self):
        for kpi in self:
            card = kpi._card_values()
            kpi.value = card["value"]
            kpi.value_display = card["value_display"]
            kpi.error = card["error"]

    def _card_values(self):
        """คำนวณค่าการ์ด — คืน dict ที่ทั้ง backend และ portal ใช้ร่วมกัน."""
        self.ensure_one()
        card = {
            "id": self.id,
            "name": self.name,
            "unit": self.unit or "",
            "value": 0.0,
            "value_display": "-",
            "error": "",
        }
        model_name = (self.target_model or "").strip()
        if not model_name:
            card["error"] = _("No source model configured.")
            return card
        if model_name not in self.env:
            card["error"] = _("Unknown model: %s") % model_name
            return card
        model = self.env[model_name].sudo()
        try:
            model.check_access("read")
        except AccessError:
            card["error"] = _("No read access on %s.") % model_name
            return card
        try:
            domain = self._evaluate_domain()
        except Exception:  # noqa: BLE001 — ผู้ดูแลพิมพ์โดเมนเอง
            card["error"] = _("Invalid domain filter.")
            return card
        try:
            value = self._aggregate_value(model, domain)
        except Exception as exc:  # noqa: BLE001 — การ์ดต้องไม่ทำให้หน้าพัง
            card["error"] = _("Computation failed: %s") % exc
            return card
        card["value"] = value
        card["value_display"] = self._format_value(value)
        return card

    def _evaluate_domain(self):
        """ประเมินโดเมนจากข้อความด้วย safe_eval (ผู้ดูแลกำหนดค่าเอง)."""
        self.ensure_one()
        raw = (self.domain_filter or "[]").strip() or "[]"
        domain = safe_eval(raw, {
            "user": self.env.user,
            "uid": self.env.uid,
            "datetime": safe_datetime,
            "date": safe_datetime.date,
            "time": safe_time,
        })
        if not isinstance(domain, (list, tuple)):
            raise ValueError("domain must be a list")
        return list(domain)

    def _aggregate_value(self, model, domain):
        self.ensure_one()
        aggregate = self.aggregate or "count"
        if aggregate == "count":
            return float(model.search_count(domain))
        field_name = (self.measure_field or "").strip()
        if not field_name or field_name not in model._fields:
            raise ValueError(
                _("Measure field '%s' is not available on %s.")
                % (field_name, self.target_model))
        spec = "%s:%s" % (field_name, _AGGREGATE_SPEC.get(aggregate, "sum"))
        rows = model._read_group(domain, [], [spec], limit=1)
        return float(rows[0][0] or 0.0) if rows and rows[0] else 0.0

    def _format_value(self, value):
        self.ensure_one()
        if float(value).is_integer():
            text = "{:,}".format(int(value))
        else:
            text = "{:,.2f}".format(value)
        return "%s %s" % (text, self.unit) if self.unit else text
