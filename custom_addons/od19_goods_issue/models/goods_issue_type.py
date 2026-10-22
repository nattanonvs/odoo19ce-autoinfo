# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class Od19GoodsIssueType(models.Model):
    _name = "od19.goods.issue.type"
    _description = "Goods Issue Type"
    _order = "name"

    name = fields.Char(
        string="ชื่อประเภท / Type Name",
        required=True,
    )
    code = fields.Char(
        string="รหัส / Code",
        copy=False,
    )
    active = fields.Boolean(
        string="ใช้งาน / Active",
        default=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="บริษัท / Company",
        default=lambda self: self.env.company,
    )
    description = fields.Text(
        string="รายละเอียด / Description",
    )
