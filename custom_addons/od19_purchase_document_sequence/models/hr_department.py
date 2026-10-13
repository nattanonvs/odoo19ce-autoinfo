from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    pr_sequence_id = fields.Many2one(
        "ir.sequence",
        string="PR Sequence",
        check_company=True,
        help="Purchase Request sequence for this department. "
        "If set, PRs created by this department will use this sequence.",
    )
    po_sequence_id = fields.Many2one(
        "ir.sequence",
        string="PO Sequence",
        check_company=True,
        help="Purchase Order sequence for this department. "
        "If set, POs created by this department will use this sequence.",
    )
