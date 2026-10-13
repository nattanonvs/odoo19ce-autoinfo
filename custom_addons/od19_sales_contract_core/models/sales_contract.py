from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19SalesContract(models.Model):
    _name = "od19.sales.contract"
    _description = "Sales Master Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True)
    od19_project_id = fields.Many2one("project.project", required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(tracking=True)
    limit_amount = fields.Float(required=True, tracking=True)
    consumed_amount = fields.Float(
        compute="_compute_consumed_amount", store=True, tracking=True
    )
    consumed_from_orders = fields.Float(
        compute="_compute_consumed_from_orders",
        store=True,
        help="Sum of confirmed sale order amounts linked to this contract.",
    )
    over_limit_policy = fields.Selection(
        [("warn", "Warn"), ("approval", "Approval"), ("block", "Block")],
        default="warn",
        required=True,
    )
    contract_activity_ids = fields.One2many(
        "od19.sales.contract.activity", "contract_id"
    )
    amendment_ids = fields.One2many(
        "od19.sales.contract.amendment", "contract_id"
    )

    @api.depends(
        "contract_activity_ids.amount_to_consume",
        "consumed_from_orders",
    )
    def _compute_consumed_amount(self):
        for contract in self:
            activity_amount = sum(
                contract.contract_activity_ids.mapped("amount_to_consume")
            )
            contract.consumed_amount = activity_amount + contract.consumed_from_orders

    @api.depends()
    def _compute_consumed_from_orders(self):
        for contract in self:
            orders = self.env["sale.order"].search(
                [
                    ("od19_contract_id", "=", contract.id),
                    ("state", "=", "sale"),
                ]
            )
            contract.consumed_from_orders = sum(orders.mapped("amount_untaxed"))

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for contract in self:
            if (
                contract.start_date
                and contract.end_date
                and contract.end_date < contract.start_date
            ):
                raise ValidationError(
                    _("Contract end date cannot be earlier than start date.")
                )

    def action_approve(self):
        for contract in self:
            if contract.state != "draft":
                raise UserError(
                    _("Only draft contracts can be approved.")
                )
            contract.state = "approved"
        return True

    def action_activate(self):
        for contract in self:
            if contract.state not in ("approved", "active"):
                raise UserError(
                    _("Only approved contracts can be activated.")
                )
            contract.state = "active"
        return True

    def action_close(self):
        for contract in self:
            if contract.state not in ("approved", "active"):
                raise UserError(
                    _("Only approved or active contracts can be closed.")
                )
            contract.state = "closed"
        return True

    def action_draft(self):
        for contract in self:
            if contract.state != "closed":
                raise UserError(
                    _("Only closed contracts can be reset to draft.")
                )
            contract.state = "draft"
        return True

    def _od19_check_contract_limit(self, order_amount):
        """Check whether adding order_amount would exceed the contract limit.

        Returns a tuple (exceeded, message).
        """
        self.ensure_one()
        projected = self.consumed_amount + order_amount
        exceeded = projected > self.limit_amount
        message = False
        if exceeded:
            message = _(
                "Contract %s would exceed its limit (projected %.2f > limit %.2f)."
            ) % (self.name, projected, self.limit_amount)
        return exceeded, message


class Od19SalesContractActivity(models.Model):
    _name = "od19.sales.contract.activity"
    _description = "Sales Contract Activity"

    name = fields.Char(required=True)
    contract_id = fields.Many2one(
        "od19.sales.contract", required=True, ondelete="cascade"
    )
    amount_to_consume = fields.Float(required=True)

    @api.constrains("amount_to_consume", "contract_id")
    def _check_contract_limit(self):
        for activity in self:
            existing_amount = sum(
                (activity.contract_id.contract_activity_ids - activity).mapped(
                    "amount_to_consume"
                )
            )
            projected = (
                existing_amount
                + activity.amount_to_consume
                + activity.contract_id.consumed_from_orders
            )
            if (
                activity.contract_id.over_limit_policy == "block"
                and projected > activity.contract_id.limit_amount
            ):
                raise ValidationError(
                    _("Contract activity exceeds blocked contract limit.")
                )


class Od19SalesContractAmendment(models.Model):
    _name = "od19.sales.contract.amendment"
    _description = "Sales Contract Amendment"

    name = fields.Char(required=True)
    contract_id = fields.Many2one(
        "od19.sales.contract", required=True, ondelete="cascade"
    )
    added_limit_amount = fields.Float(
        string="Added Limit Amount",
        help="Amount to add to the contract limit.",
    )
    note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        amendments = super().create(vals_list)
        for amendment in amendments:
            if amendment.added_limit_amount:
                amendment.contract_id.limit_amount = (
                    amendment.contract_id.limit_amount
                    + amendment.added_limit_amount
                )
        return amendments

    def write(self, vals):
        if "added_limit_amount" in vals:
            for amendment in self:
                old = amendment.added_limit_amount or 0.0
                new = vals["added_limit_amount"] or 0.0
                delta = new - old
                if delta:
                    amendment.contract_id.limit_amount = (
                        amendment.contract_id.limit_amount + delta
                    )
        return super().write(vals)
