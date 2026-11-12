# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIntakeRules(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env["od19.document.category"].create({
            "name": "ใบกำกับภาษีซื้อ", "code": "PUR_TAX",
        })
        self.channel = self.env["od19.document.channel"].create({
            "name": "พอร์ทัล", "kind": "portal",
        })

    def _make_inbox(self, name, text=None):
        return self.env["od19.document.inbox"].create({
            "name": name,
            "filename": name,
            "file": base64.b64encode((text or "x").encode("utf-8")),
            "channel_id": self.channel.id,
        })

    def test_rule_by_filename(self):
        self.env["od19.document.classify.rule"].create({
            "name": "ชื่อไฟล์มีคำว่า TAX",
            "target": "filename", "pattern": "tax", "category_id": self.category.id,
        })
        inbox = self._make_inbox("INV-TAX-2569.pdf")
        category, partner, confidence, method = inbox._od19_classify_by_rules()
        self.assertEqual(category, self.category)
        self.assertEqual(method, "rule")

    def test_rule_no_match_returns_empty(self):
        inbox = self._make_inbox("random.pdf")
        category, partner, confidence, method = inbox._od19_classify_by_rules()
        self.assertFalse(category)

    def test_rule_case_insensitive(self):
        self.env["od19.document.classify.rule"].create({
            "name": "PO", "target": "filename", "pattern": "po",
            "category_id": self.category.id,
        })
        inbox = self._make_inbox("PO-2601.pdf")
        category, _partner, _conf, method = inbox._od19_classify_by_rules()
        self.assertEqual(category, self.category)
