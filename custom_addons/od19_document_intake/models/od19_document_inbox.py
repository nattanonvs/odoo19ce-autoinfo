# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import hashlib
import json
import logging
import re

from odoo import api, fields, models

from odoo.addons.od19_ai_assistant.lib.client import AiClientError, chat_completion

_logger = logging.getLogger(__name__)

STATE_SELECTION = [
    ("new", "ใหม่"),
    ("processing", "กำลังประมวลผล"),
    ("to_review", "รอตรวจ"),
    ("linked", "ผูกแล้ว"),
    ("rejected", "ปฏิเสธ"),
    ("failed", "ผิดพลาด"),
]

CLASSIFY_METHOD_SELECTION = [
    ("rule", "กฎ"),
    ("ai", "AI"),
    ("manual", "คน"),
]

# เกณฑ์ผูกอัตโนมัติตามสเปก §8.1
CONFIDENCE_THRESHOLD = 70.0


class Od19DocumentInbox(models.Model):
    _name = "od19.document.inbox"
    _description = "กล่องรับเข้าเอกสาร (staging)"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char("ชื่อเรื่อง", required=True, default="เอกสารเข้า", tracking=True)
    file = fields.Binary("ไฟล์", attachment=True)
    filename = fields.Char("ชื่อไฟล์")
    checksum = fields.Char("Checksum (SHA1)", index=True)
    channel_id = fields.Many2one(
        "od19.document.channel", "ช่องทาง", ondelete="set null", index=True,
    )
    state = fields.Selection(
        STATE_SELECTION, "สถานะ", default="new", required=True,
        tracking=True, index=True,
    )
    suggested_category_id = fields.Many2one(
        "od19.document.category", "หมวดที่เสนอ", ondelete="set null",
    )
    suggested_partner_id = fields.Many2one(
        "res.partner", "คู่ค้าที่เสนอ", ondelete="set null",
    )
    confidence = fields.Float("ความมั่นใจ (%)", digits=(5, 2))
    classify_method = fields.Selection(
        CLASSIFY_METHOD_SELECTION, "วิธีจัดหมวด", readonly=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment", "เอกสารแนบที่ผูก", ondelete="set null", readonly=True,
    )
    res_model = fields.Char("โมเดลปลายทาง", readonly=True)
    res_id = fields.Integer("รหัสปลายทาง", readonly=True)
    log = fields.Text("บันทึกการประมวลผล", readonly=True)

    _checksum_idx = models.Index("(checksum)")

    # ------------------------------------------------------------------
    # Email alias (ช่องทางอีเมล) — alias ตั้ง Alias Model = od19.document.inbox
    # ------------------------------------------------------------------
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = dict(custom_values or {})
        subject = (msg_dict.get("subject") or "อีเมลเข้า").strip()
        values.setdefault("name", subject[:200])
        inbox = super().message_new(msg_dict, values)
        # ไฟล์แนบของอีเมลถูก mail.thread ผูกกับตัวระเบียนแล้ว — ใช้ไฟล์แรกเป็น staging
        attachment = self.env["ir.attachment"].search([
            ("res_model", "=", self._name), ("res_id", "=", inbox.id),
        ], limit=1)
        if attachment:
            inbox.write({
                "file": attachment.datas,
                "filename": attachment.name,
                "checksum": attachment.checksum,
            })
        return inbox

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _od19_compute_checksum(self):
        self.ensure_one()
        if self.checksum or not self.file:
            return self.checksum
        raw = self.file
        if isinstance(raw, str):
            raw = base64.b64decode(raw)
        self.checksum = hashlib.sha1(raw).hexdigest()
        return self.checksum

    def action_reject(self):
        self.write({"state": "rejected"})

    def _od19_rule_target_value(self, target, attachment=None):
        self.ensure_one()
        if target == "filename":
            return (self.filename or self.name or "").lower()
        if target == "partner":
            return (self.suggested_partner_id.name or "").lower()
        if target == "text" and attachment:
            extract = self.env["od19.document.extract"].search(
                [("attachment_id", "=", attachment.id)], limit=1,
            )
            return (extract.text_content or "").lower()
        return ""

    def _od19_classify_by_rules(self, attachment=None):
        """คืน (category, partner, confidence, method) หรือ (False, False, 0.0, 'rule')"""
        self.ensure_one()
        rules = self.env["od19.document.classify.rule"].search(
            [("active", "=", True)], order="sequence, id",
        )
        for rule in rules:
            haystack = self._od19_rule_target_value(rule.target, attachment)
            if haystack and rule.pattern.lower() in haystack:
                return rule.category_id, rule.partner_id, 100.0, "rule"
        empty = self.env["od19.document.category"]
        return empty, self.env["res.partner"], 0.0, "rule"

    _AI_SYSTEM_PROMPT = (
        "คุณเป็นผู้ช่วยจัดหมวดเอกสารของบริษัทไทย "
        "ตอบกลับเป็น JSON เท่านั้นตามรูปแบบ "
        '{"category_code": "<รหัสหมวด>", "confidence": <0-100>}'
    )

    def _od19_classify_with_ai(self):
        """จัดหมวดด้วย AI — คืน (category, partner, confidence, 'ai') หรือค่าว่างเมื่อล้ม"""
        self.ensure_one()
        empty_category = self.env["od19.document.category"]
        empty_partner = self.env["res.partner"]

        categories = self.env["od19.document.category"].search(
            [("auto_classify", "=", True)], limit=50,
        )
        if not categories:
            return empty_category, empty_partner, 0.0, "ai"

        code_list = "\n".join("- %s: %s" % (c.code, c.name) for c in categories)
        sample = (self.filename or self.name or "")[:200]
        config = self.env["od19.ai.chat"]._get_ai_config()
        messages = [
            {"role": "system", "content": self._AI_SYSTEM_PROMPT},
            {"role": "user", "content": (
                "ชื่อไฟล์: %s\nหมวดที่มี:\n%s\n"
                "เลือกหมวดที่เหมาะสมที่สุด" % (sample, code_list)
            )},
        ]
        try:
            answer = chat_completion(
                config["base_url"], config["model"], messages,
                api_key=config.get("api_key"), timeout=config.get("timeout", 60),
            )
        except AiClientError as exc:
            _logger.warning("od19_document_intake: AI จัดหมวดไม่สำเร็จ: %s", exc)
            return empty_category, empty_partner, 0.0, "ai"

        match = re.search(r"\{.*\}", answer or "", re.DOTALL)
        if not match:
            return empty_category, empty_partner, 0.0, "ai"
        try:
            payload = json.loads(match.group(0))
        except ValueError:
            return empty_category, empty_partner, 0.0, "ai"

        category = categories.filtered(
            lambda c: c.code == str(payload.get("category_code", "")).strip()
        )[:1]
        if not category:
            return empty_category, empty_partner, 0.0, "ai"
        try:
            confidence = float(payload.get("confidence") or 0.0)
        except (TypeError, ValueError):
            confidence = 0.0
        return category, empty_partner, confidence, "ai"

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------
    def _od19_create_attachment(self, category=None, res_model=None, res_id=None):
        """สร้าง ir.attachment จริงจากไฟล์ในกล่องรับเข้า แล้วปรับสถานะเป็น linked"""
        self.ensure_one()
        category = category or self.suggested_category_id or self.channel_id.default_category_id
        attachment = self.env["ir.attachment"].create({
            "name": self.filename or self.name,
            "datas": self.file,
            "res_model": res_model or self.res_model or False,
            "res_id": res_id or self.res_id or 0,
            "od19_origin": "external",
            "od19_category_id": category.id if category else False,
            "od19_partner_id": self.suggested_partner_id.id if self.suggested_partner_id else False,
            "od19_doc_date": fields.Date.context_today(self),
            "od19_index_state": "pending",
        })
        self.write({
            "attachment_id": attachment.id,
            "res_model": res_model or self.res_model,
            "res_id": res_id or self.res_id,
            "state": "linked",
        })
        return attachment

    def _od19_classify(self, attachment=None):
        """คืน (category, partner, confidence, method) — กฎก่อน แล้วค่อย AI"""
        self.ensure_one()
        category, partner, confidence, method = self._od19_classify_by_rules(attachment)
        if category:
            return category, partner, confidence, method
        if self.channel_id.enable_ai:
            category, partner, confidence, method = self._od19_classify_with_ai()
            if category:
                return category, partner, confidence, method
        default = self.channel_id.default_category_id
        if default:
            return default, self.env["res.partner"], 50.0, "rule"
        return self.env["od19.document.category"], self.env["res.partner"], 0.0, "rule"

    def _od19_process(self):
        """ประมวลผลรายการเดียว — ตรวจ MIME/ขนาด → checksum → จัดหมวด → ตัดสินใจ"""
        self.ensure_one()
        if self.state not in ("new", "failed"):
            return
        self.state = "processing"
        lines = []
        try:
            self._od19_compute_checksum()
            category, partner, confidence, method = self._od19_classify()
            self.write({
                "suggested_category_id": category.id if category else False,
                "suggested_partner_id": partner.id if partner else False,
                "confidence": confidence,
                "classify_method": method,
            })
            if category and confidence >= CONFIDENCE_THRESHOLD:
                attachment = self._od19_create_attachment(category)
                attachment._od19_run_extraction(self.channel_id)
                lines.append("ผูกอัตโนมัติด้วย %s (%.1f%%)" % (method, confidence))
            else:
                self.state = "to_review"
                lines.append("รอคนยืนยัน (%.1f%%)" % confidence)
        except Exception as exc:  # noqa: BLE001 — ต้องไม่ทำให้ cron ล้ม
            _logger.exception("od19_document_intake: ประมวลผล inbox %s ล้มเหลว", self.id)
            self.state = "failed"
            lines.append("ผิดพลาด: %s" % exc)
        self.log = "\n".join(lines)

    def action_process(self):
        for inbox in self:
            inbox._od19_process()

    @api.model
    def _cron_process_inbox(self):
        pending = self.search([("state", "in", ("new", "failed"))], limit=50)
        for inbox in pending:
            inbox._od19_process()
