from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    _OD19_ACCEPTANCE_WRITE_CTX = "od19_allow_service_acceptance_write"
    _OD19_ACCEPTANCE_RESET_FIELDS = {
        "date_planned",
        "name",
        "price_unit",
        "product_id",
        "product_qty",
        "product_uom_id",
        "taxes_id",
    }

    od19_service_acceptance_required = fields.Boolean(
        string="Service Acceptance Required",
        compute="_compute_od19_service_acceptance_required",
        store=True,
        readonly=True,
    )
    od19_service_accepted = fields.Boolean(
        string="Service Accepted",
        default=False,
        copy=False,
    )

    @api.depends("od19_requires_service_acceptance")
    def _compute_od19_service_acceptance_required(self):
        for line in self:
            line.od19_service_acceptance_required = bool(
                line.od19_requires_service_acceptance
            )

    def write(self, vals):
        if (
            "od19_service_accepted" in vals
            and not self.env.context.get(self._OD19_ACCEPTANCE_WRITE_CTX)
        ):
            raise UserError(
                _("Service acceptance can only be changed through the acceptance action.")
            )
        reset_acceptance = (
            not self.env.context.get(self._OD19_ACCEPTANCE_WRITE_CTX)
            and bool(self._OD19_ACCEPTANCE_RESET_FIELDS.intersection(vals))
        )
        result = super().write(vals)
        if reset_acceptance:
            accepted_lines = self.filtered("od19_service_accepted")
            if accepted_lines:
                super(
                    PurchaseOrderLine,
                    accepted_lines.with_context(
                        **{self._OD19_ACCEPTANCE_WRITE_CTX: True}
                    ),
                ).write({"od19_service_accepted": False})
        return result

    def action_od19_accept_service(self):
        service_lines = self.filtered("od19_service_acceptance_required")
        blocked_lines = service_lines.filtered(
            lambda line: not line.order_id._od19_is_committed_for_service_acceptance()
        )
        if blocked_lines:
            raise UserError(
                _(
                    "Service acceptance is only available after the purchase order is committed."
                )
            )
        service_lines.with_context(**{self._OD19_ACCEPTANCE_WRITE_CTX: True}).write(
            {"od19_service_accepted": True}
        )
