from odoo import fields, models


class Od19BillingEvidenceType(models.Model):
    _name = "od19.billing.evidence.type"
    _description = "Billing Evidence Type"

    name = fields.Char(required=True)
    trigger_kind = fields.Selection(
        [("delivery", "Delivery"), ("service", "Service"), ("other", "Other")],
        required=True,
    )
    required_for_billing = fields.Boolean(default=True)


class Od19BillingEvidence(models.Model):
    _name = "od19.billing.evidence"
    _description = "Billing Evidence"

    name = fields.Char(required=True)
    sale_order_id = fields.Many2one("sale.order", ondelete="cascade")
    contract_activity_id = fields.Many2one("od19.sales.contract.activity", ondelete="cascade")
    evidence_type_id = fields.Many2one("od19.billing.evidence.type", required=True, ondelete="restrict")
    is_verified = fields.Boolean(default=False)
    attachment_count = fields.Integer(default=0)
