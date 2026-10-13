# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        """Validate that required analytic accounts are set before posting."""
        for move in self:
            if move.state != "draft":
                continue
            move._od19_check_analytic_required()
        return super().action_post()

    def _od19_check_analytic_required(self):
        """Check that all lines requiring an analytic account have one.

        A line requires an analytic account if:
        - Its account is in the company's analytic-required account list, OR
        - The move's journal is in the company's analytic-required journal list.

        Analytic distribution (analytic_distribution) is the Odoo 17+ way of
        storing analytic allocations on a move line.
        """
        self.ensure_one()
        company = self.company_id
        required_account_ids = company.od19_analytic_required_account_ids.ids
        required_journal_ids = company.od19_analytic_require_journal_ids.ids

        if not required_account_ids and not required_journal_ids:
            return

        journal_requires_analytic = self.journal_id.id in required_journal_ids

        for line in self.line_ids:
            # Skip liquidity / counterpart lines that Odoo auto-creates
            if line.display_type:
                continue
            account_requires = line.account_id.id in required_account_ids
            if not account_requires and not journal_requires_analytic:
                continue
            # Check analytic: either analytic_account_id (legacy) or
            # analytic_distribution (Odoo 17+) must be present.
            has_analytic = bool(line.analytic_distribution) or bool(
                getattr(line, "analytic_account_id", False)
            )
            if not has_analytic:
                raise UserError(_(
                    "Analytic account is required for account '%s' "
                    "(line: %s). Please set an analytic distribution "
                    "before posting."
                ) % (line.account_id.display_name, line.name or line.account_id.code))
