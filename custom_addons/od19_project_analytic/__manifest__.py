{
    "name": "OD19 Project & Analytic Accounting",
    "version": "19.0.1.0.0",
    "category": "Services/Project",
    "summary": "Extend standard project.project with Job Number, Job Type, Department, Owner, Contractors, and auto analytic account",
    "depends": [
        "project",
        "od19_contacts_partner_roles",
        "purchase_stock",
    ],
    "data": [
        "views/project_project_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
