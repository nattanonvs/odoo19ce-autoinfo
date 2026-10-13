# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_analytic_required_account_ids = fields.Many2many(
        "account.account",
        string="Accounts Requiring Analytic",
        help="Journal items on these accounts must have an analytic account.",
    )
    od19_analytic_require_journal_ids = fields.Many2many(
        "account.journal",
        string="Journals Requiring Analytic",
        help="Journal entries in these journals must have analytic accounts "
             "on all lines. Leave empty to check by account only.",
    )
