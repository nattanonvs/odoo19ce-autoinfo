from odoo import fields, models


class Od19PurchaseTermTemplate(models.Model):
    _name = "od19.purchase.term.template"
    _description = "Purchase Term Template"
    _order = "term_type, name"

    name = fields.Char(
        string="Template Name / ชื่อแม่แบบ",
        required=True,
    )
    term_type = fields.Selection(
        selection=[
            ("warranty", "การรับประกัน / Warranty"),
            ("delivery_to", "สถานที่จัดส่ง / Delivery To"),
            ("payment_term", "เงื่อนไขการชำระเงิน / Payment Term"),
            ("shipment", "เงื่อนไขการขนส่ง / Shipment"),
            ("weight", "น้ำหนัก / Weight"),
        ],
        string="Term Type / ประเภทเงื่อนไข",
        required=True,
        index=True,
    )
    content = fields.Text(
        string="Content / เนื้อหาเงื่อนไข",
        help="The actual terms text that will be inserted into the purchase order.",
    )
    active = fields.Boolean(
        string="Active / ใช้งาน",
        default=True,
    )

    _od19_name_term_type_unique = models.Constraint(
        "unique(name, term_type)",
        "A template with the same name and term type already exists.",
    )
