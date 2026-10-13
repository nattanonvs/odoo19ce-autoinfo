from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    od19_dept_code = fields.Char(
        string="Department Code",
        size=10,
        help="Short code used in document numbering (e.g. B for BA, T for TA, I for IA, F for FA, D for F/DES).",
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
