# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 AI Assistant",
    "version": "19.0.1.5.0",
    "author": "OD19",
    "category": "Productivity",
    "summary": "Free / self-hosted AI assistant for Odoo 19 CE "
    "(Ollama or any OpenAI-compatible endpoint).",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "security/od19_ai_security.xml",
        "views/res_config_settings_views.xml",
        "views/od19_ai_chat_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "od19_ai_assistant/static/src/scss/od19_ai_chat.scss",
            "od19_ai_assistant/static/src/xml/od19_ai_chat.xml",
            "od19_ai_assistant/static/src/js/od19_ai_chat.js",
        ],
    },
    "installable": True,
    "application": True,
}
