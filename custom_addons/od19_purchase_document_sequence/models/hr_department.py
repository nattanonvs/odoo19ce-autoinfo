from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    code = fields.Char(
        string="Department Code",
        copy=False,
        help="Short code for the department used in document numbering "
        "(e.g. IA, BA, TA, DES, FA).",
    )
    pr_sequence_id = fields.Many2one(
        "ir.sequence",
        string="PR Sequence",
        check_company=True,
        help="Purchase Request sequence for this department. "
        "If set, PRs created by this department will use this sequence.",
    )
    po_sequence_id = fields.Many2one(
        "ir.sequence",
        string="PO Sequence (Local)",
        check_company=True,
        help="Purchase Order sequence for local purchases. "
        "If set, local POs created by this department will use this sequence.",
    )
    po_indent_sequence_id = fields.Many2one(
        "ir.sequence",
        string="PO Sequence (Indent/Import)",
        check_company=True,
        help="Purchase Order sequence for indent/import purchases. "
        "If set, indent POs created by this department will use this sequence.",
    )
