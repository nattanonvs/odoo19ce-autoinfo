from odoo import api, fields, models, _


class AccountAssetDepreciationLine(models.Model):
    _name = "account.asset.depreciation.line"
    _description = "Asset Depreciation Line"
    _order = "sequence"

    asset_id = fields.Many2one(
        "account.asset",
        string="Asset",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Description", required=True)
    sequence = fields.Integer(default=1)
    amount = fields.Monetary(
        string="Depreciation Amount",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="asset_id.currency_id",
        store=True,
    )
    depreciation_date = fields.Date(
        string="Depreciation Date",
        required=True,
    )
    move_id = fields.Many2one(
        "account.move",
        string="Depreciation Entry",
        readonly=True,
        copy=False,
    )
    move_check = fields.Boolean(
        string="Posted",
        compute="_compute_move_check",
        store=True,
    )

    @api.depends("move_id")
    def _compute_move_check(self):
        for line in self:
            line.move_check = bool(line.move_id)

    def create_move(self):
        self.ensure_one()
        if self.move_id:
            return
        asset = self.asset_id
        if not asset.journal_id:
            return
        move = self.env["account.move"].create(
            {
                "date": self.depreciation_date,
                "journal_id": asset.journal_id.id,
                "ref": self.name,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": asset.expense_account_id.id,
                            "debit": self.amount,
                            "credit": 0.0,
                            "name": self.name,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": asset.depreciation_account_id.id,
                            "debit": 0.0,
                            "credit": self.amount,
                            "name": self.name,
                        },
                    ),
                ],
            }
        )
        move.action_post()
        self.move_id = move
