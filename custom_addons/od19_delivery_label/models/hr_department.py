# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    code = fields.Char(
        string="Department Code",
        copy=False,
        help="Short code for the department used on delivery labels and "
        "picking references (e.g. IA, BA, TA, DES, FA).",
    )
