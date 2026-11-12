# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import hashlib
import logging

from odoo import api, fields, models

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
