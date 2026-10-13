{
    "name": "OD19 Accounting - Fiscal Year & Year-End Closing",
    "version": "19.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Fiscal year management and year-end closing process",
    "depends": [
        "account",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_fiscal_year_views.xml",
        "wizard/account_year_end_closing_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
