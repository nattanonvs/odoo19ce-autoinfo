from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    quotation_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Quotation Sequence",
        check_company=True,
        help="Quotation sequence for this department. "
        "If set, quotations created by this department will use this sequence.",
    )
