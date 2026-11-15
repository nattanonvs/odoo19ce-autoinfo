# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 System Health Monitor",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "website": "https://github.com/nattanonvs/odoo19ce-autoinfo",
    "category": "Productivity",
    "summary": "ระบบรู้ทันสุขภาพ Odoo 19 (ชั้นใน): ตรวจผล เปิดเหตุการณ์ "
    "ยกระดับการแจ้งเตือน และเฝ้าตัวเฝ้าชั้นนอก",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "od19_security_roles",
        "od19_notification_multi_channel",
        "od19_ai_assistant",
    ],
    "post_load": "post_load",
    "data": [
        "security/od19_system_monitor_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "data/od19_health_check_data.xml",
        "data/od19_health_rule_data.xml",
        "views/od19_health_check_views.xml",
        "views/od19_health_result_views.xml",
        "views/od19_health_rule_views.xml",
        "views/od19_health_incident_views.xml",
        "views/od19_health_watchdog_views.xml",
        "views/od19_health_maintenance_views.xml",
        "views/od19_health_ai_triage_views.xml",
        "views/od19_health_dashboard_views.xml",
        "views/res_config_settings_views.xml",
        "views/od19_system_monitor_menus.xml",
    ],
    "installable": True,
    "application": True,
}
