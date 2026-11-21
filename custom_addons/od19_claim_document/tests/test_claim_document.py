# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestClaimDocument(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Form = cls.env["od19.claim.form"]
        cls.Request = cls.env["od19.claim.request"]
        cls.Category = cls.env["od19.document.category"]
        cls.Attachment = cls.env["ir.attachment"]

    def _make_attachment(self, name):
        return self.Attachment.create({
            "name": name,
            "datas": "JVBERi0xLjQK",
        })

    def test_categories_loaded(self):
        for code in ("CLM", "REQ", "FRM", "CLM_WRT", "CLM_RMA", "REQ_BIL", "FRM_DAR"):
            self.assertTrue(
                self.Category.search([("code", "=", code)], limit=1),
                f"ไม่พบหมวดรหัส {code}",
            )

    def test_claim_form_print_logs_history(self):
        attachment = self._make_attachment("form.pdf")
        form = self.Form.create({
            "name": "แบบฟอร์มเคลมประกัน",
            "code": "CLM-F-001",
            "claim_type": "warranty",
            "template_attachment_id": attachment.id,
        })
        action = form.action_print_form()
        form.invalidate_recordset()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(len(form.print_ids), 1)
        self.assertEqual(form.print_count, 1)
        self.assertEqual(form.print_ids.printed_by_id, self.env.user)

    def test_claim_form_print_without_template_raises(self):
        form = self.Form.create({
            "name": "ไม่มีไฟล์",
            "code": "CLM-F-002",
            "claim_type": "return",
        })
        with self.assertRaises(UserError):
            form.action_print_form()

    def test_claim_request_sequence_and_state(self):
        rec = self.Request.create({
            "claim_type": "warranty",
            "subject": "ลูกค้าเคลมอะไหล่",
        })
        self.assertNotEqual(rec.name, "/")
        self.assertEqual(rec.state, "draft")
        rec.action_submit()
        self.assertEqual(rec.state, "submitted")
        rec.action_approve()
        self.assertEqual(rec.state, "approved")
        rec.action_close()
        self.assertEqual(rec.state, "closed")

    def test_claim_request_print_delegates_to_form(self):
        attachment = self._make_attachment("f.pdf")
        form = self.Form.create({
            "name": "แบบฟอร์มเรียกร้องผู้ขาย",
            "code": "CLM-F-003",
            "claim_type": "supplier",
            "template_attachment_id": attachment.id,
        })
        rec = self.Request.create({
            "claim_type": "supplier",
            "subject": "เรียกร้องผู้ขาย",
            "form_id": form.id,
        })
        res = rec.action_print_form()
        form.invalidate_recordset()
        self.assertEqual(res["type"], "ir.actions.act_url")
        self.assertEqual(form.print_count, 1)

    def test_claim_request_attachments(self):
        rec = self.Request.create({
            "claim_type": "insurance",
            "subject": "เรียกร้องประกันภัย",
            "attachment_ids": [(0, 0, {"name": "evidence.pdf", "datas": "JVBERi0xLjQK"})],
        })
        rec.invalidate_recordset()
        self.assertEqual(rec.attachment_count, 1)
