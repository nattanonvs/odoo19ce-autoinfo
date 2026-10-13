{
    "name": "OD19 Accounting - Withholding Tax (WHT)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localizations/Payment",
    "summary": "Thai withholding tax types and WHT computation on payments",
    "depends": [
        "account",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/wht_type_views.xml",
        "views/account_payment_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
