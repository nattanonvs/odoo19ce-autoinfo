{
    "name": "OD19 Purchase Request Extension",
    "version": "19.0.1.2.0",
    "category": "Purchase Management",
    "summary": "Thai-specific extension for OCA Purchase Request",
    "author": "OD19",
    "license": "LGPL-3",
    "depends": [
        "purchase_request",
        "purchase_request_tier_validation",
        "hr",
        "account_asset_management",
        "od19_internal_issue",
        "od19_notification_multi_channel",
    ],
    "data": [
        "security/purchase_request_security.xml",
        "data/menu_overrides.xml",
        "views/purchase_request_views.xml",
        "views/purchase_request_line_views.xml",
    ],
    "installable": True,
    "application": False,
}
