# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentChannel(TransactionCase):
    """ตรวจโมเดลช่องทางรับเข้า + กฎ constrains"""

    def test_channel_registered(self):
        self.assertIn("od19.document.channel", self.env)

    def test_folder_kind_requires_path(self):
        with self.assertRaises(ValidationError):
            self.env["od19.document.channel"].create({
                "name": "โฟลเดอร์ไม่มีพาธ",
                "kind": "folder",
            })

    def test_email_kind_requires_alias(self):
        with self.assertRaises(ValidationError):
            self.env["od19.document.channel"].create({
                "name": "อีเมลไม่มี alias",
                "kind": "email_alias",
            })

    def test_portal_channel_created(self):
        channel = self.env["od19.document.channel"].create({
            "name": "พอร์ทัล",
            "kind": "portal",
        })
        self.assertEqual(channel.kind, "portal")
