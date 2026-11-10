# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from unittest.mock import Mock

from odoo.http import _request_stack
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.misc import DotDict


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

    def test_settings_toggle_enabled(self):
        settings = self.env["res.config.settings"].create({"od19_field_hints_enabled": False})
        settings.execute()
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertFalse(config["enabled"])
        self.env["ir.config_parameter"].sudo().set_param("od19_field_hints.enabled", "True")

    def test_settings_toggle_apply_core(self):
        settings = self.env["res.config.settings"].create({"od19_field_hints_apply_core": True})
        settings.execute()
        config = self.env["od19.field.hints"]._get_client_config()
        self.assertTrue(config["apply_core"])
        self.env["ir.config_parameter"].sudo().set_param("od19_field_hints.apply_core", "False")

    def test_session_info_contains_field_hints(self):
        """config ต้องถูกส่งไปกับ session_info เพื่อให้ฝั่ง client อ่านได้แบบ synchronous"""
        # core session_info() ต้องมี HTTP request (request.session) จึงต้องจำลอง request
        request = Mock(
            db=self.env.cr.dbname,
            env=self.env,
            session=DotDict({
                "uid": self.env.uid,
                "context": dict(self.env.context),
                "debug": "",
            }),
        )
        _request_stack.push(request)
        try:
            info = self.env["ir.http"].session_info()
        finally:
            _request_stack.pop()
        self.assertIn("od19_field_hints", info)
        self.assertIn("custom_models", info["od19_field_hints"])
