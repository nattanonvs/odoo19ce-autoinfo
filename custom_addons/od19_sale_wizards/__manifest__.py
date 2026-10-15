# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Sale Wizards",
    "version": "19.0.1.0.0",
    "summary": (
        "Change delivery date wizard, get sale order lines wizard on invoice, "
        "and downpayment invoice linking"
    ),
    "author": "OD19",
    "category": "Sales",
    "depends": [
        "sale_management",
        "account",
        "sale_purchase",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order_views.xml",
        "views/account_move_views.xml",
        "wizards/sale_change_delivery_date_views.xml",
        "wizards/account_invoice_get_sale_lines_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
