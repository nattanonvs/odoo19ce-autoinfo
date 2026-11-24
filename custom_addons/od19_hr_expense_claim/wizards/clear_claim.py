# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Od19ExpenseClaimClear(models.TransientModel):
    """เคลียร์เงินทดรอง/เงินสดย่อยที่จ่ายให้พนักงาน.

    พนักงานนำค่าใช้จ่าย (``hr.expense``) มาเคลียร์กับใบทดรองที่เบิกไป และ
    คืนเงินส่วนที่เหลือ (ถ้ามี) จากนั้นระบบจะสร้างรายการบัญชีเพื่อหักกลบ
    บัญชีลูกหนี้พนักงาน (``advance_account_id``) ให้เป็นศูนย์
    """

    _name = "od19.expense.claim.clear"
    _description = "Clear Expense Claim Advance"

    claim_id = fields.Many2one(
        "od19.expense.claim",
        string="Expense Claim / ใบทดรอง",
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="claim_id.currency_id",
        readonly=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        related="claim_id.employee_id",
        readonly=True,
    )
    advance_account_id = fields.Many2one(
        "account.account",
        string="Employee Advance Account",
        related="claim_id.advance_account_id",
        readonly=True,
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount",
        related="claim_id.remaining_amount",
        currency_field="currency_id",
        readonly=True,
    )
    clear_date = fields.Date(
        string="Clearing Date",
        required=True,
        default=fields.Date.context_today,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
        help="สมุดเงินสด/ธนาคารที่รับเงินคืนจากพนักงาน (ถ้ามีการคืนเงิน)",
    )
    expense_ids = fields.Many2many(
        "hr.expense",
        string="Cleared Expenses",
        help="ค่าใช้จ่ายที่พนักงานนำมาเคลียร์กับเงินทดรองที่เบิกไป",
    )
    returned_amount = fields.Monetary(
        string="Returned Amount",
        currency_field="currency_id",
        default=0.0,
        help="จำนวนเงินที่พนักงานคืนให้บริษัท",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        claim_id = self.env.context.get("default_claim_id")
        if claim_id:
            claim = self.env["od19.expense.claim"].browse(claim_id)
            if claim:
                res["claim_id"] = claim.id
                if claim.journal_id:
                    res["journal_id"] = claim.journal_id.id
                elif claim.cash_fund_id:
                    res["journal_id"] = claim.cash_fund_id.id
        return res

    @api.constrains("returned_amount")
    def _check_returned_amount(self):
        for wizard in self:
            if wizard.returned_amount < 0:
                raise ValidationError(_("Returned amount cannot be negative."))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_clear(self):
        self.ensure_one()
        claim = self.claim_id
        if claim.state != "paid":
            raise UserError(_("Only paid advances can be cleared."))

        expenses = self.expense_ids
        expense_total = sum(expenses.mapped("total_amount"))
        cleared_total = expense_total + self.returned_amount

        if cleared_total <= 0:
            raise UserError(
                _("Please add expenses or a returned amount to clear the advance.")
            )
        if cleared_total - claim.remaining_amount > 0.01:
            raise UserError(
                _(
                    "Cleared amount (%.2f) exceeds the remaining advance (%.2f)."
                )
                % (cleared_total, claim.remaining_amount)
            )
        if self.returned_amount > 0 and not self.journal_id:
            raise UserError(
                _("Please select a journal for the returned cash.")
            )

        if expenses:
            expenses.write({"od19_hr_advance_id": claim.id})

        move = self._create_clearing_move(
            expenses, expense_total, self.returned_amount
        )
        move.action_post()
        self._od19_reconcile_advance(claim, move)

        claim.write({"clear_move_id": move.id, "clear_date": self.clear_date})
        claim.invalidate_recordset(["cleared_amount", "remaining_amount"])
        if claim.remaining_amount <= 0.005:
            claim.write({"state": "cleared", "cash_state": "settled"})
        else:
            claim.cash_state = "partially_used"
        return {"type": "ir.actions.act_window_close"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _od19_get_clearing_journal(self):
        """สมุดสำหรับรายการหักกลบ (misc) ถ้าไม่ได้เลือกไว้."""
        self.ensure_one()
        if self.journal_id:
            return self.journal_id
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", self.claim_id.company_id.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        if not journal:
            raise UserError(
                _("Please configure a miscellaneous journal to clear advances.")
            )
        return journal

    def _od19_to_company_currency(self, amount):
        self.ensure_one()
        claim = self.claim_id
        return claim.currency_id._convert(
            amount,
            claim.company_id.currency_id,
            claim.company_id,
            self.clear_date or fields.Date.context_today(self),
        )

    def _create_clearing_move(self, expenses, expense_total, returned_amount):
        """สร้างรายการบัญชีหักกลบเงินทดรอง.

        เดบิตบัญชีค่าใช้จ่าย (ตามยอดที่พนักงานใช้จริง) + เดบิตเงินสด/ธนาคาร
        (ยอดที่คืน) และเครดิตบัญชีลูกหนี้พนักงาน (ยอดรวมที่เคลียร์)
        """
        self.ensure_one()
        claim = self.claim_id
        partner = claim.partner_id
        date = self.clear_date
        ref = _("Advance Clearing - %s") % claim.name
        lines = []

        for expense in expenses:
            account = (
                expense.account_id
                or expense.product_id.expense_account_id
                or expense.product_id.property_account_expense_id
            )
            if not account:
                raise UserError(
                    _("Expense %s has no expense account configured.")
                    % expense.name
                )
            balance = self._od19_to_company_currency(expense.total_amount)
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": ref,
                        "account_id": account.id,
                        "partner_id": partner.id if partner else False,
                        "debit": balance,
                        "credit": 0.0,
                        "date_maturity": date,
                    },
                )
            )

        if returned_amount:
            debit_account = self.journal_id.default_account_id
            if not debit_account:
                raise UserError(
                    _("The journal %s has no default account.")
                    % self.journal_id.display_name
                )
            balance = self._od19_to_company_currency(returned_amount)
            lines.append(
                (
                    0,
                    0,
                    {
                        "name": _("Advance Return - %s") % claim.name,
                        "account_id": debit_account.id,
                        "partner_id": partner.id if partner else False,
                        "debit": balance,
                        "credit": 0.0,
                        "date_maturity": date,
                    },
                )
            )

        credit_balance = self._od19_to_company_currency(
            expense_total + returned_amount
        )
        lines.append(
            (
                0,
                0,
                {
                    "name": ref,
                    "account_id": claim.advance_account_id.id,
                    "partner_id": partner.id if partner else False,
                    "debit": 0.0,
                    "credit": credit_balance,
                    "date_maturity": date,
                },
            )
        )

        return self.env["account.move"].create(
            {
                "date": date,
                "journal_id": self._od19_get_clearing_journal().id,
                "ref": ref,
                "line_ids": lines,
            }
        )

    def _od19_reconcile_advance(self, claim, move):
        """หักกลบรายการบัญชีลูกหนี้พนักงาน (payment + clearing entry)."""
        self.ensure_one()
        lines = (claim.payment_id.move_id.line_ids | move.line_ids).filtered(
            lambda line: line.account_id == claim.advance_account_id
            and line.parent_state == "posted"
        )
        if len(lines) >= 2:
            lines.reconcile()
