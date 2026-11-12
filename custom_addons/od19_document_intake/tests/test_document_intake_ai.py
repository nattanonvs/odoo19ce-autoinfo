# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.od19_ai_assistant.lib.client import AiClientError


@tagged("post_install", "-at_install")
class TestIntakeAi(TransactionCase):

    def setUp(self):
        super().setUp()
        self.category = self.env["od19.document.category"].create({
            "name": "ใบเสร็จรับเงิน", "code": "SAL_RECEIPT",
        })
        self.channel = self.env["od19.document.channel"].create({
            "name": "พอร์ทัล", "kind": "portal", "enable_ai": True,
        })
        self.inbox = self.env["od19.document.inbox"].create({
            "name": "receipt.pdf", "filename": "receipt.pdf",
            "file": base64.b64encode(b"receipt thai text"),
            "channel_id": self.channel.id,
        })

    def test_ai_returns_category(self):
        answer = '{"category_code": "SAL_RECEIPT", "confidence": 88}'
        with patch(
            "odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion",
            return_value=answer,
        ):
            category, _partner, confidence, method = self.inbox._od19_classify_with_ai()
        self.assertEqual(category, self.category)
        self.assertEqual(confidence, 88.0)
        self.assertEqual(method, "ai")

    def test_ai_endpoint_error_is_swallowed(self):
        with patch(
            "odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion",
            side_effect=AiClientError("boom"),
        ):
            category, _partner, confidence, method = self.inbox._od19_classify_with_ai()
        self.assertFalse(category)
        self.assertEqual(confidence, 0.0)
        self.assertEqual(method, "ai")

    def test_ai_unknown_category_is_ignored(self):
        answer = '{"category_code": "NOPE", "confidence": 95}'
        with patch(
            "odoo.addons.od19_document_intake.models.od19_document_inbox.chat_completion",
            return_value=answer,
        ):
            category, _partner, _conf, _method = self.inbox._od19_classify_with_ai()
        self.assertFalse(category)
