# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class IsoStandard(models.Model):
    _name = "od19.iso.standard"
    _description = "ISO Standard"
    _order = "code"

    name = fields.Char(string="ชื่อมาตรฐาน", required=True)
    code = fields.Char(string="รหัส", required=True, help="เช่น ISO 9001:2015")
    active = fields.Boolean(string="ใช้งาน", default=True)
    description = fields.Text(string="คำอธิบาย")
