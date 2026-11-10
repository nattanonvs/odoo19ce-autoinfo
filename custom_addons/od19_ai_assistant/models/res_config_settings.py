# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models

from .od19_ai_chat import PROVIDER_PRESETS


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    od19_ai_provider = fields.Selection(
        selection=[
            ("ollama", "Ollama (ในเครื่อง)"),
            ("groq", "Groq (คลาวด์ฟรี)"),
            ("custom", "กำหนดเอง (OpenAI-compatible)"),
        ],
        string="ผู้ให้บริการ AI",
        config_parameter="od19_ai.provider",
        default="ollama",
        help="เลือกผู้ให้บริการเพื่อเติมที่อยู่ (Base URL) และโมเดลเริ่มต้นให้ "
        "อัตโนมัติ แล้วแก้ไขได้ตามต้องการ "
        "Ollama ทำงานฟรี/ในเครื่อง ส่วน Groq มีโควตาฟรีบนคลาวด์",
    )
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
    od19_ai_capability_mode = fields.Selection(
        selection=[
            ("read_only", "อ่านเท่านั้น (A)"),
            ("read_draft", "อ่าน + ร่างเอกสาร (B)"),
        ],
        string="โหมดผู้ช่วย AI (ดีฟอลต์ระบบ)",
        config_parameter="od19_ai.capability_mode",
        default="read_only",
        help="โหมดเริ่มต้นของผู้ช่วย AI สำหรับผู้ใช้ใหม่ "
        "read_only = อ่านข้อมูลเท่านั้น; read_draft = อ่าน + เสนอร่างเอกสาร "
        "(ต้องยืนยันก่อนสร้างจริงเสมอ)",
    )

    @api.onchange("od19_ai_provider")
    def _onchange_od19_ai_provider(self):
        """Prefill the endpoint/model from the selected provider preset.

        Existing custom values are preserved: only a blank value or a value
        copied from another preset is replaced.
        """
        preset = PROVIDER_PRESETS.get(self.od19_ai_provider)
        if not preset:
            return
        known_urls = {item["base_url"] for item in PROVIDER_PRESETS.values()}
        known_models = {item["model"] for item in PROVIDER_PRESETS.values()}
        if not self.od19_ai_base_url or self.od19_ai_base_url in known_urls:
            self.od19_ai_base_url = preset["base_url"]
        if not self.od19_ai_model or self.od19_ai_model in known_models:
            self.od19_ai_model = preset["model"]
