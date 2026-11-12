# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Document Intake",
    "version": "19.0.1.0.0",
    "category": "Document Management",
    "summary": "กล่องรับเข้า ช่องทางรับเอกสาร การสกัดข้อความ และการจัดหมวดด้วยกฎ/AI",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["od19_document_hub", "od19_ai_assistant"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/od19_document_channel_views.xml",
        "views/od19_document_classify_rule_views.xml",
        "views/od19_document_inbox_views.xml",
        "views/od19_document_intake_wizard_views.xml",
        "views/od19_document_intake_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
