# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Scan-to-article wizard: turn phone-camera scans into ready-made Knowledge
articles (``document.page``) with a styled, template-driven body.
"""

import html as html_mod
import logging
import re

from odoo import api, fields, models
from odoo.exceptions import UserError

from .od19_ocr_service import ENGINE_SELECTION as OCR_ENGINE_SELECTION

_logger = logging.getLogger(__name__)

PALETTE = {
    "primary": "#8a1c2b",
    "dark": "#3a0d13",
    "accent": "#c9a227",
    "paper": "#ffffff",
    "bg": "#f7f3f0",
    "text": "#2b2b2b",
    "muted": "#7a7a7a",
    "line": "#e6ddd8",
}

CATEGORY_SELECTION = [
    ("general", "ทั่วไป"),
    ("procedure", "ขั้นตอนการปฏิบัติงาน (Procedure)"),
    ("troubleshooting", "แก้ไขปัญหา (Troubleshooting)"),
    ("faq", "คำถามที่พบบ่อย (FAQ)"),
]

# Each template is a list of ``(heading, kind)`` sections:
#   ``raw``         -> holds the OCR text
#   ``checklist``   -> bullet scaffold for the user to fill
#   ``placeholder`` -> a single muted prompt
TEMPLATE_DEFS = {
    "general": {
        "label": "บันทึก / สรุปทั่วไป",
        "subtitle": "สรุปเนื้อหาจากเอกสารที่สแกน",
        "sections": [("เนื้อหาที่สแกนได้", "raw")],
    },
    "meeting": {
        "label": "รายงานการประชุม",
        "subtitle": "บันทึกการประชุม (Minutes of Meeting)",
        "sections": [
            ("ข้อมูลการประชุม", "placeholder"),
            ("วาระและประเด็นที่หารือ", "raw"),
            ("มติที่ประชุม", "checklist"),
            ("งานที่ต้องทำต่อ (Action Items)", "checklist"),
        ],
    },
    "sop": {
        "label": "ขั้นตอนการปฏิบัติงาน (SOP)",
        "subtitle": "คู่มือวิธีปฏิบัติงานมาตรฐาน",
        "sections": [
            ("วัตถุประสงค์", "placeholder"),
            ("ขอบเขต", "placeholder"),
            ("ขั้นตอนการปฏิบัติ", "raw"),
            ("ผู้รับผิดชอบ", "placeholder"),
            ("เอกสารอ้างอิง", "placeholder"),
        ],
    },
    "troubleshooting": {
        "label": "คู่มือแก้ไขปัญหา",
        "subtitle": "Troubleshooting Guide",
        "sections": [
            ("อาการที่พบ / ข้อมูลจากเอกสาร", "raw"),
            ("สาเหตุ", "checklist"),
            ("วิธีแก้ไข", "checklist"),
            ("การป้องกันไม่ให้เกิดซ้ำ", "placeholder"),
        ],
    },
    "howto": {
        "label": "คู่มือการใช้งาน (How-to)",
        "subtitle": "ขั้นตอนการใช้งานแบบทีละขั้น",
        "sections": [
            ("ภาพรวม", "placeholder"),
            ("สิ่งที่ต้องเตรียม", "checklist"),
            ("ขั้นตอน", "raw"),
            ("เคล็ดลับ", "placeholder"),
        ],
    },
    "product": {
        "label": "ข้อมูลสินค้า / สเปก",
        "subtitle": "Product Specification",
        "sections": [
            ("ภาพรวมสินค้า", "raw"),
            ("คุณลักษณะ / สเปก", "checklist"),
            ("ข้อกำหนด", "placeholder"),
            ("หมายเหตุ", "placeholder"),
        ],
    },
}


class Od19ScanPage(models.TransientModel):
    _name = "od19.scan.page"
    _description = "ภาพสแกนสำหรับแปลงเป็นบทความ (OD19)"
    _order = "id"

    wizard_id = fields.Many2one(
        "od19.scan.article.wizard", required=True, ondelete="cascade"
    )
    image = fields.Binary("ภาพที่สแกน", attachment=True)
    image_filename = fields.Char("ชื่อไฟล์")
    ocr_text = fields.Text("ข้อความที่อ่านได้")
    ocr_engine = fields.Char("ตัวอ่าน")
    state = fields.Selection(
        [("draft", "รออ่านข้อความ"), ("done", "อ่านแล้ว"), ("error", "ผิดพลาด")],
        default="draft",
        string="สถานะ",
    )
    error_message = fields.Char("ข้อความผิดพลาด")


class Od19ScanArticleWizard(models.TransientModel):
    _name = "od19.scan.article.wizard"
    _description = "แปลงไฟล์สแกนเป็นบทความ Knowledge (OD19)"

    page_ids = fields.One2many(
        "od19.scan.page", "wizard_id", string="ภาพที่สแกน", copy=True
    )
    title = fields.Char("หัวเรื่องบทความ", required=True)
    template = fields.Selection(
        [(key, value["label"]) for key, value in TEMPLATE_DEFS.items()],
        string="เทมเพลตบทความ",
        default="general",
        required=True,
    )
    category = fields.Selection(
        CATEGORY_SELECTION, string="หมวดความรู้", default="general"
    )
    keywords = fields.Char("คำค้นหา (คั่นด้วยจุลภาค)")
    language = fields.Selection(
        [("auto", "ตรวจจับอัตโนมัติ"), ("th", "ไทย"), ("en", "อังกฤษ")],
        string="ภาษาของเอกสาร",
        default="auto",
    )
    ocr_engine = fields.Selection(
        OCR_ENGINE_SELECTION,
        string="ตัวอ่านข้อความ",
        default="auto",
    )
    run_ocr = fields.Boolean("อ่านข้อความอัตโนมัติ (OCR)", default=True)
    text_content = fields.Text("เนื้อหาที่อ่านได้ (แก้ไขได้)")
    engine_used = fields.Char("ตัวอ่านที่ใช้ล่าสุด", readonly=True)
    attach_images = fields.Boolean("แนบภาพต้นฉบับไว้ในบทความ", default=True)
    parent_id = fields.Many2one("document.page", "วางไว้ในหมวด")
    article_id = fields.Many2one("document.page", "บทความที่สร้าง", readonly=True)
    state = fields.Selection(
        [("input", "กรอกข้อมูล"), ("done", "สร้างบทความแล้ว")], default="input"
    )

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------
    def action_run_ocr(self):
        self.ensure_one()
        if not self.page_ids:
            raise UserError("กรุณาเพิ่มภาพที่สแกนอย่างน้อย 1 ภาพก่อน")
        ocr = self.env["od19.ocr.service"]
        collected = []
        used = set()
        for page in self.page_ids:
            if not page.image:
                continue
            try:
                result = ocr.extract_text(
                    page.image,
                    page.image_filename or "scan.jpg",
                    engine=self.ocr_engine,
                    language=self.language,
                )
                page.write(
                    {
                        "ocr_text": result["text"],
                        "ocr_engine": result["engine"],
                        "state": "done",
                        "error_message": False,
                    }
                )
                if result["text"]:
                    collected.append(result["text"])
                used.add(result["engine"])
            except UserError as exc:
                page.write({"state": "error", "error_message": str(exc)})
        if collected:
            self.text_content = "\n\n".join(collected)
        if used:
            self.engine_used = ", ".join(sorted(used))
        return self._reload()

    # ------------------------------------------------------------------
    # Article creation
    # ------------------------------------------------------------------
    def action_create_article(self):
        self.ensure_one()
        title = (self.title or "").strip()
        if not title:
            raise UserError("กรุณากรอกหัวเรื่องบทความ")
        if not self.page_ids and not (self.text_content or "").strip():
            raise UserError("กรุณาเพิ่มภาพที่สแกนหรือพิมพ์เนื้อหา")

        # Auto-read any page that has not been processed yet when OCR is on.
        if self.run_ocr and any(
            page.image and page.state == "draft" for page in self.page_ids
        ):
            self.action_run_ocr()

        body = self._build_body_html()
        article = self.env["document.page"].create(
            {
                "name": title,
                "type": "content",
                "parent_id": self.parent_id.id or False,
                "content": self._wrap_article(body),
                "category": self.category or "general",
                "keywords": self.keywords or "",
            }
        )
        if self.attach_images:
            images_html = self._attach_scan_images(article)
            if images_html:
                article.content = article.content + images_html

        self.write({"article_id": article.id, "state": "done"})
        return {
            "type": "ir.actions.act_window",
            "name": title,
            "res_model": "document.page",
            "res_id": article.id,
            "view_mode": "form",
            "target": "current",
        }

    def _attach_scan_images(self, article):
        """Copy each scanned page into the article's attachments and inline them."""
        attachments = self.env["ir.attachment"]
        for index, page in enumerate(self.page_ids, start=1):
            if not page.image:
                continue
            attachments |= self.env["ir.attachment"].create(
                {
                    "name": page.image_filename or ("scan-%s.jpg" % index),
                    "res_model": "document.page",
                    "res_id": article.id,
                    "datas": page.image,
                    "mimetype": "image/jpeg",
                }
            )
        if not attachments:
            return ""
        figures = "".join(
            '<figure style="margin:14px 0;text-align:center">'
            '<img src="/web/image/%s" alt="ภาพที่สแกน" '
            'style="max-width:100%%;border:1px solid %s;border-radius:10px"/>'
            '<figcaption style="font-size:12px;color:%s;margin-top:6px">'
            "ภาพที่สแกน %s</figcaption></figure>"
            % (att.id, PALETTE["line"], PALETTE["muted"], att.name)
            for att in attachments
        )
        return self._section_html(
            "ภาพเอกสารต้นฉบับ",
            figures,
            number="A",
        )

    # ------------------------------------------------------------------
    # HTML building
    # ------------------------------------------------------------------
    def _wrap_article(self, body_html):
        spec = TEMPLATE_DEFS.get(self.template, TEMPLATE_DEFS["general"])
        chips = [
            ("วันที่", self._today_label()),
            ("หมวด", self._category_label()),
            ("ตัวอ่าน", self.engine_used or "—"),
            ("จำนวนภาพ", str(len(self.page_ids))),
        ]
        chip_html = "".join(
            '<span style="display:inline-block;margin:0 8px 8px 0;padding:4px 12px;'
            'border:1px solid rgba(255,255,255,.45);border-radius:999px;'
            'font-size:12px;color:#fff">%s: %s</span>'
            % (html_mod.escape(label), html_mod.escape(value))
            for label, value in chips
        )
        return (
            '<div style="font-family:Sarabun,Tahoma,Arial,sans-serif;'
            'color:%(text)s;line-height:1.65;max-width:860px">'
            '<section style="background:linear-gradient(135deg,%(primary)s,%(dark)s);'
            'border-radius:16px;padding:28px 32px;color:#fff;'
            'box-shadow:0 10px 24px rgba(58,13,19,.18)">'
            '<div style="font-size:12px;letter-spacing:.18em;'
            'text-transform:uppercase;color:%(accent)s">OD19 · สแกนอัตโนมัติ</div>'
            '<h1 style="margin:8px 0 6px;font-size:28px;line-height:1.3;color:#fff">'
            "%(title)s</h1>"
            '<div style="color:#f3d9d9;font-size:15px">%(subtitle)s</div>'
            '<div style="margin-top:16px">%(chips)s</div>'
            "</section>"
            '<div style="background:%(paper)s;border:1px solid %(line)s;'
            'border-radius:16px;padding:26px 32px;margin-top:18px">%(body)s</div>'
            '<p style="font-size:12px;color:%(muted)s;margin-top:14px">'
            "สร้างจากไฟล์สแกนด้วย OD19 Document Scan — "
            "กรุณาตรวจทานความถูกต้องก่อนเผยแพร่</p>"
            "</div>"
        ) % {
            "text": PALETTE["text"],
            "primary": PALETTE["primary"],
            "dark": PALETTE["dark"],
            "accent": PALETTE["accent"],
            "paper": PALETTE["paper"],
            "line": PALETTE["line"],
            "muted": PALETTE["muted"],
            "title": html_mod.escape(self.title or ""),
            "subtitle": html_mod.escape(spec["subtitle"]),
            "chips": chip_html,
            "body": body_html,
        }

    def _build_body_html(self):
        spec = TEMPLATE_DEFS.get(self.template, TEMPLATE_DEFS["general"])
        parts = []
        for index, (heading, kind) in enumerate(spec["sections"], start=1):
            parts.append(self._section_html(heading, self._section_body(kind), index))
        return "".join(parts)

    def _section_html(self, heading, inner, number=None):
        badge = ""
        if number is not None:
            badge = (
                '<span style="display:inline-flex;align-items:center;'
                "justify-content:center;width:26px;height:26px;margin-right:10px;"
                "border-radius:50%%;background:%s;color:#fff;font-size:13px;"
                'font-weight:600">%s</span>' % (PALETTE["primary"], html_mod.escape(str(number)))
            )
        return (
            '<h2 style="display:flex;align-items:center;font-size:18px;'
            "margin:24px 0 10px;padding-bottom:8px;border-bottom:2px solid %s;"
            'color:%s">%s%s</h2>%s'
            % (PALETTE["line"], PALETTE["dark"], badge, html_mod.escape(heading), inner)
        )

    def _section_body(self, kind):
        if kind == "raw":
            return self._text_to_html(self.text_content)
        if kind == "checklist":
            return (
                '<ul style="margin:0;padding-inline-start:22px;color:%s">'
                "<li>—</li><li>—</li></ul>" % PALETTE["muted"]
            )
        return '<p style="color:%s;font-style:italic">— เติมข้อมูลส่วนนี้ —</p>' % PALETTE["muted"]

    def _text_to_html(self, text):
        if not text or not text.strip():
            return (
                '<p style="color:%s;font-style:italic">'
                "— ยังไม่มีข้อความ กดปุ่ม “อ่านข้อความด้วย OCR” หรือพิมพ์เอง —</p>"
                % PALETTE["muted"]
            )
        blocks = []
        items = []

        def flush_items():
            if items:
                blocks.append(
                    '<ul style="margin:6px 0 14px;padding-inline-start:22px">%s</ul>'
                    % "".join("<li>%s</li>" % item for item in items)
                )
                items.clear()

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                flush_items()
                continue
            bullet = re.match(r"^[-*\u2022\u25cf\u25aa]\s+(.*)$", line)
            numbered = re.match(r"^(\d{1,3})[.)]\s+(.*)$", line)
            if bullet:
                items.append(html_mod.escape(bullet.group(1)))
                continue
            if numbered:
                items.append(html_mod.escape(numbered.group(2)))
                continue
            flush_items()
            blocks.append(
                "<p style=\"margin:6px 0 12px\">%s</p>" % html_mod.escape(line)
            )
        flush_items()
        return "".join(blocks)

    # ------------------------------------------------------------------
    # Small labels
    # ------------------------------------------------------------------
    def _category_label(self):
        for key, label in CATEGORY_SELECTION:
            if key == self.category:
                return label
        return "ทั่วไป"

    def _today_label(self):
        return fields.Date.context_today(self).strftime("%d/%m/%Y")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _reload(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.onchange("template")
    def _onchange_template(self):
        if not self.title:
            spec = TEMPLATE_DEFS.get(self.template)
            if spec:
                self.title = spec["label"]
