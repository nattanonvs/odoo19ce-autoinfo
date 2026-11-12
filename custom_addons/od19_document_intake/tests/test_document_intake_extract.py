# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIntakeExtract(TransactionCase):

    def _make_attachment(self, name, mimetype, content):
        return self.env["ir.attachment"].create({
            "name": name, "mimetype": mimetype,
            "datas": base64.b64encode(content),
        })

    def test_extract_plain_text(self):
        attachment = self._make_attachment(
            "note.txt", "text/plain", "ใบเสร็จรับเงิน ค่าบริการ".encode("utf-8"),
        )
        extract = attachment._od19_run_extraction()
        self.assertTrue(extract)
        self.assertIn("ค่าบริการ", extract.text_content)
        self.assertEqual(attachment.od19_index_state, "done")

    def test_extract_empty_content_creates_no_record(self):
        attachment = self._make_attachment("empty.txt", "text/plain", b"")
        extract = attachment._od19_run_extraction()
        self.assertFalse(extract)
        self.assertIn(attachment.od19_index_state, ("skipped", "done"))

    def test_extract_unsupported_mimetype_is_skipped(self):
        attachment = self._make_attachment(
            "photo.xyz", "application/octet-stream", b"\x00\x01\x02",
        )
        attachment._od19_run_extraction()
        self.assertEqual(attachment.od19_index_state, "skipped")

    def test_extract_large_file_is_skipped(self):
        content = b"a" * (26 * 1024 * 1024)  # เกิน MAX_EXTRACT_SIZE (25 MB)
        attachment = self._make_attachment("big.txt", "text/plain", content)
        attachment._od19_run_extraction()
        self.assertEqual(attachment.od19_index_state, "skipped")
