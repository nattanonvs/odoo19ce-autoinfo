# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ExpenseDelegate(models.TransientModel):
    _name = 'od19.expense.delegate'
    _description = 'Delegate Expense Approval'

    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense / ค่าใช้จ่าย',
        required=True,
    )
    delegate_approver_id = fields.Many2one(
        'res.users',
        string='Delegate To / มอบหมายให้',
        required=True,
        help='The user who will be allowed to approve/reject this expense.',
    )
    reason = fields.Char(string='Reason / เหตุผล')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_expense_id'):
            res['expense_id'] = self.env.context['default_expense_id']
        return res

    def action_delegate(self):
        self.ensure_one()
        if not self.expense_id:
            raise UserError(_('Expense is missing.'))
        if self.delegate_approver_id == self.env.user:
            raise UserError(_('You cannot delegate approval to yourself.'))
        self.expense_id.write({
            'od19_delegate_approver_id': self.delegate_approver_id.id,
            'od19_delegated_by_id': self.env.user.id,
            'od19_delegation_date': fields.Datetime.now(),
        })
        return {'type': 'ir.actions.act_window_close'}
