# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""การวินิจฉัยเหตุการณ์ด้วย AI (P5) — โหมด A: อ่านอย่างเดียวเท่านั้น.

ใช้ผู้ช่วย AI ที่มีอยู่แล้วในระบบ (``od19_ai_assistant`` ซึ่งรองรับ Ollama
และปลายทางที่เข้ากันได้กับ OpenAI) เพื่อสรุปเหตุการณ์สุขภาพระบบเป็นภาษาไทย
พร้อมข้อสันนิษฐานสาเหตุและแนวทางตรวจสอบเบื้องต้น

ข้อจำกัดด้านความปลอดภัย (สอดคล้องข้อเสนอโครงการ P5 และนโยบายของผู้ใช้):
AI **ห้าม** สั่งแก้ไขระบบ อนุมัติ หรือชำระเงินใด ๆ — ทำหน้าที่สรุป/เสนอแนะ
เท่านั้น ผลลัพธ์ทุกครั้งถูกบันทึกไว้เพื่อการตรวจสอบย้อนหลัง
"""

import logging
import time

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

TRIAGE_STATES = [
    ("done", "สำเร็จ"),
    ("error", "ผิดพลาด"),
]

# คำสั่งระบบ: จำกัดบทบาทให้เป็น "ผู้อ่านและวิเคราะห์" เท่านั้น
SYSTEM_PROMPT = (
    "คุณคือวิศวกรผู้ดูแลระบบ Odoo 19 ที่เชี่ยวชาญการวินิจฉัยปัญหา "
    "ให้สรุปเหตุการณ์สุขภาพระบบเป็นภาษาไทยอย่างกระชับ โดยแบ่งเป็น "
    "1) สาเหตุที่เป็นไปได้ 2) ผลกระทบต่อผู้ใช้ 3) ขั้นตอนตรวจสอบและแก้ไขเบื้องต้น "
    "ห้ามสั่งให้แก้ไขระบบด้วยตัวเอง ห้ามอนุมัติหรือชำระเงินใด ๆ "
    "ตอบเป็นข้อความล้วน ไม่ต้องใส่ JSON"
)


class Od19HealthAiTriage(models.Model):
    """ผลการวินิจฉัยด้วย AI 1 ครั้ง (อ่านอย่างเดียว)."""

    _name = "od19.health.ai.triage"
    _description = "การวินิจฉัยเหตุการณ์ด้วย AI (OD19)"
    _order = "run_at desc, id desc"

    incident_id = fields.Many2one(
        "od19.health.incident",
        string="เหตุการณ์",
        required=True,
        ondelete="cascade",
        index=True,
    )
    run_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    state = fields.Selection(TRIAGE_STATES, default="done", readonly=True)
    provider = fields.Char(readonly=True)
    model_name = fields.Char(string="โมเดลที่ใช้", readonly=True)
    duration_ms = fields.Integer(string="ระยะเวลา (ms)", readonly=True)
    summary = fields.Text(string="บทสรุปการวินิจฉัย", readonly=True)
    prompt = fields.Text(string="ข้อมูลที่ส่งให้ AI", readonly=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    # ------------------------------------------------------------------
    # การเตรียมข้อมูล
    # ------------------------------------------------------------------
    @api.model
    def _build_prompt(self, incident):
        """ประกอบข้อมูลเหตุการณ์เป็นข้อความสำหรับส่งให้ AI (อ่านเท่านั้น)."""
        incident.ensure_one()
        lines = [
            _("เหตุการณ์สุขภาพระบบ Odoo 19"),
            "- %s: %s" % (_("รหัส"), incident.name),
            "- %s: %s (%s)"
            % (_("การตรวจ"), incident.check_id.name, incident.check_id.code),
            "- %s: %s" % (_("ความรุนแรง"), incident.severity),
            "- %s: %s" % (_("สถานะ"), incident.state),
            "- %s: %s" % (_("เป้าหมาย"), incident.target or "-"),
            "- %s: %s" % (_("เกิดครั้งแรก"), incident.first_seen or "-"),
            "- %s: %s" % (_("เกิดล่าสุด"), incident.last_seen or "-"),
            "- %s: %s" % (_("จำนวนครั้ง"), incident.occurrence_count),
            "- %s: %s" % (_("รายละเอียด"), incident.description or "-"),
        ]
        last = incident.check_id.result_ids[:1]
        if last:
            lines.append(
                "- %s: %s"
                % (_("ผลการตรวจล่าสุด"), last.value_label or last.message or "-")
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # การวินิจฉัย
    # ------------------------------------------------------------------
    @api.model
    def _triage(self, incident):
        """รันการวินิจฉัยเหตุการณ์ ``incident`` แล้วบันทึกผล (ไม่แก้ข้อมูลอื่น)."""
        incident.ensure_one()
        started = time.monotonic()
        provider = model_name = ""
        prompt = self._build_prompt(incident)
        state = "done"
        try:
            config = self.env["od19.ai.chat"]._get_ai_config()
            provider = config.get("provider") or ""
            model_name = config.get("model") or ""
            # นำเข้าแบบเลื่อนเวลา (deferred) เพื่อไม่ผูกตอน import โมดูล
            from odoo.addons.od19_ai_assistant.lib.client import chat_completion

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
            summary = chat_completion(
                config.get("base_url"),
                config.get("model"),
                messages,
                api_key=config.get("api_key") or None,
                timeout=config.get("timeout") or 60,
            )
        except Exception as exc:  # noqa: BLE001 — AI ล่มต้องไม่ทำให้ระบบล่ม
            _logger.warning("วินิจฉัยด้วย AI ล้มเหลว (%s): %s", incident.name, exc)
            state = "error"
            summary = _("วินิจฉัยไม่สำเร็จ: %s") % exc

        duration_ms = int((time.monotonic() - started) * 1000)
        return self.create(
            {
                "incident_id": incident.id,
                "state": state,
                "provider": provider,
                "model_name": model_name,
                "summary": summary,
                "prompt": prompt,
                "duration_ms": duration_ms,
                "company_id": incident.company_id.id,
            }
        )
