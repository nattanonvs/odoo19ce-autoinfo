# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestDocumentSearchPerf(TransactionCase):
    """ยืนยันว่าดัชนี GIN trigram มีจริงและถูกเลือกใช้เมื่อ seq scan ถูกปิด"""

    def _explain(self, sql, params=None):
        self.env.cr.execute("SET LOCAL enable_seqscan = off")
        self.env.cr.execute("EXPLAIN " + sql, params or ())
        return "\n".join(row[0] for row in self.env.cr.fetchall())

    def test_name_trigram_index_exists(self):
        self.env.cr.execute(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'ir_attachment' AND indexdef ILIKE '%gin_trgm_ops%';",
        )
        defs = " ".join(row[0] for row in self.env.cr.fetchall())
        self.assertIn("name", defs)

    def test_content_trigram_index_used(self):
        plan = self._explain(
            "SELECT id FROM od19_document_extract "
            "WHERE text_content ILIKE %s",
            ("%สัญญาจ้างเหมา%",),
        )
        self.assertIn("Index", plan)
        self.assertIn("trgm", plan.lower())

    def test_name_trigram_index_used(self):
        plan = self._explain(
            "SELECT id FROM ir_attachment WHERE name ILIKE %s",
            ("%ใบเสร็จ%",),
        )
        self.assertIn("Index", plan)
        self.assertIn("trgm", plan.lower())
