from odoo import fields, models, api


class VehicleExpenseCategory(models.Model):
    _name = 'od19.vehicle.expense.category'
    _description = 'Vehicle Expense Category'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    expense_type = fields.Selection([
        ('fuel', 'Fuel'),
        ('maintenance', 'Maintenance & Repair'),
        ('insurance', 'Insurance'),
        ('registration', 'Registration & Tax'),
        ('toll', 'Toll & Parking'),
        ('washing', 'Washing & Cleaning'),
        ('depreciation', 'Depreciation'),
        ('other', 'Other'),
    ], string='Expense Type', default='other', required=True)
    account_id = fields.Many2one('account.account', string='Expense Account',
        domain="[('account_type', 'in', ['expense', 'expense_direct_cost'])]")
    active = fields.Boolean(string='Active', default=True)
