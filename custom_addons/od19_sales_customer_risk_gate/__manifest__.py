{
    "name": "OD19 Sales Customer Risk and Credit Gate",
    "summary": "Block blacklisted customers and unapproved credit sales; accounting-owned credit approval",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "license": "LGPL-3",
    "depends": ["sale_management", "account", "mail"],
    "data": [
        "security/od19_credit_gate_security.xml",
        "views/account_payment_term_views.xml",
    ],
    "installable": True,
    "application": False,
}
