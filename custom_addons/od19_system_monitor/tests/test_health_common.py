# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import TransactionCase, tagged

from odoo.addons.od19_system_monitor.models.od19_health_common import (
    compare,
    human_bytes,
)


@tagged("post_install", "-at_install")
class TestHealthCommon(TransactionCase):
    """ทดสอบฟังก์ชันช่วยเหลือร่วม (แปลงไบต์ + ตัวเปรียบเทียบของ rule engine)."""

    def test_human_bytes_units(self):
        self.assertEqual(human_bytes(0), "0.0 B")
        self.assertEqual(human_bytes(512), "512.0 B")
        self.assertEqual(human_bytes(1024), "1.0 KB")
        self.assertEqual(human_bytes(1536), "1.5 KB")
        self.assertEqual(human_bytes(1024**2), "1.0 MB")
        self.assertEqual(human_bytes(1024**3), "1.0 GB")

    def test_human_bytes_invalid(self):
        # ค่า None ถือเป็น 0 และค่าที่แปลงไม่ได้ต้องคืน "-" (ไม่ทำให้รายงานพัง)
        self.assertEqual(human_bytes(None), "0.0 B")
        self.assertEqual(human_bytes("not-a-number"), "-")

    def test_compare_numeric_operators(self):
        self.assertTrue(compare("gt", 10, 5))
        self.assertFalse(compare("gt", 5, 10))
        self.assertTrue(compare("ge", 10, 10))
        self.assertTrue(compare("lt", 3, 9))
        self.assertTrue(compare("le", 9, 9))
        self.assertTrue(compare("eq", 4, 4))
        self.assertTrue(compare("ne", 4, 5))
        self.assertFalse(compare("ne", 4, 4))

    def test_compare_numeric_strings(self):
        self.assertTrue(compare("gt", "10", "9"))
        self.assertTrue(compare("eq", "1.50", "1.5"))

    def test_compare_text_fallback(self):
        # เทียบแบบข้อความเมื่อไม่ใช่ตัวเลข (เช่น status eq down)
        self.assertTrue(compare("eq", "down", "down"))
        self.assertTrue(compare("ne", "down", "ok"))
        self.assertFalse(compare("gt", "down", "ok"))

    def test_compare_contains(self):
        self.assertTrue(compare("contains", "an error occurred", "error"))
        self.assertFalse(compare("contains", "all good", "error"))
        self.assertTrue(compare("contains", None, ""))

    def test_compare_unknown_operator(self):
        self.assertFalse(compare("bogus", 1, 2))
