{
    "name": "Internal Issue Management",
    "version": "19.0.1.0.1",
    "category": "Internal Operations",
    "summary": "ระบบรับแจ้งเรื่อง/ปัญหาภายใน พร้อมคิวที่เป็นธรรมและการแซงคิวแบบอนุมัติ 2 ชั้น",
    "description": """
Internal Issue Management
=========================
ต่อยอด OCA helpdesk_mgmt สำหรับงานภายในองค์กร:
- หมวดใหญ่ (issue_stream) + route อัตโนมัติ + กล่องกลาง (Triage)
- ความเป็นส่วนตัว public / แผนก / ส่วนตัว
- คิวต่อทีม (priority -> FIFO) + แสดงตำแหน่งคิวให้ผู้แจ้ง
- Fair priority: Impact x Urgency + โควตางานด่วน
- คำขอแซงคิว: อนุมัติ 2 ชั้น + ผู้อนุมัติเลือกตำแหน่งแทรก
- แจ้งเตือนหลายช่องทางผ่าน od19_notification_multi_channel
""",
    "author": "OD19",
    "website": "https://github.com/odoo/odoo",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_mgmt",
        "od19_helpdesk_extension",
        "base_tier_validation",
        "hr",
        "mail",
        "od19_notification_multi_channel",
        "od19_security_roles",
    ],
    "data": [
        "security/internal_issue_security.xml",
        "security/od19_department_rule.xml",
        "security/ir.model.access.csv",
        "data/internal_issue_data.xml",
        "data/internal_issue_cron.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_queue_request_views.xml",
        "views/helpdesk_routing_rule_views.xml",
        "views/internal_issue_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "icon": "/od19_internal_issue/static/description/icon.svg",
}
