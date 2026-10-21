{
    "name": "OD19 Reporting - Jasper Reports Foundation",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Reporting",
    "summary": "Foundation for Jasper and QWeb report templates",
    "depends": [
        "account",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "report/generic_report.xml",
        "views/jasper_report_template_views.xml",
        "views/jasper_report_action_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
