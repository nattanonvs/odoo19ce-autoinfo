from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    od19_initials = fields.Char(
        string="Initials",
        size=10,
        help="Salesperson initials used in project job number (e.g. NV for Nattanai Vinyangkoon).",
    )
