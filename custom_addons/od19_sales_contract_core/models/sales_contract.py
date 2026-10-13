from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Od19SalesContract(models.Model):
    _name = "od19.sales.contract"
    _description = "Sales Master Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    od19_project_id = fields.Many2one("project.project", required=True, tracking=True)
    limit_amount = fields.Float(required=True)
    consumed_amount = fields.Float(compute="_compute_consumed_amount", store=True)
    over_limit_policy = fields.Selection(
        [("warn", "Warn"), ("approval", "Approval"), ("block", "Block")],
        default="warn",
        required=True,
    )
    contract_activity_ids = fields.One2many("od19.sales.contract.activity", "contract_id")
    amendment_ids = fields.One2many("od19.sales.contract.amendment", "contract_id")

    @api.depends("contract_activity_ids.amount_to_consume")
    def _compute_consumed_amount(self):
        for contract in self:
            contract.consumed_amount = sum(contract.contract_activity_ids.mapped("amount_to_consume"))


class Od19SalesContractActivity(models.Model):
    _name = "od19.sales.contract.activity"
    _description = "Sales Contract Activity"

    name = fields.Char(required=True)
    contract_id = fields.Many2one("od19.sales.contract", required=True, ondelete="cascade")
    amount_to_consume = fields.Float(required=True)

    @api.constrains("amount_to_consume", "contract_id")
    def _check_contract_limit(self):
        for activity in self:
            existing_amount = sum(
                (activity.contract_id.contract_activity_ids - activity).mapped("amount_to_consume")
            )
            projected = existing_amount + activity.amount_to_consume
            if (
                activity.contract_id.over_limit_policy == "block"
                and projected > activity.contract_id.limit_amount
            ):
                raise ValidationError("Contract activity exceeds blocked contract limit.")


class Od19SalesContractAmendment(models.Model):
    _name = "od19.sales.contract.amendment"
    _description = "Sales Contract Amendment"

    name = fields.Char(required=True)
    contract_id = fields.Many2one("od19.sales.contract", required=True, ondelete="cascade")
    added_limit_amount = fields.Float()
    note = fields.Text()
