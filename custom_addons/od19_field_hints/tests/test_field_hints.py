# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestFieldHints(TransactionCase):
    def test_model_is_available(self):
        """โมดูลต้องลงทะเบียน AbstractModel od19.field.hints ให้เรียกใช้ได้"""
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertTrue(config["enabled"])

    def test_auto_hints_cover_common_types(self):
        config = self.env["od19.field.hints"]._get_client_config()
        auto = config["auto"]
        self.assertEqual(auto["date"], ["example", "วว/ดด/ปปปป"])
        self.assertEqual(auto["monetary"], ["example", "0.00"])
        self.assertEqual(auto["many2one"], ["hint", "เลือกจากรายการ"])
        self.assertEqual(config["default"], ["hint", "ระบุข้อมูล"])

    def test_prefixes(self):
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertEqual(config["prefixes"]["example"], "ตัวอย่าง:")
        self.assertEqual(config["prefixes"]["hint"], "แนะนำ:")
        self.assertEqual(config["prefixes"]["warning"], "สำคัญ:")

    def test_overrides_shape(self):
        config = self.env["od19.field.hints"]._get_client_config()
        entry = config["overrides"]["res.partner"]["name"]
        self.assertEqual(entry["kind"], "example")
        self.assertTrue(entry["text"].startswith("เช่น:"))

    def test_custom_models_detects_od19_fields(self):
        """โมเดลที่มีฟิลด์จากโมดูล od19_* ต้องถูกตรวจพบ"""
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertIn("res.partner", config["custom_models"])

    def test_custom_models_excludes_pure_core_models(self):
        """โมเดล Core ล้วน ๆ ต้องไม่อยู่ในรายการ"""
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertNotIn("ir.ui.view", config["custom_models"])
