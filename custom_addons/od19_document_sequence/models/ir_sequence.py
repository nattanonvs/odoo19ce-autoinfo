# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


THAI_MONTH_FULL = [
    "",
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
]

THAI_MONTH_SHORT = [
    "",
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
]


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def _interpolation_dict(self, date=None, date_range=None):
        res = super()._interpolation_dict(date=date, date_range=date_range)

        def _month_names(year_key, month_key):
            month_int = int(res.get(month_key, "0") or 0)
            full = THAI_MONTH_FULL[month_int] if 1 <= month_int <= 12 else ""
            short = THAI_MONTH_SHORT[month_int] if 1 <= month_int <= 12 else ""
            return full, short

        # Current / effective date
        full, short = _month_names("year", "month")
        res["month_th"] = full
        res["month_th_short"] = short

        # Range date
        full, short = _month_names("range_year", "range_month")
        res["range_month_th"] = full
        res["range_month_th_short"] = short

        # Current (now) date
        full, short = _month_names("current_year", "current_month")
        res["current_month_th"] = full
        res["current_month_th_short"] = short

        # Range end date
        if res.get("range_end_month"):
            full, short = _month_names("range_end_year", "range_end_month")
            res["range_end_month_th"] = full
            res["range_end_month_th_short"] = short

        return res
