{
    "name": "OD19 Inventory Reporting",
    "version": "19.0.1.0.0",
    "depends": [
        "stock",
        "od19_inventory_execution_control",
        "od19_inventory_audit_count",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/report_inventory_movement_backlog_views.xml",
        "views/report_inventory_accuracy_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
