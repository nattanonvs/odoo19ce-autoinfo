# -*- coding: utf-8 -*-
from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    od19_claim_id = fields.Many2one(
        "od19.expense.claim",
        string="Expense Claim / ใบเบิก",
        copy=False,
        index="btree_not_null",
        ondelete="cascade",
        help="หัวใบเบิกค่าใช้จ่ายที่บรรทัดนี้สังกัด",
    )
    od19_hr_advance_id = fields.Many2one(
        "od19.expense.claim",
        string="Cleared Against Advance / ใบทดรองที่เคลียร์",
        copy=False,
        index="btree_not_null",
        help="ใบทดรอง/เงินสดย่อยที่ค่าใช้จ่ายนี้ถูกนำไปเคลียร์",
    )
