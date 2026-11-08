# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_ai_base_url = fields.Char(
        string="ที่อยู่ AI (Base URL)",
        config_parameter="od19_ai.base_url",
        default="http://localhost:11434/v1",
        help="ปลายทางที่รองรับ OpenAI API เช่น http://localhost:11434/v1 "
        "(Ollama), https://api.groq.com/openai/v1 (Groq).",
    )
    od19_ai_model = fields.Char(
        string="โมเดล AI",
        config_parameter="od19_ai.model",
        default="qwen2.5:7b",
        help="ชื่อโมเดลที่ปลายทางให้บริการ เช่น qwen2.5:7b, typhoon, "
        "llama3.1, gemini-2.0-flash.",
    )
    od19_ai_api_key = fields.Char(
        string="คีย์ API",
        config_parameter="od19_ai.api_key",
        groups="base.group_system",
        help="เว้นว่างได้หากใช้ Ollama ที่ทำงานภายในเครื่อง",
    )
    od19_ai_timeout = fields.Integer(
        string="หมดเวลา (วินาที)",
        config_parameter="od19_ai.timeout",
        default=60,
    )
    od19_ai_system_prompt = fields.Char(
        string="คำสั่งระบบ (System Prompt)",
        config_parameter="od19_ai.system_prompt",
        default="You are a helpful assistant for a Thai accounting ERP "
        "(Odoo 19). Answer in Thai unless asked otherwise.",
    )
