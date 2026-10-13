# -*- coding: utf-8 -*-
{
    "name": "Quotation Document Sequence (OD19)",
    "version": "1.0.0",
    "summary": "Department-based quotation sequences (QB/QT/QI/QD) and quotation revision",
    "description": """
Adds department-based document sequences for quotations.
Each department can have its own Quotation sequence
(prefixes like QB, QT, QI, QD).
Also supports quotation revision with /R01, /R02 suffix.
    """,
    "author": "OD19 Custom",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "hr",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "views/hr_department_views.xml",
        "views/sale_order_views.xml",
        "wizard/sale_order_revision_wizard.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
