# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDocumentIntakeModule(TransactionCase):
    """ตรวจว่าโมดูลติดตั้งได้ และ dependency พร้อม"""

    def test_module_installed(self):
        module = self.env["ir.module.module"].search(
            [("name", "=", "od19_document_intake")], limit=1
        )
        self.assertTrue(module, "ต้องพบโมดูล od19_document_intake")
        self.assertEqual(module.state, "installed")

    def test_hub_dependency_available(self):
        # ต้องใช้ของ hub ได้ (หมวด + extract)
        self.assertIn("od19.document.category", self.env)
        self.assertIn("od19.document.extract", self.env)
