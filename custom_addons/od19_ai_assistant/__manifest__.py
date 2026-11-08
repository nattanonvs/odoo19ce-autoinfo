# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 AI Assistant",
    "version": "19.0.1.2.0",
    "author": "OD19",
    "category": "Productivity",
    "summary": "Free / self-hosted AI assistant for Odoo 19 CE "
    "(Ollama or any OpenAI-compatible endpoint).",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/od19_ai_chat_views.xml",
    ],
    "installable": True,
    "application": True,
}
