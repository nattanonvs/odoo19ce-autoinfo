from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_billing_readiness_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting", "Waiting Evidence"),
            ("ready", "Ready"),
            ("billed", "Billed"),
        ],
        string="Billing Readiness",
        compute="_compute_od19_billing_readiness_state",
        store=True,
    )
    od19_evidence_ids = fields.One2many(
        "od19.billing.evidence",
        "sale_order_id",
        string="Billing Evidence",
    )

    @api.depends(
        "state",
        "invoice_status",
        "od19_evidence_ids.is_verified",
        "od19_evidence_ids.evidence_type_id.required_for_billing",
    )
    def _compute_od19_billing_readiness_state(self):
        for order in self:
            # Draft quotations are in draft state
            if order.state in ("draft", "sent"):
                order.od19_billing_readiness_state = "draft"
                continue
            # Already invoiced orders are billed
            if order.invoice_status == "invoiced":
                order.od19_billing_readiness_state = "billed"
                continue
            # Check if all required evidence is verified
            required_types = self.env["od19.billing.evidence.type"].search(
                [("required_for_billing", "=", True)]
            )
            if not required_types:
                # No required evidence types configured -> ready
                order.od19_billing_readiness_state = "ready"
                continue
            verified_required = order.od19_evidence_ids.filtered(
                lambda rec: rec.evidence_type_id.required_for_billing
                and rec.is_verified
            )
            order.od19_billing_readiness_state = (
                "ready" if verified_required else "waiting"
            )

    def _create_invoices(self, grouped=False, final=False, date=None):
        # Block invoice creation if billing evidence is not ready
        for order in self:
            if order.od19_billing_readiness_state not in ("ready", "billed"):
                raise UserError(
                    _(
                        "Cannot create invoice for sale order '%s': "
                        "billing evidence is not ready (state: %s). "
                        "Please verify all required billing evidence."
                    )
                    % (order.display_name, order.od19_billing_readiness_state)
                )
        return super()._create_invoices(grouped=grouped, final=final, date=date)
