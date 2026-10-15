# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ExpenseReset(models.TransientModel):
    _name = 'od19.expense.reset'
    _description = 'Reset Expense Cash State'

    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense / ค่าใช้จ่าย',
        required=True,
        readonly=True,
    )
    reason = fields.Char(
        string='Reason / เหตุผล',
        required=True,
        help='Reason for resetting the cash state (for audit trail).',
    )
    new_state = fields.Selection(
        [
            ('not_received', 'Not Received / ยังไม่ได้รับเงิน'),
            ('received', 'Received / ได้รับเงินแล้ว'),
            ('used', 'Used / ใช้เงินแล้ว'),
        ],
        string='New State / สถานะใหม่',
        default='not_received',
        required=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('default_expense_id'):
            res['expense_id'] = self.env.context['default_expense_id']
        return res

    def action_reset(self):
        self.ensure_one()
        if not self.env.is_admin():
            raise UserError(_(
                'Only administrators can reset the cash state.'
            ))
        if not self.expense_id:
            raise UserError(_('Expense is missing.'))
        self.expense_id.od19_cash_state = self.new_state
        self.expense_id.message_post(
            body=_(
                'Cash state reset to <b>%s</b> by %s.<br/>Reason: %s'
            ) % (
                dict(self._fields['new_state'].selection).get(self.new_state, self.new_state),
                self.env.user.name,
                self.reason,
            )
        )
        return {'type': 'ir.actions.act_window_close'}
