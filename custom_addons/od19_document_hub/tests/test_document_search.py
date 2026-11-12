# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestDocumentSearch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Attachment = cls.env["ir.attachment"]
        cls.Extract = cls.env["od19.document.extract"]
        cls.att_name = cls.Attachment.create({
            "name": "ใบเสร็จค่าไฟฟ้า_มีนาคม.pdf",
            "raw": b"dummy",
        })
        cls.att_content = cls.Attachment.create({
            "name": "scan_0001.pdf",
            "raw": b"dummy",
        })
        cls.Extract.create({
            "attachment_id": cls.att_content.id,
            "text_content": "สัญญาจ้างเหมาประกอบตู้ หมายเลข PO-2569-0042",
            "engine": "manual",
        })

    def test_search_by_filename(self):
        """ค้นด้วยชื่อไฟล์ (ไทย) ต้องเจอ"""
        found = self.Attachment.search(
            [("od19_search_text", "ilike", "ใบเสร็จค่าไฟฟ้า")],
        )
        self.assertIn(self.att_name, found)

    def test_search_by_content(self):
        """ค้นด้วยข้อความในไฟล์ (ไทย) ต้องเจอ แม้ชื่อไฟล์ไม่ตรง"""
        found = self.Attachment.search(
            [("od19_search_text", "ilike", "PO-2569-0042")],
        )
        self.assertIn(self.att_content, found)
        self.assertNotIn(self.att_name, found)

    def test_search_combined_name_or_content(self):
        """กล่องเดียวค้นทั้งชื่อและเนื้อหา"""
        found = self.Attachment.search(
            [("od19_search_text", "ilike", "ประกอบตู้")],
        )
        self.assertIn(self.att_content, found)

    def test_extract_relation(self):
        """ir.attachment ต้องเห็น od19_extract_ids ย้อนกลับ"""
        self.assertEqual(len(self.att_content.od19_extract_ids), 1)

    def test_search_empty_term_returns_all(self):
        """ค่าว่างไม่กรองออก"""
        found = self.Attachment.search([("od19_search_text", "ilike", "")])
        self.assertIn(self.att_name, found)
        self.assertIn(self.att_content, found)
