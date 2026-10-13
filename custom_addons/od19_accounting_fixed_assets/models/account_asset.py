from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountAsset(models.Model):
    _name = "account.asset"
    _description = "Fixed Asset"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Asset Name", required=True, tracking=True)
    asset_account_id = fields.Many2one(
        "account.account",
        string="Asset Account",
        required=True,
        domain="[('account_type', 'in', ['asset_fixed', 'asset_current'])]",
    )
    depreciation_account_id = fields.Many2one(
        "account.account",
        string="Accumulated Depreciation Account",
        required=True,
    )
    expense_account_id = fields.Many2one(
        "account.account",
        string="Depreciation Expense Account",
        required=True,
        domain="[('account_type', '=', 'expense')]",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
    )
    value = fields.Monetary(
        string="Gross Value",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    salvage_value = fields.Monetary(
        string="Salvage Value",
        currency_field="currency_id",
        default=0.0,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string="Asset Date",
        required=True,
        default=fields.Date.context_today,
    )
    method = fields.Selection(
        [
            ("linear", "Straight Line"),
        ],
        string="Depreciation Method",
        default="linear",
        required=True,
    )
    method_number = fields.Integer(
        string="Number of Depreciations",
        default=5,
        required=True,
    )
    method_period = fields.Integer(
        string="Period Length (months)",
        default=12,
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Running"),
            ("close", "Closed"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    depreciation_line_ids = fields.One2many(
        "account.asset.depreciation.line",
        "asset_id",
        string="Depreciation Lines",
    )
    note = fields.Text(string="Notes")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    @api.constrains("value")
    def _check_value(self):
        for asset in self:
            if asset.value <= 0:
                raise ValidationError(
                    _("Asset value must be greater than zero.")
                )

    @api.constrains("method_number")
    def _check_method_number(self):
        for asset in self:
            if asset.method_number <= 0:
                raise ValidationError(
                    _("Number of depreciations must be greater than zero.")
                )

    def validate(self):
        for asset in self:
            if asset.state != "draft":
                continue
            asset._compute_depreciation_schedule()
            asset.state = "open"

    def set_to_close(self):
        for asset in self:
            if asset.state != "open":
                continue
            asset.state = "close"

    def set_to_draft(self):
        for asset in self:
            if asset.state != "close":
                continue
            asset.state = "draft"

    def _compute_depreciation_schedule(self):
        self.ensure_one()
        self.depreciation_line_ids.unlink()
        if self.method == "linear":
            depreciable_amount = self.value - self.salvage_value
            if depreciable_amount <= 0:
                return
            period_amount = depreciable_amount / self.method_number
            date = self.date
            for i in range(self.method_number):
                self.env["account.asset.depreciation.line"].create(
                    {
                        "asset_id": self.id,
                        "name": _("Depreciation %s/%s") % (i + 1, self.method_number),
                        "amount": period_amount,
                        "depreciation_date": date,
                        "sequence": i + 1,
                    }
                )
                # Next period
                if self.method_period == 12:
                    date = date.replace(year=date.year + 1)
                else:
                    month = date.month + self.method_period
                    year = date.year
                    while month > 12:
                        month -= 12
                        year += 1
                    date = date.replace(year=year, month=month)
