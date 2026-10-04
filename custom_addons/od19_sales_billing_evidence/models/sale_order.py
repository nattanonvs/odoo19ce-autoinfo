from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_billing_readiness_state = fields.Selection(
        [("draft", "Draft"), ("waiting", "Waiting Evidence"), ("ready", "Ready"), ("billed", "Billed")],
        compute="_compute_od19_billing_readiness_state",
        store=True,
    )
    od19_evidence_ids = fields.One2many("od19.billing.evidence", "sale_order_id")

    @api.depends("od19_evidence_ids.is_verified", "od19_evidence_ids.evidence_type_id.required_for_billing")
    def _compute_od19_billing_readiness_state(self):
        for order in self:
            required_verified = order.od19_evidence_ids.filtered(
                lambda rec: rec.evidence_type_id.required_for_billing and rec.is_verified
            )
            order.od19_billing_readiness_state = "ready" if required_verified else "waiting"
