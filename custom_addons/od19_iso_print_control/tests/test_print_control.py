from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIsoPrintControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.category = cls.env["od19.iso.document.category"].search([], limit=1)
        cls.users = cls.env["res.users"].create([
            {"name": "Print User A", "login": "print_user_a"},
            {"name": "Print User B", "login": "print_user_b"},
        ])

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _doc(self, revision="00", status="approved"):
        return self.env["od19.iso.document"].create({
            "document_title": "ทดสอบเอกสารพิมพ์",
            "category_id": self.category.id,
            "revision": revision,
            "status": status,
        })

    def _request(self, doc, copies=2, **kw):
        vals = {
            "document_id": doc.id,
            "copies_count": copies,
            "request_type": "new_print",
            "requester_id": self.users[0].id,
        }
        vals.update(kw)
        return self.env["od19.iso.print.request"].create(vals)

    def _approved_copies(self, doc, copies=2):
        request = self._request(doc, copies=copies)
        request.action_submit()
        request.action_approve()
        return request, request.copy_ids

    # ------------------------------------------------------------------
    # numbering
    # ------------------------------------------------------------------
    def test_request_number_format(self):
        doc = self._doc()
        request = self._request(doc)
        year2 = fields.Date.today().strftime("%y")
        self.assertTrue(request.name.startswith("PRN%s-" % year2))
        self.assertEqual(len(request.name), len("PRN%s-" % year2) + 3)

    def test_request_sequence_increments(self):
        doc = self._doc()
        a = self._request(doc)
        b = self._request(doc)
        self.assertNotEqual(a.name, b.name)
        self.assertEqual(int(b.name[-3:]), int(a.name[-3:]) + 1)

    def test_distribution_number_format(self):
        doc = self._doc()
        dist = self.env["od19.iso.distribution.list"].create({
            "document_id": doc.id,
        })
        year2 = fields.Date.today().strftime("%y")
        self.assertTrue(dist.name.startswith("DL%s-" % year2))

    def test_copy_name_format(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=2)
        self.assertEqual(copies[0].name, "%s/P001" % doc.code)
        self.assertEqual(copies[1].name, "%s/P002" % doc.code)

    # ------------------------------------------------------------------
    # approve -> generate copies
    # ------------------------------------------------------------------
    def test_approve_generates_copies(self):
        doc = self._doc()
        request, copies = self._approved_copies(doc, copies=3)
        self.assertEqual(len(copies), 3)
        self.assertEqual(request.state, "approved")
        self.assertEqual(set(copies.mapped("state")), {"reserved"})
        self.assertEqual(sorted(copies.mapped("copy_number")), [1, 2, 3])
        self.assertEqual(len(set(copies.mapped("copy_number"))), 3)

    def test_approve_idempotent(self):
        doc = self._doc()
        request, copies = self._approved_copies(doc, copies=2)
        request._apply_approval_effect()
        self.assertEqual(request.copy_count, 2)

    def test_approve_requires_review_state(self):
        doc = self._doc()
        request = self._request(doc)
        with self.assertRaises(UserError):
            request.action_approve()

    # ------------------------------------------------------------------
    # issue / return lifecycle
    # ------------------------------------------------------------------
    def test_issue_return_flow(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=2)
        copies.action_issue()
        self.assertEqual(set(copies.mapped("state")), {"issued"})
        self.assertTrue(all(c.issue_date for c in copies))
        copies.action_return()
        self.assertEqual(set(copies.mapped("state")), {"returned"})
        self.assertTrue(all(c.return_date for c in copies))

    def test_return_requires_issued(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=1)
        with self.assertRaises(UserError):
            copies.action_return()

    def test_destroy_and_lost(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=2)
        copies.action_destroy()
        self.assertEqual(set(copies.mapped("state")), {"destroyed"})
        _request2, copies2 = self._approved_copies(doc, copies=1)
        copies2.action_mark_lost()
        self.assertEqual(copies2.state, "lost")

    # ------------------------------------------------------------------
    # G1: revision-driven replacement
    # ------------------------------------------------------------------
    def test_revision_change_replaces_copies(self):
        doc = self._doc(revision="00")
        _request, copies = self._approved_copies(doc, copies=2)
        copies.action_issue()
        self.assertEqual(len(copies), 2)

        doc.write({"revision": "01"})
        self.assertEqual(set(copies.mapped("state")), {"replaced"})
        replace_requests = self.env["od19.iso.print.request"].search([
            ("document_id", "=", doc.id),
            ("request_type", "=", "replace_revision"),
        ])
        self.assertEqual(len(replace_requests), 1)
        self.assertEqual(replace_requests.copies_count, 2)
        self.assertEqual(replace_requests.revision, "01")

    def test_revision_change_without_issued_copies(self):
        doc = self._doc(revision="00")
        self.env["od19.iso.print.copy"]._on_document_revision_change(doc, "01")
        self.assertFalse(self.env["od19.iso.print.request"].search([
            ("document_id", "=", doc.id),
            ("request_type", "=", "replace_revision"),
        ]))

    # ------------------------------------------------------------------
    # Distribution list
    # ------------------------------------------------------------------
    def test_distribution_activate_supersedes(self):
        doc = self._doc()
        first = self.env["od19.iso.distribution.list"].create({
            "document_id": doc.id,
            "line_ids": [(0, 0, {"recipient_id": self.users[0].id, "copies_required": 1})],
        })
        first.action_activate()
        self.assertEqual(first.state, "active")
        second = self.env["od19.iso.distribution.list"].create({
            "document_id": doc.id,
            "line_ids": [(0, 0, {"recipient_id": self.users[1].id, "copies_required": 1})],
        })
        second.action_activate()
        self.assertEqual(second.state, "active")
        self.assertEqual(first.state, "superseded")

    def test_distribution_activate_requires_lines(self):
        doc = self._doc()
        dist = self.env["od19.iso.distribution.list"].create({
            "document_id": doc.id,
        })
        with self.assertRaises(UserError):
            dist.action_activate()

    # ------------------------------------------------------------------
    # document inherit counts
    # ------------------------------------------------------------------
    def test_document_counts(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=2)
        copies.action_issue()
        self.assertEqual(doc.print_request_count, 1)
        self.assertEqual(doc.print_copy_count, 2)
        self.assertEqual(doc.issued_copy_count, 2)
        self.assertIn("print_copy_ids", doc._fields)
        self.assertIn("distribution_list_ids", doc._fields)

    # ------------------------------------------------------------------
    # cron overdue
    # ------------------------------------------------------------------
    def test_cron_overdue_creates_activity(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=1)
        copies.action_issue()
        copies.write({
            "holder_id": self.users[0].id,
            "return_due_date": fields.Date.subtract(fields.Date.today(), days=5),
        })
        self.env["od19.iso.print.copy"]._cron_copy_return_overdue()
        copies.invalidate_recordset()
        self.assertTrue(copies.activity_ids)

    # ------------------------------------------------------------------
    # security / reports
    # ------------------------------------------------------------------
    def test_security_groups_exist(self):
        for xmlid in (
            "od19_iso_print_control.group_iso_print_user",
            "od19_iso_print_control.group_iso_print_controller",
            "od19_iso_print_control.group_iso_print_manager",
        ):
            self.assertTrue(self.env.ref(xmlid))

    def test_department_rule_exists(self):
        rule = self.env.ref(
            "od19_iso_print_control.rule_od19_iso_print_copy_department"
        )
        self.assertIn("department_id", rule.domain_force)

    def test_print_register_report_renders(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=1)
        html, _mimetype = self.env["ir.actions.report"]._render_qweb_html(
            "od19_iso_print_control.action_report_od19_iso_print_register",
            copies.ids,
        )
        self.assertIn(copies[0].name, html.decode("utf-8"))

    def test_copy_label_report_renders(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=1)
        html, _mimetype = self.env["ir.actions.report"]._render_qweb_html(
            "od19_iso_print_control.action_report_od19_iso_copy_label",
            copies.ids,
        )
        self.assertIn("CONTROLLED COPY", html.decode("utf-8"))

    def test_distribution_report_renders(self):
        doc = self._doc()
        dist = self.env["od19.iso.distribution.list"].create({
            "document_id": doc.id,
            "line_ids": [(0, 0, {"recipient_id": self.users[0].id, "copies_required": 1})],
        })
        html, _mimetype = self.env["ir.actions.report"]._render_qweb_html(
            "od19_iso_print_control.action_report_od19_iso_distribution",
            dist.ids,
        )
        self.assertIn(dist.name, html.decode("utf-8"))

    # ------------------------------------------------------------------
    # wizard
    # ------------------------------------------------------------------
    def test_wizard_issue(self):
        doc = self._doc()
        _request, copies = self._approved_copies(doc, copies=1)
        wizard = self.env["od19.iso.print.issue.wizard"].with_context(
            active_ids=copies.ids
        ).create({
            "action_type": "issue",
            "copy_ids": [(6, 0, copies.ids)],
            "holder_id": self.users[0].id,
            "return_due_date": fields.Date.add(fields.Date.today(), days=30),
        })
        wizard.action_apply()
        self.assertEqual(copies.state, "issued")
        self.assertEqual(copies.holder_id, self.users[0])
        self.assertTrue(copies.return_due_date)
