from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountYearEndClosing(models.TransientModel):
    _name = "account.year.end.closing"
    _description = "Year-End Closing Wizard"

    fiscal_year_id = fields.Many2one(
        "account.fiscal.year",
        string="Fiscal Year",
        required=True,
    )
    retained_earnings_account_id = fields.Many2one(
        "account.account",
        string="Retained Earnings Account",
        required=True,
        domain="[('account_type', '=', 'equity')]",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
    )
    date = fields.Date(
        string="Closing Date",
        required=True,
        default=fields.Date.context_today,
    )

    def action_close_fiscal_year(self):
        self.ensure_one()
        fy = self.fiscal_year_id
        if fy.state != "open":
            raise ValidationError(
                _("Fiscal year must be in 'Open' state to close.")
            )

        # Get all income and expense accounts
        income_accounts = self.env["account.account"].search(
            [("account_type", "=", "income")]
        )
        expense_accounts = self.env["account.account"].search(
            [("account_type", "=", "expense")]
        )

        # Compute balances for the fiscal year
        move_lines = self.env["account.move.line"].search(
            [
                ("date", ">=", fy.date_from),
                ("date", "<=", fy.date_to),
                ("account_id", "in", (income_accounts | expense_accounts).ids),
                ("parent_state", "=", "posted"),
            ]
        )

        total_credit = 0.0
        total_debit = 0.0
        account_balances = {}
        for line in move_lines:
            account_id = line.account_id.id
            if account_id not in account_balances:
                account_balances[account_id] = 0.0
            account_balances[account_id] += line.credit - line.debit

        # Create closing entry
        lines = []
        for account_id, balance in account_balances.items():
            if abs(balance) < 0.001:
                continue
            account = self.env["account.account"].browse(account_id)
            if balance > 0:
                # Credit balance (income) - debit to close
                lines.append(
                    (
                        0,
                        0,
                        {
                            "account_id": account_id,
                            "debit": balance,
                            "credit": 0.0,
                            "name": _("Year-end closing"),
                        },
                    )
                )
                total_debit += balance
            else:
                # Debit balance (expense) - credit to close
                lines.append(
                    (
                        0,
                        0,
                        {
                            "account_id": account_id,
                            "debit": 0.0,
                            "credit": abs(balance),
                            "name": _("Year-end closing"),
                        },
                    )
                )
                total_credit += abs(balance)

        # Retained earnings line
        net_balance = total_debit - total_credit
        if net_balance > 0:
            lines.append(
                (
                    0,
                    0,
                    {
                        "account_id": self.retained_earnings_account_id.id,
                        "debit": 0.0,
                        "credit": net_balance,
                        "name": _("Year-end closing - Net income"),
                    },
                )
            )
        elif net_balance < 0:
            lines.append(
                (
                    0,
                    0,
                    {
                        "account_id": self.retained_earnings_account_id.id,
                        "debit": abs(net_balance),
                        "credit": 0.0,
                        "name": _("Year-end closing - Net loss"),
                    },
                )
            )

        if lines:
            move = self.env["account.move"].create(
                {
                    "date": self.date,
                    "journal_id": self.journal_id.id,
                    "ref": _("Year-end closing - %s") % fy.name,
                    "line_ids": lines,
                }
            )
            move.action_post()

        # Close the fiscal year
        fy.action_close()

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id if lines else False,
            "view_mode": "form",
            "target": "current",
        } if lines else True
