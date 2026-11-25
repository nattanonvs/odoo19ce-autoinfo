# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 UI Defaults",
    "version": "19.0.1.5.0",
    "summary": (
        "Project-wide UI defaults: Configuration menu is always the last menu of "
        "its app, related NavBar sections are grouped, moved or renamed together, "
        "the Accounting Customers/Vendors sections follow the accounting "
        "workflow, form fields are more readable, the chatter can be collapsed "
        "per user, Developer Tools and About stay at the bottom of the Settings "
        "page, and the standard Sales 'Discounts' setting is enabled"
    ),
    "author": "OD19",
    "category": "Tools",
    "depends": ["base", "sale", "base_setup"],
    "data": [
        "views/res_config_settings_views.xml",
        "data/ui_defaults.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_ui_defaults/static/src/css/form_readability.css",
            "od19_ui_defaults/static/src/css/chatter_collapse.css",
            "od19_ui_defaults/static/src/js/field_empty_marker.js",
            "od19_ui_defaults/static/src/js/error_dialog_clipboard.js",
            "od19_ui_defaults/static/src/js/chatter_collapse.js",
            "od19_ui_defaults/static/src/xml/chatter_collapse.xml",
        ],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_ui_defaults/static/description/icon.svg",
}
