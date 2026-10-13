{
    "name": "OD19 Accounting - Advance Payment",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "Customer and supplier advance payment tracking",
    "depends": [
        "account",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/account_advance_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
