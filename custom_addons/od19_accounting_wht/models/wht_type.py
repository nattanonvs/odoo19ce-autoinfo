from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WHTType(models.Model):
    _name = "wht.type"
    _description = "Withholding Tax Type"
    _order = "percent, name"

    name = fields.Char(required=True)
    percent = fields.Float(string="Percent (%)", required=True)
    account_id = fields.Many2one(
        "account.account",
        string="WHT Payable Account",
        required=True,
        domain="[('account_type', 'in', ['liability_payable', 'liability_current'])]",
    )
    active = fields.Boolean(default=True)

    @api.constrains("percent")
    def _check_percent(self):
        for record in self:
            if record.percent < 0 or record.percent > 100:
                raise ValidationError(
                    "WHT percent must be between 0 and 100."
                )
