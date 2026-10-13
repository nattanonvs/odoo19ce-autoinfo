from odoo import fields, models, api


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    department_id = fields.Many2one('hr.department', string='Department')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    expense_category_id = fields.Many2one('od19.vehicle.expense.category',
        string='Default Expense Category')
    total_expense = fields.Monetary(string='Total Expense', compute='_compute_total_expense',
        currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    @api.depends('log_services.amount')
    def _compute_total_expense(self):
        for vehicle in self:
            vehicle.total_expense = sum(vehicle.log_services.mapped('amount'))
