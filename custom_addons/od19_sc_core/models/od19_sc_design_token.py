# -*- coding: utf-8 -*-
"""Design Engine — design tokens → CSS ผ่าน ir.attachment + ir.asset"""
from odoo import fields, models


class Od19ScDesignToken(models.Model):
    _name = "od19.sc.design.token"
    _description = "Service Center — Design Token"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("od19.sc.template", required=True, ondelete="cascade")
    key = fields.Char(required=True, help="ชื่อตัวแปร CSS เช่น --sc-primary")
    value = fields.Char(required=True, help="ค่าของตัวแปร เช่น #7c5cff หรือ 8px")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
