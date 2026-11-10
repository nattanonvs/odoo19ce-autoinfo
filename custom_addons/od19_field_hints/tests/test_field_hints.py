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
