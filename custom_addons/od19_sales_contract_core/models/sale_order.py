from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_contract_id = fields.Many2one(
        "od19.sales.contract",
        string="Sales Contract",
        tracking=True,
    )

    def action_confirm(self):
        for order in self:
            if order.od19_contract_id:
                order._od19_check_contract_budget()
        res = super().action_confirm()
        for order in self:
            if order.od19_contract_id:
                # Trigger recompute of consumed_from_orders
                order.od19_contract_id._compute_consumed_from_orders()
        return res

    def _od19_check_contract_budget(self):
        """Check the contract budget before confirming a sale order.

        Depending on the contract over-limit policy:
        - warn: log a warning but allow confirmation
        - approval: require the user to confirm via message
        - block: raise UserError
        """
        self.ensure_one()
        contract = self.od19_contract_id
        if not contract:
            return
        exceeded, message = contract._od19_check_contract_limit(self.amount_untaxed)
        if not exceeded:
            return
        if contract.over_limit_policy == "block":
            raise UserError(message)
        elif contract.over_limit_policy == "approval":
            # Post a message on the contract for approval
            contract.message_post(
                body=_(
                    "Sale order %s (%.2f) requires budget approval. %s"
                )
                % (self.display_name, self.amount_untaxed, message)
            )
            raise UserError(
                _("Contract budget approval required. %s") % message
            )
        # warn policy: just log a message on the contract
        contract.message_post(
            body=_(
                "Warning: Sale order %s (%.2f) exceeds contract budget. %s"
            )
            % (self.display_name, self.amount_untaxed, message)
        )


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    od19_contract_activity_id = fields.Many2one(
        "od19.sales.contract.activity",
        string="Contract Activity",
        help="Contract activity this order line is linked to.",
    )
