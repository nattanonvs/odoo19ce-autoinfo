{
    "name": "OD19 Purchase Procurement Core",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "depends": [
        "purchase",
        "purchase_requisition",
        "purchase_stock",
        "sale_purchase",
        "od19_contacts_partner_roles",
        "od19_sales_project_context",
    ],
    "data": [
        "security/purchase_director_security.xml",
        "views/purchase_order_views.xml",
        "views/purchase_requisition_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
