# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


# Frequency used by both the activity master and the plan lines.
FREQUENCY = [
    ("monthly", "รายเดือน"),
    ("quarterly", "รายไตรมาส"),
    ("semi_annual", "ครึ่งปี"),
    ("annual", "รายปี"),
    ("ad_hoc", "ตามความจำเป็น"),
]


class IsoPlanActivityType(models.Model):
    """รายการกิจกรรม ISO มาตรฐาน (editable master list).

    These are the standard recurring ISO activities (internal audit,
    management review, training, ...) that can be added to an annual plan.
    """

    _name = "od19.iso.plan.activity.type"
    _description = "ISO Plan Activity Type"
    _order = "sequence, name"

    name = fields.Char(string="ชื่อกิจกรรม", required=True, translate=True)
    code = fields.Char(string="รหัส")
    default_frequency = fields.Selection(
        FREQUENCY, string="ความถี่เริ่มต้น", default="annual"
    )
    description = fields.Text(string="คำอธิบาย")
    sequence = fields.Integer(string="ลำดับ", default=10)
    active = fields.Boolean(string="ใช้งาน", default=True)

    _name_uniq = models.Constraint(
        "unique(name)",
        "ชื่อกิจกรรมนี้มีอยู่แล้ว",
    )
