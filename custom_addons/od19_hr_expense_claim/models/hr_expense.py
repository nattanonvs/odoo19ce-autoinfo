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
