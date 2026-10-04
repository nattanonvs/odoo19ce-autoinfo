{
    "name": "OD19 Sales OCA Workflow Bridge",
    "version": "19.0.1.0.0",
    "depends": [
        "od19_sales_project_context",
        "od19_sales_contract_core",
        "od19_sales_billing_evidence",
        "od19_sales_reporting",
        "base_user_role",
        "sale_delivery_state",
    ],
    "data": ["views/sale_order_bridge_views.xml"],
    "installable": True,
    "license": "LGPL-3",
}
