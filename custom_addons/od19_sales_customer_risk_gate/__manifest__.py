{
    "name": "OD19 Sales Customer Risk and Credit Gate",
    "summary": "Block blacklisted customers and unapproved credit sales; accounting-owned credit approval",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "license": "LGPL-3",
    "depends": ["sale_management", "account", "mail"],
    "data": [
        "security/od19_credit_gate_security.xml",
        "security/ir.model.access.csv",
        "views/account_payment_term_views.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
        "views/od19_credit_gate_report_views.xml",
    ],
    "installable": True,
    "application": False,
}
