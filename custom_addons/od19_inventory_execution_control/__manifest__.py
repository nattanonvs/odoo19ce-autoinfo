{
    "name": "OD19 Inventory Execution Control",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    # Intentional Wave 1 integration baseline, not accidental over-coupling.
    "depends": [
        "stock",
        "purchase_stock",
        "sale_stock",
        "od19_purchase_procurement_core",
        "od19_sales_project_context",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_valuation_by_lot_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
