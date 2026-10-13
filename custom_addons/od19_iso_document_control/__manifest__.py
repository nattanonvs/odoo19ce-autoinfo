# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "ISO Document Control",
    "version": "19.0.1.0.0",
    "category": "ISO/Quality",
    "license": "LGPL-3",
    "author": "TRAE",
    "website": "https://www.trae.ai",
    "summary": "ISO 9001 / ISO 14001 Document Control with 4-level approval",
    "depends": [
        "base",
        "mail",
        "hr",
        "web",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/iso_document_category_data.xml",
        "data/iso_standard_data.xml",
        "data/iso_document_seed_data.xml",
        "data/ir_sequence_data.xml",
        "report/iso_footer_templates.xml",
        "report/external_layout_footer.xml",
        "views/iso_document_views.xml",
        "views/iso_document_category_views.xml",
        "views/iso_standard_views.xml",
        "views/ir_actions_report_views.xml",
        "views/menu.xml",
    ],
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
}
