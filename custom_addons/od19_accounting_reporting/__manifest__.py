{
    "name": "OD19 Accounting Reporting",
    "version": "19.0.1.0.0",
    "depends": [
        "account",
        "sale_management",
        "od19_sales_billing_evidence",
        "od19_accounting_operational_closure",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_accounting_operational_closure_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
