from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    od19_initials = fields.Char(
        string="Initials",
        size=10,
        help="Salesperson initials used in project job number (e.g. NV for Nattanai Vinyangkoon).",
    )
    project_sale_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Sale Project Job No. Sequence",
        check_company=True,
        help="Sequence used to build the Job Number for Sales-type projects "
             "(Project Type = Sales). The prefix is free-form, e.g. JS%(y)s-.",
    )
