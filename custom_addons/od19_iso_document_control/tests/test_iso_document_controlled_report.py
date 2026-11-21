# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase, tagged

REPORT_XMLID = (
    "od19_iso_document_control.action_report_iso_controlled_document"
)
REPORT_NAME = "od19_iso_document_control.report_iso_controlled_document"


@tagged("post_install", "-at_install")
class TestControlledDocumentReport(TransactionCase):
    """WP3 acceptance criteria: cover / history / distribution / stamp."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Doc = cls.env["od19.iso.document"]
        cls.Dept = cls.env["hr.department"]
        cls.Report = cls.env["ir.actions.report"]
        cls.Revision = cls.env["od19.iso.document.revision"]
        cls.DistributionList = cls.env["od19.iso.distribution.list"]
        cls.DistributionLine = cls.env["od19.iso.distribution.line"]
        cls.PrintRequest = cls.env["od19.iso.print.request"]

        cls.cat_fm = cls.env.ref("od19_iso_document_control.iso_doc_cat_fm")
        cls.dept = cls.Dept.create({"name": "Purchasing", "code": "PU"})
        cls.user = cls.env.ref("base.user_admin")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_doc(self, **overrides):
        vals = {
            "document_title": "Controlled Document Test",
            "category_id": self.cat_fm.id,
            "department_id": self.dept.id,
        }
        vals.update(overrides)
        return self.Doc.create(vals)

    def _active_distribution(self, doc, line_vals_list):
        distribution = self.DistributionList.create({"document_id": doc.id})
        for vals in line_vals_list:
            self.DistributionLine.create(
                dict(vals, distribution_list_id=distribution.id)
            )
        distribution.action_activate()
        return distribution

    # ------------------------------------------------------------------
    # print_cover_page
    # ------------------------------------------------------------------
    def test_print_cover_page_default_true(self):
        doc = self._create_doc()
        self.assertTrue(doc.print_cover_page)

    # ------------------------------------------------------------------
    # Distribution list helper — must match the ACTIVE list
    # ------------------------------------------------------------------
    def test_distribution_lines_from_active_list(self):
        doc = self._create_doc()
        self._active_distribution(
            doc, [{"holder_name": "Somchai", "copies_required": 1}]
        )
        lines = doc._get_distribution_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.holder_name, "Somchai")

    def test_distribution_lines_empty_without_active_list(self):
        doc = self._create_doc()
        self.assertFalse(doc._get_distribution_lines())

    def test_distribution_lines_prefers_current_revision(self):
        doc = self._create_doc()
        old = self._active_distribution(doc, [{"holder_name": "Old Holder"}])
        self.assertEqual(old.revision, "00")

        doc.write({"revision": "01"})
        self._active_distribution(doc, [{"holder_name": "New Holder"}])

        lines = doc._get_distribution_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines.holder_name, "New Holder")

    # ------------------------------------------------------------------
    # Revision history helper
    # ------------------------------------------------------------------
    def test_revision_history_matches_records(self):
        doc = self._create_doc()
        self.Revision.create(
            {
                "document_id": doc.id,
                "revision": "00",
                "effective_date": "2026-01-01",
                "approved_by": self.user.id,
                "note": "Initial release",
            }
        )
        self.Revision.create(
            {
                "document_id": doc.id,
                "revision": "01",
                "effective_date": "2026-06-01",
                "approved_by": self.user.id,
                "note": "Second release",
            }
        )
        history = doc._get_revision_history()
        self.assertEqual(len(history), 2)
        # Newest revision first (order: effective_date desc).
        self.assertEqual(history[0].revision, "01")
        self.assertEqual(history[0].note, "Second release")

    # ------------------------------------------------------------------
    # Print copies helper (stamp source)
    # ------------------------------------------------------------------
    def test_print_copies_helper(self):
        doc = self._create_doc()
        request = self.PrintRequest.create(
            {
                "document_id": doc.id,
                "copies_count": 2,
                "copy_type": "controlled",
            }
        )
        request.action_submit()
        request.action_approve()

        copies = doc._get_print_copies()
        self.assertEqual(len(copies), 2)
        self.assertEqual(copies[0].name, "%s/P001" % doc.code)

    # ------------------------------------------------------------------
    # Report rendering — all four sections present
    # ------------------------------------------------------------------
    def test_report_renders_core_sections(self):
        doc = self._create_doc()
        self._active_distribution(doc, [{"holder_name": "Dist Holder"}])
        self.Revision.create(
            {
                "document_id": doc.id,
                "revision": "00",
                "effective_date": "2026-01-01",
                "approved_by": self.user.id,
                "note": "History Marker",
            }
        )

        html, report_type = self.Report._render_qweb_html(
            REPORT_XMLID, doc.ids
        )
        self.assertEqual(report_type, "html")
        if isinstance(html, bytes):
            html = html.decode()

        self.assertIn(doc.code, html)
        self.assertIn("History Marker", html)
        self.assertIn("Dist Holder", html)
        self.assertIn("CONTROLLED COPY", html)

    def test_action_print_controlled_document(self):
        doc = self._create_doc()
        # discard_logo_check skips the external-layout configurator that the
        # base implementation would otherwise return for admins.
        action = doc.with_context(
            discard_logo_check=True
        ).action_print_controlled_document()
        self.assertEqual(action.get("type"), "ir.actions.report")
        self.assertEqual(action.get("report_name"), REPORT_NAME)
