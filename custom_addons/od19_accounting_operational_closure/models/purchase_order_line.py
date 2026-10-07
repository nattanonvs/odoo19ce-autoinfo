from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_service_acceptance_required = fields.Boolean(
        string="Service Acceptance Required",
        compute="_compute_od19_service_acceptance_required",
        store=True,
        readonly=True,
    )
    od19_service_accepted = fields.Boolean(
        string="Service Accepted",
        default=False,
    )

    @api.depends("od19_requires_service_acceptance")
    def _compute_od19_service_acceptance_required(self):
        for line in self:
            line.od19_service_acceptance_required = bool(
                line.od19_requires_service_acceptance
            )

    def action_od19_accept_service(self):
        self.filtered("od19_service_acceptance_required").write(
            {"od19_service_accepted": True}
        )
