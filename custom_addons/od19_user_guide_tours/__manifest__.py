# -*- coding: utf-8 -*-
{
    'name': 'User Guide Tours',
    'version': '19.0.1.0.0',
    'category': 'Tools/User Guide',
    'summary': 'Interactive guided tours for all OD19 business modules',
    'description': """
OD19 User Guide Tours
=====================
Provides interactive guided tours to help users learn how to use
all OD19 custom modules, including Contacts & Credit Risk,
Sales Contracts & Billing, Purchase Approval, Inventory Operations,
Accounting, HR Expense, and Project & Analytic Accounting.

Tours are accessible from the user menu (top-right) under "Start Tour"
and from the Help icon on each relevant screen.
    """,
    'depends': [
        'web_tour',
        'od19_contacts_partner_roles',
        'od19_sales_customer_risk_gate',
        'od19_sales_contract_core',
        'od19_sales_billing_evidence',
        'od19_purchase_procurement_core',
        'od19_inventory_audit_count',
        'od19_service_card',
        'od19_quality_control',
        'od19_transportation',
        'od19_accounting_petty_cash',
        'od19_accounting_wht',
        'od19_accounting_fiscal_year',
        'od19_accounting_cheque',
        'od19_accounting_dncn',
        'od19_accounting_advance',
        'od19_hr_expense_thai',
        'od19_project_analytic',
        'od19_service_warranty',
        'od19_asset_loan',
        'od19_stock_valuation_adjustment',
        'od19_fleet_accounting',
        'od19_announcement',
    ],
    'assets': {
        'web.assets_backend': [
            'od19_user_guide_tours/static/src/tours/contacts_tour.js',
            'od19_user_guide_tours/static/src/tours/sales_tour.js',
            'od19_user_guide_tours/static/src/tours/purchase_tour.js',
            'od19_user_guide_tours/static/src/tours/inventory_tour.js',
            'od19_user_guide_tours/static/src/tours/accounting_tour.js',
            'od19_user_guide_tours/static/src/tours/cheque_tour.js',
            'od19_user_guide_tours/static/src/tours/dncn_tour.js',
            'od19_user_guide_tours/static/src/tours/advance_payment_tour.js',
            'od19_user_guide_tours/static/src/tours/hr_expense_tour.js',
            'od19_user_guide_tours/static/src/tours/project_tour.js',
            'od19_user_guide_tours/static/src/tours/warranty_tour.js',
            'od19_user_guide_tours/static/src/tours/asset_loan_tour.js',
            'od19_user_guide_tours/static/src/tours/stock_valuation_tour.js',
            'od19_user_guide_tours/static/src/tours/fleet_tour.js',
            'od19_user_guide_tours/static/src/tours/announcement_tour.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
    'author': 'OD19',
}
