# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


class Od19BarcodeScanLog(models.Model):
    """History of every barcode scanned through the mobile camera.

    Kept intentionally lightweight: one row per scan so warehouse operators can
    audit what was scanned, when, where it resolved, and on which transfer.
    """

    _name = "od19.barcode.scan.log"
    _description = "Barcode Scan Log"
    _order = "create_date desc, id desc"

    barcode = fields.Char("Barcode", required=True, index=True)
    matched = fields.Boolean("Matched", default=False)
    scan_type = fields.Selection(
        selection=[
            ("product", "สินค้า"),
            ("lot", "ล็อต/ซีเรียล"),
            ("location", "ตำแหน่งจัดเก็บ"),
            ("package", "หีบห่อ"),
            ("unknown", "ไม่รู้จัก"),
        ],
        string="Type",
        default="unknown",
        index=True,
    )
    res_model = fields.Char("Matched Model")
    res_id = fields.Integer("Matched Record ID")
    res_name = fields.Char("Matched Record")
    product_id = fields.Many2one("product.product", "Product", index=True)
    lot_id = fields.Many2one("stock.lot", "Lot/Serial Number")
    location_id = fields.Many2one("stock.location", "Location")
    package_id = fields.Many2one("stock.package", "Package")
    picking_id = fields.Many2one("stock.picking", "Transfer", index=True)
    quantity = fields.Float("Quantity")
    user_id = fields.Many2one(
        "res.users",
        "Scanned by",
        default=lambda self: self.env.user,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        "Company",
        default=lambda self: self.env.company,
        index=True,
    )
    note = fields.Char("Note")
