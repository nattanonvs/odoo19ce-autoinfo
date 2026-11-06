# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Offline Draft (ร่างอัตโนมัติ)",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "Autosave + restore drafts across backend and portal (T1 Draft Hub)",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [
        "security/od19_draft_security.xml",
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_offline_draft/static/src/draft_service.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
