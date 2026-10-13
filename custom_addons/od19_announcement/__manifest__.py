{
    "name": "Announcement",
    "version": "19.0.1.0.0",
    "category": "Internal",
    "summary": "Company announcements with read receipts and multi-channel push",
    "author": "OD19",
    "license": "LGPL-3",
    "depends": ["base", "mail", "hr", "base_user_role", "od19_notification_multi_channel"],
    "data": [
        "security/ir.model.access.csv",
        "security/announcement_security.xml",
        "data/announcement_cron.xml",
        "views/announcement_views.xml",
        "views/announcement_menus.xml",
    ],
    "installable": True,
    "application": True,
}
