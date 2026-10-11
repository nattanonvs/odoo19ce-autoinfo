from odoo import api, fields, models


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    od19_is_credit_term = fields.Boolean(
        string="Credit Term",
        compute="_compute_od19_is_credit_term",
        store=True,
        readonly=False,
        help="Credit terms require an approved customer credit request before selling. "
        "Defaults to True when any line is due after the invoice date; accounting may override.",
    )

    @api.depends("line_ids.nb_days", "line_ids.delay_type")
    def _compute_od19_is_credit_term(self):
        for term in self:
            term.od19_is_credit_term = any(
                line.nb_days > 0 or line.delay_type != "days_after" for line in term.line_ids
            )
