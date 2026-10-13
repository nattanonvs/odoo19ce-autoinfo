# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IsoDocumentCategory(models.Model):
    _name = "od19.iso.document.category"
    _description = "ISO Document Category"
    _order = "prefix"

    name = fields.Char(string="ประเภทเอกสาร", required=True)
    prefix = fields.Char(
        string="คำนำหน้า",
        required=True,
        help="คำนำหน้ารหัสเอกสาร เช่น FM, PROC, WI, REC, MANUAL",
    )
    description = fields.Text(string="คำอธิบาย")
    active = fields.Boolean(string="ใช้งาน", default=True)
