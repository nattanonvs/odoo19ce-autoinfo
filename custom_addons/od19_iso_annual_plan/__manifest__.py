# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "ISO Annual Plan",
    "version": "19.0.1.0.0",
    "category": "ISO/Quality",
    "license": "LGPL-3",
    "author": "TRAE",
    "website": "https://www.trae.ai",
    "summary": "ISO annual plan matrix (12 months) with due-date reminders",
    "depends": [
        "base",
        "mail",
        "hr",
        "od19_iso_document_control",
        "od19_security_roles",
        "od19_notification_multi_channel",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/od19_department_rule.xml",
        "data/iso_plan_activity_type_data.xml",
        "data/ir_cron_data.xml",
        "views/iso_plan_activity_type_views.xml",
        "views/iso_annual_plan_views.xml",
        "views/menu.xml",
    ],
    "demo": [],
    "icon": "/od19_iso_annual_plan/static/description/icon.svg",
    "installable": True,
    "application": True,
    "auto_install": False,
}
