# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models


class Od19DocumentPullMixin(models.AbstractModel):
    _name = "od19.document.pull.mixin"
    _description = "OD19 Document Pull Mixin"

    def _od19_pull_source_specs(self):
        return []


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "od19.document.pull.mixin"]
