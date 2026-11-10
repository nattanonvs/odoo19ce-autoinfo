# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRetentionPolicy(TransactionCase):

    def test_create_policy(self):
        policy = self.env["od19.document.retention.policy"].create({
            "name": "บัญชี 5 ปี",
            "duration_month": 60,
            "action": "delete",
        })
        self.assertEqual(policy.duration_month, 60)

    def test_duration_must_be_positive(self):
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                self.env["od19.document.retention.policy"].create({
                    "name": "ผิด", "duration_month": 0, "action": "review",
                })

