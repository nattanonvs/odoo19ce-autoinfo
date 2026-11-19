# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_ai_base_url = fields.Char(
        string="AI Base URL",
        config_parameter="od19_ai.base_url",
        default="http://localhost:11434/v1",
        help="OpenAI-compatible endpoint root, e.g. http://localhost:11434/v1 "
        "(Ollama), https://api.groq.com/openai/v1 (Groq).",
    )
    od19_ai_model = fields.Char(
        string="AI Model",
        config_parameter="od19_ai.model",
        default="qwen2.5:7b",
        help="Model name served by the endpoint, e.g. qwen2.5:7b, typhoon, "
        "llama3.1, gemini-2.0-flash.",
    )
    od19_ai_api_key = fields.Char(
        string="API Key",
        config_parameter="od19_ai.api_key",
        groups="base.group_system",
        help="Leave empty for a local Ollama endpoint.",
    )
    od19_ai_timeout = fields.Integer(
        string="Timeout (seconds)",
        config_parameter="od19_ai.timeout",
        default=60,
    )
    od19_ai_system_prompt = fields.Char(
        string="System Prompt",
        config_parameter="od19_ai.system_prompt",
        default="You are a helpful assistant for a Thai accounting ERP "
        "(Odoo 19). Answer in Thai unless asked otherwise.",
    )
