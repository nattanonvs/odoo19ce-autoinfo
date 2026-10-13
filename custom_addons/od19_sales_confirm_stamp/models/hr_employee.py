from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    signature = fields.Image(
        string="Signature",
        max_width=512,
        max_height=128,
        attachment=True,
        help="Handwritten signature image shown in the CONFIRMED stamp on printed quotations.",
    )
