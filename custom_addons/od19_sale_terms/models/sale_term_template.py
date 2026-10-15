from odoo import fields, models


class Od19SaleTermTemplate(models.Model):
    _name = "od19.sale.term.template"
    _description = "Sale Term Template"
    _order = "term_type, name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Template Name / ชื่อแม่แบบ",
        required=True,
        tracking=True,
    )
    term_type = fields.Selection(
        selection=[
            ("price", "ราคาการขาย / Price Terms"),
            ("delivery", "เงื่อนไขการจัดส่ง / Delivery Terms"),
            (
                "payment_product",
                "เงื่อนไขชำระเงินสินค้า / Payment Terms (Product)",
            ),
            (
                "payment_engineering",
                "เงื่อนไขชำระเงินวิศวกรรม / Payment Terms (Engineering)",
            ),
            ("validity", "ระยะเวลาความถูกต้อง / Validity Terms"),
            ("warranty", "การรับประกัน / Warranty Terms"),
            ("credit", "เครดิต / Credit Terms"),
        ],
        string="Term Type / ประเภทเงื่อนไข",
        required=True,
        tracking=True,
        index=True,
    )
    content = fields.Text(
        string="Content / เนื้อหาเงื่อนไข",
        tracking=True,
        help="The actual terms text that will be inserted into the quotation.",
    )
    active = fields.Boolean(
        string="Active / ใช้งาน",
        default=True,
        tracking=True,
    )
    note = fields.Text(
        string="Internal Note / หมายเหตุภายใน",
        tracking=True,
    )

    _name_type_unique = models.Constraint(
        "unique(name, term_type)",
        "A template with the same name and term type already exists.",
    )
