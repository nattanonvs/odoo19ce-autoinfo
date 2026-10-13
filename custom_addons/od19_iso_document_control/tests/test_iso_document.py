# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestIsoDocumentSequence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Doc = cls.env["od19.iso.document"]
        cls.Category = cls.env["od19.iso.document.category"]
        cls.Dept = cls.env["hr.department"]

        cls.cat_fm = cls.env.ref("od19_iso_document_control.iso_doc_cat_fm")
        cls.cat_proc = cls.env.ref("od19_iso_document_control.iso_doc_cat_proc")
        cls.dept = cls.Dept.create({"name": "Purchasing", "code": "PU"})

    def _create_doc(self, **overrides):
        vals = {
            "document_title": "Test Document",
            "category_id": self.cat_fm.id,
            "department_id": self.dept.id,
        }
        vals.update(overrides)
        return self.Doc.create(vals)

    # ------------------------------------------------------------------
    # Auto-sequence
    # ------------------------------------------------------------------
    def test_code_auto_generated(self):
        doc = self._create_doc()
        self.assertTrue(doc.code)
        self.assertNotEqual(doc.code, "/")
        self.assertTrue(doc.code.startswith("FM-PU-"))

    def test_code_includes_department_code(self):
        doc = self._create_doc()
        self.assertIn("PU", doc.code.split("-"))

    def test_code_increments(self):
        doc1 = self._create_doc()
        doc2 = self._create_doc()
        num1 = int(doc1.code.split("-")[-1])
        num2 = int(doc2.code.split("-")[-1])
        self.assertEqual(num2, num1 + 1)

    def test_code_falls_back_without_department(self):
        doc = self._create_doc(department_id=False)
        self.assertTrue(doc.code.startswith("FM-XX-"))

    def test_code_generated_on_write_when_missing(self):
        doc = self.Doc.create(
            {
                "document_title": "No Code Yet",
                "category_id": self.cat_fm.id,
            }
        )
        # code should be / or generated with XX
        self.assertTrue(doc.code)
        doc.write({"department_id": self.dept.id})
        self.assertTrue(doc.code.startswith("FM-PU-"))

    def test_different_categories_use_different_sequences(self):
        doc_fm = self._create_doc(category_id=self.cat_fm.id)
        doc_proc = self._create_doc(category_id=self.cat_proc.id)
        self.assertTrue(doc_fm.code.startswith("FM-"))
        self.assertTrue(doc_proc.code.startswith("PROC-"))

    # ------------------------------------------------------------------
    # department_code related field
    # ------------------------------------------------------------------
    def test_department_code_related(self):
        doc = self._create_doc()
        self.assertEqual(doc.department_code, "PU")
