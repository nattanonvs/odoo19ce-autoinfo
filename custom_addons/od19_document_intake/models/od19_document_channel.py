# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import hashlib
import logging
import os

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

KIND_SELECTION = [
    ("folder", "โฟลเดอร์เฝ้าดู"),
    ("email_alias", "อีเมล (Alias)"),
    ("portal", "พอร์ทัล / อัปโหลด"),
]


class Od19DocumentChannel(models.Model):
    _name = "od19.document.channel"
    _description = "ช่องทางรับเอกสารเข้า"
    _order = "sequence, name"

    name = fields.Char("ชื่อช่องทาง", required=True)
    sequence = fields.Integer(default=10)
    kind = fields.Selection(KIND_SELECTION, "ประเภท", required=True, default="portal")
    path = fields.Char(
        "พาธโฟลเดอร์",
        help=r"พาธในเครื่องหรือ network share เช่น D:\Intake หรือ \\server\docs",
    )
    alias_id = fields.Many2one(
        "mail.alias", "อีเมล Alias", ondelete="restrict",
        help="Alias ที่ตั้ง Alias Model = od19.document.inbox",
    )
    default_category_id = fields.Many2one(
        "od19.document.category", "หมวดเริ่มต้น", ondelete="restrict",
        help="ใช้เมื่อกฎและ AI ไม่สรุปได้ (ยังไม่ถึงเกณฑ์ confidence)",
    )
    enable_ocr = fields.Boolean("เปิด OCR", default=True)
    enable_ai = fields.Boolean("เปิดจัดหมวดด้วย AI", default=True)
    active = fields.Boolean(default=True)
    last_scan_at = fields.Datetime("สแกนล่าสุด", readonly=True)
    last_error = fields.Text("ข้อผิดพลาดล่าสุด", readonly=True)

    @api.constrains("kind", "path", "alias_id")
    def _check_kind_config(self):
        for channel in self:
            if channel.kind == "folder" and not channel.path:
                raise ValidationError("ช่องทาง 'โฟลเดอร์เฝ้าดู' ต้องระบุพาธโฟลเดอร์")
            if channel.kind == "email_alias" and not channel.alias_id:
                raise ValidationError("ช่องทาง 'อีเมล (Alias)' ต้องผูก Alias")

    # ------------------------------------------------------------------
    # Folder scanning + cron
    # ------------------------------------------------------------------
    def _od19_scan_channel(self):
        """สแกนโฟลเดอร์ของช่องทางนี้ แล้วสร้าง inbox สำหรับไฟล์ใหม่"""
        self.ensure_one()
        created = 0
        if self.kind != "folder" or not self.path:
            return created
        if not os.path.isdir(self.path):
            self.last_error = "ไม่พบโฟลเดอร์: %s" % self.path
            return created

        Inbox = self.env["od19.document.inbox"]
        for filename in sorted(os.listdir(self.path)):
            filepath = os.path.join(self.path, filename)
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "rb") as handle:
                    data = handle.read()
            except OSError as exc:
                self.last_error = "อ่านไฟล์ %s ไม่ได้: %s" % (filename, exc)
                continue
            checksum = hashlib.sha1(data).hexdigest()
            already = Inbox.search_count([
                ("channel_id", "=", self.id), ("checksum", "=", checksum),
            ])
            if already:
                continue
            Inbox.create({
                "name": filename[:200],
                "filename": filename[:200],
                "file": base64.b64encode(data),
                "checksum": checksum,
                "channel_id": self.id,
                "state": "new",
            })
            created += 1

        self.last_scan_at = fields.Datetime.now()
        self.last_error = False
        return created

    @api.model
    def _cron_scan_channels(self):
        """cron: ไล่ทุกช่องทางโฟลเดอร์ — ถ้าช่องทางใดล้ม ต้องไม่ทำให้ cron ทั้งรอบล้ม"""
        for channel in self.search([("kind", "=", "folder"), ("active", "=", True)]):
            try:
                channel._od19_scan_channel()
            except Exception as exc:  # noqa: BLE001 — guard ต่อช่องทางตามสเปก §9
                _logger.exception("od19_document_intake: สแกนช่องทาง %s ล้มเหลว", channel.name)
                channel.last_error = "สแกนล้มเหลว: %s" % exc
