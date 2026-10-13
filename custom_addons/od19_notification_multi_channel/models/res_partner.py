from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    line_user_id = fields.Char(
        string="LINE User ID",
        help="LINE User ID for push notifications via LINE Messaging API.",
        copy=False,
    )
