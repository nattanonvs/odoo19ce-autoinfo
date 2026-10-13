from odoo import fields, models, api


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    expense_category_id = fields.Many2one('od19.vehicle.expense.category',
        string='Expense Category')
    analytic_account_id = fields.Many2one('account.analytic.account',
        string='Analytic Account')
    department_id = fields.Many2one('hr.department', string='Department')

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id:
            self.analytic_account_id = self.vehicle_id.analytic_account_id
            self.department_id = self.vehicle_id.department_id
            self.expense_category_id = self.vehicle_id.expense_category_id
