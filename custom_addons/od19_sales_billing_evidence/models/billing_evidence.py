from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
    contract_activity_id = fields.Many2one(
        "od19.sales.contract.activity", ondelete="cascade"
    )
    evidence_type_id = fields.Many2one(
        "od19.billing.evidence.type", required=True, ondelete="restrict"
    )
    is_verified = fields.Boolean(default=False)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "od19_billing_evidence_attachment_rel",
        "evidence_id",
        "attachment_id",
        string="Attachments",
        help="Supporting documents for this billing evidence.",
    )
    attachment_count = fields.Integer(
        compute="_compute_attachment_count",
        string="Number of Attachments",
        store=True,
    )

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for evidence in self:
            evidence.attachment_count = len(evidence.attachment_ids)

    @api.constrains("is_verified", "attachment_ids")
    def _check_verified_has_attachment(self):
        for evidence in self:
            if evidence.is_verified and not evidence.attachment_ids:
                raise ValidationError(
                    _(
                        "Billing evidence '%s' cannot be verified "
                        "without at least one attachment."
                    )
                    % evidence.name
                )
