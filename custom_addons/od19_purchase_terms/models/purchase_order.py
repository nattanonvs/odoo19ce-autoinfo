from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_warranty_term_id = fields.Many2one(
        "od19.purchase.term.template",
        string="Warranty / การรับประกัน",
        domain=[("term_type", "=", "warranty")],
    )
    od19_delivery_to_term_id = fields.Many2one(
        "od19.purchase.term.template",
        string="Delivery To / สถานที่จัดส่ง",
        domain=[("term_type", "=", "delivery_to")],
    )
    od19_payment_term_id = fields.Many2one(
        "od19.purchase.term.template",
        string="Payment Term / เงื่อนไขการชำระเงิน",
        domain=[("term_type", "=", "payment_term")],
    )
    od19_shipment_term_id = fields.Many2one(
        "od19.purchase.term.template",
        string="Shipment / เงื่อนไขการขนส่ง",
        domain=[("term_type", "=", "shipment")],
    )
    od19_weight_term_id = fields.Many2one(
        "od19.purchase.term.template",
        string="Weight / น้ำหนัก",
        domain=[("term_type", "=", "weight")],
    )
    od19_terms_text = fields.Text(
        string="Terms Text / ข้อความเงื่อนไขทั้งหมด",
        compute="_compute_od19_terms_text",
        help="Concatenated text of all selected term templates for report display.",
    )

    @api.depends(
        "od19_warranty_term_id.content",
        "od19_delivery_to_term_id.content",
        "od19_payment_term_id.content",
        "od19_shipment_term_id.content",
        "od19_weight_term_id.content",
    )
    def _compute_od19_terms_text(self):
        """Concatenate the content of every selected term template.

        Templates are concatenated in a fixed order (warranty, delivery to,
        payment term, shipment, weight) so the resulting block is
        deterministic regardless of the order in which the user selected
        them.
        """
        term_fields = (
            "od19_warranty_term_id",
            "od19_delivery_to_term_id",
            "od19_payment_term_id",
            "od19_shipment_term_id",
            "od19_weight_term_id",
        )
        for order in self:
            parts = []
            for field_name in term_fields:
                template = order[field_name]
                if template and template.content:
                    parts.append(template.content.strip())
            order.od19_terms_text = "\n\n".join(parts) if parts else False
