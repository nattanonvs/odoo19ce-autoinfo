{
    "name": "OD19 Sales Contract Core",
    "version": "19.0.1.0.0",
    "depends": ["sale_management", "mail", "od19_sales_project_context"],
    "data": [
        "security/ir.model.access.csv",
        "views/sales_contract_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
