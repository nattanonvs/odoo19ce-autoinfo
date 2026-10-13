# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class DncnReason(models.Model):
    _name = "account.move.dncn.reason"
    _description = "DN/CN Reason"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    description = fields.Text(string="Description")
    active = fields.Boolean(default=True)
