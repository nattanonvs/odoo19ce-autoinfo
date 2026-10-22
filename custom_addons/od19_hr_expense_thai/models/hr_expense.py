# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ], string='Reimbursement Method', default='cash', tracking=True)
    reimbursement_date = fields.Date(
        string='Reimbursement Date',
        help='Date when the employee was reimbursed.',
    )
    first_approval_date = fields.Date(
        string='First Approval Date', readonly=True,
    )
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approver',
        tracking=True,
    )
    second_approval_date = fields.Date(
        string='Second Approval Date', readonly=True,
    )
    thai_expense_type = fields.Selection([
        ('travel', 'Travel'),
        ('meal', 'Meal'),
        ('transport', 'Transportation'),
        ('accommodation', 'Accommodation'),
        ('communication', 'Communication'),
        ('office_supplies', 'Office Supplies'),
        ('medical', 'Medical'),
        ('training', 'Training'),
        ('other', 'Other'),
    ], string='Expense Type', default='other', tracking=True)
    require_second_approval = fields.Boolean(
        string='Require Second Approval',
        compute='_compute_require_second_approval', store=True,
    )
    second_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Second Approval State', default='not_required', readonly=True, copy=False)

    @api.depends('total_amount')
    def _compute_require_second_approval(self):
        """Require second approval for expenses above a threshold."""
        threshold = self.env['ir.config_parameter'].sudo().get_param(
            'od19_hr_expense_thai.second_approval_threshold', '5000')
        try:
            threshold = float(threshold)
        except (ValueError, TypeError):
            threshold = 5000.0
        for expense in self:
            expense.require_second_approval = expense.total_amount > threshold

    def action_approve_first(self):
        """First level approval."""
        for expense in self:
            if expense.state not in ('submitted',):
                raise UserError(_('Only submitted expenses can be approved.'))
            approver = expense.first_approver_id
            if approver and approver.user_id and approver.user_id != self.env.user:
                raise UserError(_(
                    'Only the designated first approver (%s) can approve this '
                    'expense.'
                ) % approver.display_name)
            expense.first_approver_id = self.env.user.employee_id
            expense.first_approval_date = fields.Date.context_today(expense)
            if expense.require_second_approval:
                expense.second_approval_state = 'pending'
            else:
                expense.action_approve_second()

    def action_approve_second(self):
        """Second level approval."""
        for expense in self:
            if expense.second_approval_state == 'approved':
                raise UserError(_('This expense has already been approved.'))
            if (
                expense.first_approver_id
                and expense.first_approver_id.user_id == self.env.user
            ):
                raise UserError(_(
                    'The second approver must be different from the first '
                    'approver.'
                ))
            expense.second_approver_id = self.env.user.employee_id
            expense.second_approval_date = fields.Date.context_today(expense)
            expense.second_approval_state = 'approved'
            # Call standard approve
            expense.action_approve()

    def action_refuse_second(self):
        """Second level refusal."""
        for expense in self:
            expense.second_approval_state = 'refused'
            expense.action_refuse()

    def action_mark_reimbursed(self):
        """Mark expense as reimbursed (for own_account payment mode)."""
        for expense in self:
            if expense.payment_mode != 'own_account':
                raise UserError(_('Only expenses paid by employee can be reimbursed.'))
            expense.reimbursement_date = fields.Date.context_today(expense)
