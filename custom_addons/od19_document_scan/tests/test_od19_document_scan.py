# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Unit tests for OD19 Document Scan (OCR service + scan-to-article wizard).

External engines (Ollama Vision / Tesseract) are never contacted: the network
calls are patched so the suite stays deterministic and offline.
"""

import base64
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

# Any bytes are enough for the paths under test; OCR engines are patched and
# the "manual" engine never opens the image.
TINY_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\nOD19-scan-test").decode()


@tagged("post_install", "-at_install")
class TestOd19OcrService(TransactionCase):
    """od19.ocr.service: engine selection, auto fallback, helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ocr = cls.env["od19.ocr.service"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_param(self, key, value):
        self.env["ir.config_parameter"].sudo().set_param("od19_scan.%s" % key, value)

    # ------------------------------------------------------------------
    # Pure helpers
    # ------------------------------------------------------------------
    def test_guess_mimetype(self):
        self.assertEqual(self.Ocr._guess_mimetype("a.JPG"), "image/jpeg")
        self.assertEqual(self.Ocr._guess_mimetype("scan.jpeg"), "image/jpeg")
        self.assertEqual(self.Ocr._guess_mimetype("scan.png"), "image/png")
        self.assertEqual(self.Ocr._guess_mimetype("scan.webp"), "image/webp")
        self.assertEqual(self.Ocr._guess_mimetype("doc.pdf"), "application/pdf")
        self.assertEqual(self.Ocr._guess_mimetype("noext"), "image/jpeg")

    def test_is_pdf(self):
        self.assertTrue(self.Ocr._is_pdf("application/pdf", "x.jpg"))
        self.assertTrue(self.Ocr._is_pdf("image/jpeg", "x.PDF"))
        self.assertFalse(self.Ocr._is_pdf("image/jpeg", "x.jpg"))

    def test_clean_ocr_output(self):
        self.assertEqual(self.Ocr._clean_ocr_output("  hello \r\n"), "hello")
        self.assertEqual(self.Ocr._clean_ocr_output("```\nabc\n```"), "abc")
        self.assertEqual(self.Ocr._clean_ocr_output("```python\nprint(1)\n```"), "print(1)")
        self.assertEqual(self.Ocr._clean_ocr_output(False), "")

    def test_manual_engine_always_available(self):
        self.assertTrue(self.Ocr.engine_available("manual"))
        self.assertIn("manual", self.Ocr.available_engines())
        self.assertFalse(self.Ocr.engine_available("nonsense"))

    def test_default_engine(self):
        self.assertEqual(self.Ocr._default_engine(), "auto")
        self._set_param("ocr_engine", "manual")
        self.assertEqual(self.Ocr._default_engine(), "manual")

    def test_tesseract_lang(self):
        self.assertEqual(self.Ocr._tesseract_lang("th"), "tha+eng")
        self.assertEqual(self.Ocr._tesseract_lang("en"), "eng")
        self.assertEqual(self.Ocr._tesseract_lang("auto"), "tha+eng")
        self._set_param("tesseract_lang", "eng")
        self.assertEqual(self.Ocr._tesseract_lang("th"), "eng")

    # ------------------------------------------------------------------
    # extract_text
    # ------------------------------------------------------------------
    def test_extract_text_empty_raises(self):
        with self.assertRaises(UserError):
            self.Ocr.extract_text(False, "a.jpg")

    def test_extract_text_manual(self):
        result = self.Ocr.extract_text(TINY_B64, "a.jpg", engine="manual")
        self.assertEqual(result, {"text": "", "engine": "manual"})

    def test_extract_text_pdf_routes_to_pdfminer(self):
        Service = type(self.Ocr)
        with patch.object(Service, "_extract_pdf", return_value="PDF TEXT"):
            result = self.Ocr.extract_text(TINY_B64, "doc.pdf")
        self.assertEqual(result, {"text": "PDF TEXT", "engine": "pdfminer"})

    def test_extract_text_ollama(self):
        Service = type(self.Ocr)
        with patch.object(Service, "_extract_with_vision", return_value="Vision text"):
            result = self.Ocr.extract_text(TINY_B64, "a.jpg", engine="ollama")
        self.assertEqual(result, {"text": "Vision text", "engine": "ollama"})

    def test_extract_text_tesseract(self):
        Service = type(self.Ocr)
        with patch.object(Service, "_extract_with_tesseract", return_value="Tess text"):
            result = self.Ocr.extract_text(TINY_B64, "a.jpg", engine="tesseract")
        self.assertEqual(result, {"text": "Tess text", "engine": "tesseract"})

    def test_extract_text_unknown_engine_raises(self):
        with self.assertRaises(UserError):
            self.Ocr.extract_text(TINY_B64, "a.jpg", engine="does-not-exist")

    def test_auto_prefers_vision(self):
        Service = type(self.Ocr)
        with patch.object(Service, "_extract_with_vision", return_value="V"), patch.object(
            Service, "_extract_with_tesseract", return_value="T"
        ):
            result = self.Ocr.extract_text(TINY_B64, "a.jpg", engine="auto")
        self.assertEqual(result, {"text": "V", "engine": "ollama"})

    def test_auto_falls_back_to_tesseract(self):
        Service = type(self.Ocr)
        with patch.object(
            Service, "_extract_with_vision", side_effect=UserError("no vision")
        ), patch.object(Service, "_extract_with_tesseract", return_value="T"):
            result = self.Ocr.extract_text(TINY_B64, "a.jpg", engine="auto")
        self.assertEqual(result, {"text": "T", "engine": "tesseract"})

    def test_auto_all_engines_fail(self):
        Service = type(self.Ocr)
        with patch.object(
            Service, "_extract_with_vision", side_effect=UserError("x")
        ), patch.object(Service, "_extract_with_tesseract", side_effect=UserError("y")):
            with self.assertRaises(UserError):
                self.Ocr.extract_text(TINY_B64, "a.jpg", engine="auto")


@tagged("post_install", "-at_install")
class TestOd19ScanWizard(TransactionCase):
    """od19.scan.article.wizard: OCR collection + article creation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Wizard = cls.env["od19.scan.article.wizard"]
        cls.Page = cls.env["od19.scan.page"]
        cls.DocPage = cls.env["document.page"]
        cls.Attachment = cls.env["ir.attachment"]
        cls.category = cls.DocPage.create({"name": "Scan Category", "type": "category"})

    def _make_wizard(self, **overrides):
        vals = {"title": "Scan Article", "template": "general"}
        vals.update(overrides)
        return self.Wizard.create(vals)

    def _add_page(self, wizard, name="scan.jpg"):
        return self.Page.create(
            {
                "wizard_id": wizard.id,
                "image": TINY_B64,
                "image_filename": name,
            }
        )

    # ------------------------------------------------------------------
    # HTML building
    # ------------------------------------------------------------------
    def test_text_to_html_paragraphs_and_lists(self):
        wiz = self._make_wizard()
        html = wiz._text_to_html("Hello\n- one\n- two\n1. first\n2. second\n\nWorld")
        self.assertIn("Hello", html)
        self.assertIn("<ul", html)
        self.assertEqual(html.count("<li>"), 4)
        self.assertIn("World", html)

    def test_text_to_html_escapes_markup(self):
        wiz = self._make_wizard()
        html = wiz._text_to_html("<script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_text_to_html_empty_placeholder(self):
        wiz = self._make_wizard()
        self.assertIn("ยังไม่มีข้อความ", wiz._text_to_html(""))

    def test_wrap_article_branding(self):
        wiz = self._make_wizard(title="Brand Title")
        html = wiz._wrap_article("<p>body</p>")
        self.assertIn("#8a1c2b", html)
        self.assertIn("Brand Title", html)
        self.assertIn("OD19", html)

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    def test_run_ocr_requires_pages(self):
        with self.assertRaises(UserError):
            self._make_wizard().action_run_ocr()

    def test_create_requires_content(self):
        wiz = self._make_wizard(title="No content", text_content="")
        with self.assertRaises(UserError):
            wiz.action_create_article()

    def test_create_requires_title(self):
        wiz = self._make_wizard(title="   ", text_content="Some body")
        with self.assertRaises(UserError):
            wiz.action_create_article()

    # ------------------------------------------------------------------
    # OCR collection
    # ------------------------------------------------------------------
    def test_run_ocr_manual(self):
        wiz = self._make_wizard(ocr_engine="manual")
        page = self._add_page(wiz)
        wiz.action_run_ocr()
        self.assertEqual(page.state, "done")
        self.assertEqual(page.ocr_engine, "manual")

    def test_run_ocr_collects_text(self):
        Service = type(self.env["od19.ocr.service"])
        wiz = self._make_wizard(ocr_engine="auto")
        page = self._add_page(wiz)
        with patch.object(Service, "_extract_with_vision", return_value="OCR LINE"):
            wiz.action_run_ocr()
        self.assertEqual(page.state, "done")
        self.assertEqual(page.ocr_text, "OCR LINE")
        self.assertIn("OCR LINE", wiz.text_content)
        self.assertEqual(wiz.engine_used, "ollama")

    # ------------------------------------------------------------------
    # Article creation
    # ------------------------------------------------------------------
    def test_create_article_from_typed_text(self):
        wiz = self._make_wizard(
            title="Typed Article",
            text_content="Line A\n- bullet",
            category="faq",
            keywords="alpha, beta",
            parent_id=self.category.id,
        )
        action = wiz.action_create_article()
        self.assertEqual(action["res_model"], "document.page")
        article = self.DocPage.browse(action["res_id"])
        self.assertTrue(article.exists())
        self.assertEqual(article.name, "Typed Article")
        self.assertEqual(article.category, "faq")
        self.assertEqual(article.keywords, "alpha, beta")
        self.assertEqual(article.parent_id, self.category)
        self.assertEqual(article.type, "content")
        self.assertIn("Line A", article.content)
        self.assertIn("<li>bullet</li>", article.content)
        self.assertEqual(wiz.state, "done")
        self.assertEqual(wiz.article_id, article)

    def test_create_article_auto_runs_ocr(self):
        Service = type(self.env["od19.ocr.service"])
        wiz = self._make_wizard(title="Auto OCR", run_ocr=True, ocr_engine="auto")
        page = self._add_page(wiz)
        with patch.object(Service, "_extract_with_vision", return_value="AUTO TEXT"):
            wiz.action_create_article()
        self.assertEqual(page.state, "done")
        self.assertIn("AUTO TEXT", wiz.text_content)

    def test_create_article_all_templates(self):
        for tmpl in ("general", "meeting", "sop", "troubleshooting", "howto", "product"):
            wiz = self._make_wizard(
                title="T-%s" % tmpl, template=tmpl, text_content="Body %s" % tmpl
            )
            action = wiz.action_create_article()
            article = self.DocPage.browse(action["res_id"])
            self.assertIn("Body %s" % tmpl, article.content)

    def test_attach_scan_images(self):
        wiz = self._make_wizard(title="With Images", text_content="Body")
        self._add_page(wiz, "scan1.jpg")
        self._add_page(wiz, "scan2.jpg")
        action = wiz.action_create_article()
        article = self.DocPage.browse(action["res_id"])
        attachments = self.Attachment.search(
            [
                ("res_model", "=", "document.page"),
                ("res_id", "=", article.id),
            ]
        )
        self.assertEqual(len(attachments), 2)
        self.assertIn("ภาพเอกสารต้นฉบับ", article.content)
        self.assertIn("/web/image/", article.content)

    def test_attach_images_disabled(self):
        wiz = self._make_wizard(
            title="No Images", text_content="Body", attach_images=False
        )
        self._add_page(wiz, "scan1.jpg")
        action = wiz.action_create_article()
        article = self.DocPage.browse(action["res_id"])
        attachments = self.Attachment.search(
            [
                ("res_model", "=", "document.page"),
                ("res_id", "=", article.id),
            ]
        )
        self.assertFalse(attachments)

    # ------------------------------------------------------------------
    # Onchange / labels
    # ------------------------------------------------------------------
    def test_onchange_template_fills_empty_title(self):
        wiz = self.Wizard.new({"template": "meeting"})
        wiz._onchange_template()
        self.assertEqual(wiz.title, "รายงานการประชุม")

    def test_onchange_template_keeps_title(self):
        wiz = self.Wizard.new({"template": "meeting", "title": "Keep me"})
        wiz._onchange_template()
        self.assertEqual(wiz.title, "Keep me")

    def test_category_label(self):
        wiz = self._make_wizard(category="troubleshooting")
        self.assertIn("Troubleshooting", wiz._category_label())
