# -*- coding: utf-8 -*-
{
    'name': 'HR Expense Portal',
    'version': '19.0.2.1.0',
    'category': 'Human Resources/Expenses',
    'summary': (
        'Employee-facing expense experience: a quick submission wizard, a '
        '"My Expenses" kanban and an employee portal (/my/expenses) for HR '
        'Expense.'
    ),
    'author': 'OD19',
    'website': 'https://od19.com',
    'license': 'LGPL-3',
    'depends': [
        'hr_expense',
        'od19_hr_expense_thai',
        'mail',
        'portal',
        'base_tier_validation',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/od19_hr_expense_portal_security.xml',
        'views/hr_expense_quick_create_views.xml',
        'views/hr_expense_kanban_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
