# -*- coding: utf-8 -*-
import base64
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ExpenseXlsxExport(models.TransientModel):
    _name = 'od19.expense.xlsx.export'
    _description = 'Export Expenses to XLSX'

    date_from = fields.Date(
        string='Date From / จากวันที่',
        required=True,
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string='Date To / ถึงวันที่',
        required=True,
        default=fields.Date.context_today,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee / พนักงาน',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department / แผนก',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('posted', 'Posted'),
            ('in_payment', 'In Payment'),
            ('paid', 'Paid'),
            ('refused', 'Refused'),
        ],
        string='State / สถานะ',
    )
    cash_state = fields.Selection(
        [
            ('not_received', 'Not Received'),
            ('received', 'Received'),
            ('used', 'Used'),
            ('returned', 'Returned'),
        ],
        string='Cash State / สถานะเงินสด',
    )

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to and wizard.date_from > wizard.date_to:
                raise ValidationError(
                    _('Date From must be earlier than or equal to Date To.')
                )

    def _get_expense_domain(self):
        """Build the search domain for expenses."""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.state:
            domain.append(('state', '=', self.state))
        if self.cash_state:
            domain.append(('od19_cash_state', '=', self.cash_state))
        # If active_ids are passed (from tree button), restrict to those
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            domain.append(('id', 'in', active_ids))
        return domain

    def action_export(self):
        self.ensure_one()
        expenses = self.env['hr.expense'].search(self._get_expense_domain())
        if not expenses:
            raise UserError(_('No expenses found matching the selected filters.'))

        xlsx_data = self.env[
            'report.od19_hr_expense_enhanced.expense_xlsx'
        ].create_xlsx_report(expenses.ids, {})

        filename = 'expenses_%s_%s.xlsx' % (
            self.date_from.strftime('%Y%m%d'),
            self.date_to.strftime('%Y%m%d'),
        )
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': xlsx_data,
            'res_model': 'od19.expense.xlsx.export',
            'res_id': self.id,
            'type': 'binary',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
