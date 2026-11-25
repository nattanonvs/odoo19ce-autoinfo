# -*- coding: utf-8 -*-
from odoo import api, fields, models


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

    # ------------------------------------------------------------------
    # Toll / ค่าผ่านทาง (แถวในแท็บ "ค่าผ่านทาง" ของหน้า /odoo/expenses)
    # ------------------------------------------------------------------
    # A toll row is a regular ``hr.expense`` line flagged with
    # ``od19_is_toll`` so it keeps flowing through the normal posting path
    # (the header totals and the journal entries stay consistent). Each row
    # captures one expressway toll segment claimed against the receipts on
    # hand; the net amount is the number of receipts times the amount per
    # receipt.
    od19_is_toll = fields.Boolean(
        string="Toll / ค่าผ่านทาง",
        tracking=True,
        help="ทำเครื่องหมายเมื่อรายการนี้เป็นค่าผ่านทาง (ทางด่วน/ทางพิเศษ) "
             "ที่เบิกตามใบเสร็จในมือ",
    )
    od19_toll_segment_from = fields.Char(string="From / จาก")
    od19_toll_segment_to = fields.Char(string="To / ถึง")
    od19_toll_receipt_no = fields.Char(string="Receipt No / เลขที่ใบเสร็จ")
    od19_toll_receipt_count = fields.Integer(
        string="Receipts / จำนวนใบ", default=1,
    )
    od19_toll_unit_amount = fields.Monetary(
        string="Amount/Receipt / ค่าผ่านทางต่อใบ",
        currency_field="currency_id",
    )
    od19_toll_net_amount = fields.Monetary(
        string="Net Amount / ยอดสุทธิ",
        currency_field="currency_id",
        compute="_compute_od19_toll_net_amount", store=True,
        help="ยอดสุทธิ = จำนวนใบ × ค่าผ่านทางต่อใบ",
    )

    @api.depends("od19_is_toll", "od19_toll_receipt_count",
                 "od19_toll_unit_amount")
    def _compute_od19_toll_net_amount(self):
        for expense in self:
            expense.od19_toll_net_amount = (
                (expense.od19_toll_receipt_count or 0)
                * (expense.od19_toll_unit_amount or 0)
            )

    def _od19_apply_toll_amount(self):
        """Keep quantity / total / description aligned for a toll row."""
        for expense in self:
            if not expense.od19_is_toll:
                continue
            count = expense.od19_toll_receipt_count or 1
            net = ((expense.od19_toll_receipt_count or 0)
                   * (expense.od19_toll_unit_amount or 0))
            vals = {}
            if expense.quantity != count:
                vals["quantity"] = count
            if expense.total_amount != net:
                vals["total_amount"] = net
            if not expense.name:
                label = "ค่าผ่านทาง"
                if (expense.od19_toll_segment_from
                        or expense.od19_toll_segment_to):
                    label = "%s: %s → %s" % (
                        label,
                        expense.od19_toll_segment_from or "",
                        expense.od19_toll_segment_to or "",
                    )
                vals["name"] = label
            if vals:
                expense.with_context(od19_skip_toll_sync=True).write(vals)

    @api.onchange("od19_is_toll", "od19_toll_receipt_count",
                  "od19_toll_unit_amount", "od19_toll_segment_from",
                  "od19_toll_segment_to")
    def _onchange_od19_toll(self):
        self._od19_apply_toll_amount()

    @api.model_create_multi
    def create(self, vals_list):
        expenses = super().create(vals_list)
        expenses.filtered("od19_is_toll")._od19_apply_toll_amount()
        return expenses

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("od19_skip_toll_sync"):
            self.filtered("od19_is_toll")._od19_apply_toll_amount()
        return res
