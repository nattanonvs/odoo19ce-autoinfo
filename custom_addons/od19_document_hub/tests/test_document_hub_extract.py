# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentExtract(TransactionCase):

    def _make_attachment(self):
        return self.env["ir.attachment"].create({
            "name": "inv.txt", "datas": base64.b64encode(b"invoice"),
        })

    def test_create_extract(self):
        att = self._make_attachment()
        extract = self.env["od19.document.extract"].create({
            "attachment_id": att.id,
            "text_content": "ใบกำกับภาษี เลขที่ INV-2569-0001",
            "engine": "pdfminer",
            "lang": "th",
        })
        self.assertEqual(extract.attachment_id, att)

    def test_one_extract_per_attachment(self):
        att = self._make_attachment()
        self.env["od19.document.extract"].create({
            "attachment_id": att.id, "text_content": "x",
        })
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["od19.document.extract"].create({
                    "attachment_id": att.id, "text_content": "y",
                })

    def test_trigram_search_thai(self):
        att = self._make_attachment()
        self.env["od19.document.extract"].create({
            "attachment_id": att.id, "text_content": "ใบเสร็จรับเงิน ค่าบริการรายเดือน",
        })
        found = self.env["od19.document.extract"].search([
            ("text_content", "ilike", "ค่าบริการ"),
        ])
        self.assertTrue(found)

    def test_cascade_delete(self):
        att = self._make_attachment()
        extract = self.env["od19.document.extract"].create({
            "attachment_id": att.id, "text_content": "z",
        })
        att.unlink()
        self.assertFalse(extract.exists())
