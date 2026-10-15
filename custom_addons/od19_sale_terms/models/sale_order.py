from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_price_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Price Terms / ราคาการขาย",
        domain=[("term_type", "=", "price")],
        tracking=True,
    )
    od19_delivery_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Delivery Terms / เงื่อนไขการจัดส่ง",
        domain=[("term_type", "=", "delivery")],
        tracking=True,
    )
    od19_payment_product_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Payment Terms (Product) / เงื่อนไขชำระเงินสินค้า",
        domain=[("term_type", "=", "payment_product")],
        tracking=True,
    )
    od19_payment_engineering_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Payment Terms (Engineering) / เงื่อนไขชำระเงินวิศวกรรม",
        domain=[("term_type", "=", "payment_engineering")],
        tracking=True,
    )
    od19_validity_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Validity Terms / ระยะเวลาความถูกต้อง",
        domain=[("term_type", "=", "validity")],
        tracking=True,
    )
    od19_warranty_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Warranty Terms / การรับประกัน",
        domain=[("term_type", "=", "warranty")],
        tracking=True,
    )
    od19_credit_term_id = fields.Many2one(
        "od19.sale.term.template",
        string="Credit Terms / เครดิต",
        domain=[("term_type", "=", "credit")],
        tracking=True,
    )
    od19_terms_text = fields.Text(
        string="Terms Text / ข้อความเงื่อนไขทั้งหมด",
        compute="_compute_od19_terms_text",
        help="Concatenated text of all selected term templates for report display.",
    )

    @api.depends(
        "od19_price_term_id.content",
        "od19_delivery_term_id.content",
        "od19_payment_product_term_id.content",
        "od19_payment_engineering_term_id.content",
        "od19_validity_term_id.content",
        "od19_warranty_term_id.content",
        "od19_credit_term_id.content",
    )
    def _compute_od19_terms_text(self):
        """Concatenate the content of every selected term template.

        Templates are concatenated in a fixed order (price, delivery,
        payment product, payment engineering, validity, warranty, credit)
        so the resulting block is deterministic regardless of the order in
        which the user selected them.
        """
        term_fields = (
            "od19_price_term_id",
            "od19_delivery_term_id",
            "od19_payment_product_term_id",
            "od19_payment_engineering_term_id",
            "od19_validity_term_id",
            "od19_warranty_term_id",
            "od19_credit_term_id",
        )
        for order in self:
            parts = []
            for field_name in term_fields:
                template = order[field_name]
                if template and template.content:
                    parts.append(template.content.strip())
            order.od19_terms_text = "\n\n".join(parts) if parts else False
