# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "od19.document.pull.mixin"]
