from odoo.tests.common import TransactionCase
from odoo import fields


class TestFleetAccounting(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle = cls.env['fleet.vehicle'].create({
            'license_plate': 'TEST-001',
            'model_id': cls.env['fleet.vehicle.model'].search([], limit=1).id
            or cls.env['fleet.vehicle.model'].create({
                'name': 'Test Model',
                'brand_id': cls.env['fleet.vehicle.model.brand'].search([], limit=1).id
                or cls.env['fleet.vehicle.model.brand'].create({'name': 'Test Brand'}).id,
            }).id,
        })
        cls.service_type = cls.env['fleet.service.type'].search([], limit=1) or cls.env['fleet.service.type'].create({
            'name': 'Test Service',
        })
        cls.expense_category = cls.env['od19.vehicle.expense.category'].create({
            'name': 'Fuel',
            'code': 'FUEL',
            'expense_type': 'fuel',
        })
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
        })
        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Test Plan',
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test Analytic',
            'plan_id': cls.analytic_plan.id,
        })

    def test_expense_category_creation(self):
        self.assertEqual(self.expense_category.name, 'Fuel')
        self.assertEqual(self.expense_category.expense_type, 'fuel')

    def test_vehicle_accounting_fields(self):
        self.vehicle.write({
            'department_id': self.department.id,
            'analytic_account_id': self.analytic_account.id,
            'expense_category_id': self.expense_category.id,
        })
        self.assertEqual(self.vehicle.department_id, self.department)
        self.assertEqual(self.vehicle.analytic_account_id, self.analytic_account)
        self.assertEqual(self.vehicle.expense_category_id, self.expense_category)

    def test_log_service_onchange_vehicle(self):
        service = self.env['fleet.vehicle.log.services'].new({
            'vehicle_id': self.vehicle.id,
        })
        service.vehicle_id = self.vehicle
        service._onchange_vehicle_id()
        self.assertEqual(service.analytic_account_id, self.vehicle.analytic_account_id)
        self.assertEqual(service.department_id, self.vehicle.department_id)

    def test_vehicle_total_expense(self):
        self.env['fleet.vehicle.log.services'].create({
            'vehicle_id': self.vehicle.id,
            'amount': 1000,
            'description': 'Fuel',
            'service_type_id': self.service_type.id,
            'expense_category_id': self.expense_category.id,
        })
        self.env['fleet.vehicle.log.services'].create({
            'vehicle_id': self.vehicle.id,
            'amount': 500,
            'description': 'Maintenance',
            'service_type_id': self.service_type.id,
        })
        self.assertEqual(self.vehicle.total_expense, 1500)

    def test_log_service_expense_category(self):
        service = self.env['fleet.vehicle.log.services'].create({
            'vehicle_id': self.vehicle.id,
            'amount': 500,
            'service_type_id': self.service_type.id,
            'expense_category_id': self.expense_category.id,
        })
        self.assertEqual(service.expense_category_id, self.expense_category)

    def test_expense_types(self):
        for expense_type in ['fuel', 'maintenance', 'insurance', 'registration',
                              'toll', 'washing', 'depreciation', 'other']:
            cat = self.env['od19.vehicle.expense.category'].create({
                'name': f'Type {expense_type}',
                'expense_type': expense_type,
            })
            self.assertEqual(cat.expense_type, expense_type)

    def test_log_service_department(self):
        service = self.env['fleet.vehicle.log.services'].create({
            'vehicle_id': self.vehicle.id,
            'amount': 300,
            'service_type_id': self.service_type.id,
            'department_id': self.department.id,
        })
        self.assertEqual(service.department_id, self.department)
