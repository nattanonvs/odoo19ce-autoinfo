from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PettyCashFund(models.Model):
    _name = "petty.cash.fund"
    _description = "Petty Cash Fund"
    _order = "name"

    name = fields.Char(required=True)
    account_id = fields.Many2one(
        "account.account",
        string="Petty Cash Account",
        required=True,
        domain="[('account_type', '=', 'asset_cash')]",
    )
    amount = fields.Monetary(
        string="Initial Amount",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    balance = fields.Monetary(
        string="Current Balance",
        currency_field="currency_id",
        compute="_compute_balance",
        store=True,
    )
    state = fields.Selection(
        [
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        default="active",
    )
    transaction_ids = fields.One2many(
        "petty.cash.transaction",
        "fund_id",
        string="Transactions",
    )

    @api.depends("amount", "transaction_ids.amount", "transaction_ids.transaction_type", "transaction_ids.state")
    def _compute_balance(self):
        for fund in self:
            balance = fund.amount
            for transaction in fund.transaction_ids.filtered(
                lambda t: t.state == "posted"
            ):
                if transaction.transaction_type == "expense":
                    balance -= transaction.amount
                elif transaction.transaction_type == "replenishment":
                    balance += transaction.amount
            fund.balance = balance

    @api.constrains("amount")
    def _check_amount(self):
        for fund in self:
            if fund.amount < 0:
                raise ValidationError(
                    _("Initial amount cannot be negative.")
                )

    def action_deactivate(self):
        for fund in self:
            fund.state = "inactive"

    def action_activate(self):
        for fund in self:
            fund.state = "active"
