# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIsoAuditProgram(TransactionCase):
    """Tests for the annual ISO audit programme."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Program = cls.env["od19.iso.audit.program"]

    def _create_program(self, **overrides):
        vals = {"name": "Annual Audit Programme", "year": 2026}
        vals.update(overrides)
        return self.Program.create(vals)

    def test_create_program_defaults(self):
        program = self._create_program()
        self.assertEqual(program.state, "draft")
        self.assertEqual(program.year, 2026)
        self.assertEqual(program.company_id, self.env.company)

    def test_year_constraint_too_low(self):
        with self.assertRaises(ValidationError):
            self._create_program(year=1999)

    def test_year_constraint_too_high(self):
        with self.assertRaises(ValidationError):
            self._create_program(year=2101)

    def test_program_state_transitions(self):
        program = self._create_program()
        program.action_approve()
        self.assertEqual(program.state, "approved")
        program.action_close()
        self.assertEqual(program.state, "closed")


class TestIsoAudit(TransactionCase):
    """Tests for internal audit records."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Audit = cls.env["od19.iso.audit"]
        cls.Finding = cls.env["od19.iso.audit.finding"]
        cls.dept = cls.env["hr.department"].create({"name": "Production"})

    def _create_audit(self, **overrides):
        vals = {
            "title": "Internal Audit Q1",
            "audit_type": "process",
            "date_planned": fields.Date.today(),
            "lead_auditor_id": self.env.user.id,
            "auditee_department_id": self.dept.id,
        }
        vals.update(overrides)
        return self.Audit.create(vals)

    def test_audit_name_auto_sequence(self):
        audit = self._create_audit()
        self.assertTrue(audit.name)
        self.assertNotEqual(audit.name, "/")

    def test_audit_default_state_draft(self):
        audit = self._create_audit()
        self.assertEqual(audit.state, "draft")

    def test_audit_state_flow(self):
        audit = self._create_audit()

        audit.action_plan()
        self.assertEqual(audit.state, "planned")

        audit.action_start()
        self.assertEqual(audit.state, "in_progress")
        self.assertTrue(audit.date_start)

        audit.action_report()
        self.assertEqual(audit.state, "report")
        self.assertTrue(audit.report_date)

        audit.action_follow_up()
        self.assertEqual(audit.state, "follow_up")
        self.assertTrue(audit.follow_up_date)

        audit.action_close()
        self.assertEqual(audit.state, "closed")
        self.assertTrue(audit.close_date)

        audit.action_reset_to_draft()
        self.assertEqual(audit.state, "draft")

        audit.action_cancel()
        self.assertEqual(audit.state, "cancel")

    def test_audit_date_constraint(self):
        with self.assertRaises(ValidationError):
            self._create_audit(
                date_start="2026-02-01",
                date_end="2026-01-01",
            )

    def test_audit_program_link(self):
        program = self.env["od19.iso.audit.program"].create(
            {"name": "Programme", "year": 2026}
        )
        audit = self._create_audit(program_id=program.id)
        self.assertEqual(audit.program_id, program)
        self.assertIn(audit, program.audit_ids)

    def _audit_activities(self, audit):
        return self.env["mail.activity"].search([
            ("res_model", "=", "od19.iso.audit"),
            ("res_id", "=", audit.id),
        ])

    def test_cron_planned_reminder_creates_activity(self):
        audit = self._create_audit(
            date_planned=fields.Date.add(fields.Date.today(), days=3)
        )
        self.env["od19.iso.audit"]._cron_audit_planned_reminder()
        self.assertTrue(self._audit_activities(audit))

    def test_cron_planned_reminder_is_idempotent(self):
        audit = self._create_audit(
            date_planned=fields.Date.add(fields.Date.today(), days=3)
        )
        Audit = self.env["od19.iso.audit"]
        Audit._cron_audit_planned_reminder()
        count = len(self._audit_activities(audit))
        Audit._cron_audit_planned_reminder()
        self.assertEqual(len(self._audit_activities(audit)), count)

    def test_cron_planned_reminder_ignores_started_audit(self):
        audit = self._create_audit(
            date_planned=fields.Date.add(fields.Date.today(), days=3)
        )
        audit.action_start()
        self.env["od19.iso.audit"]._cron_audit_planned_reminder()
        self.assertFalse(self._audit_activities(audit))


class TestIsoAuditFinding(TransactionCase):
    """Tests for audit findings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Audit = cls.env["od19.iso.audit"]
        cls.Finding = cls.env["od19.iso.audit.finding"]
        cls.dept = cls.env["hr.department"].create({"name": "Quality"})
        cls.audit = cls.Audit.create(
            {
                "title": "Audit for findings",
                "audit_type": "system",
                "date_planned": fields.Date.today(),
                "lead_auditor_id": cls.env.user.id,
                "auditee_department_id": cls.dept.id,
            }
        )

    def _create_finding(self, **overrides):
        vals = {
            "name": "Major finding",
            "audit_id": self.audit.id,
            "severity": "major",
        }
        vals.update(overrides)
        return self.Finding.create(vals)

    def test_finding_defaults(self):
        finding = self._create_finding()
        self.assertEqual(finding.status, "open")

    def test_finding_status_flow(self):
        finding = self._create_finding()

        finding.action_in_progress()
        self.assertEqual(finding.status, "in_progress")

        finding.action_verify()
        self.assertEqual(finding.status, "verified")
        self.assertTrue(finding.verification_date)

        finding.action_close()
        self.assertEqual(finding.status, "closed")
        self.assertTrue(finding.close_date)

        finding.action_open()
        self.assertEqual(finding.status, "open")

    def test_finding_linked_to_audit(self):
        finding = self._create_finding()
        self.assertIn(finding, self.audit.finding_ids)

    def _finding_activities(self, finding):
        return self.env["mail.activity"].search([
            ("res_model", "=", "od19.iso.audit.finding"),
            ("res_id", "=", finding.id),
        ])

    def test_cron_finding_due_reminder_creates_activity(self):
        finding = self._create_finding(
            due_date=fields.Date.add(fields.Date.today(), days=3)
        )
        self.env["od19.iso.audit.finding"]._cron_finding_due_reminder()
        self.assertTrue(self._finding_activities(finding))

    def test_cron_finding_overdue_reminder_creates_activity(self):
        finding = self._create_finding(
            due_date=fields.Date.add(fields.Date.today(), days=-2)
        )
        self.env["od19.iso.audit.finding"]._cron_finding_due_reminder()
        self.assertTrue(self._finding_activities(finding))

    def test_cron_finding_reminder_is_idempotent(self):
        finding = self._create_finding(
            due_date=fields.Date.add(fields.Date.today(), days=3)
        )
        Finding = self.env["od19.iso.audit.finding"]
        Finding._cron_finding_due_reminder()
        count = len(self._finding_activities(finding))
        Finding._cron_finding_due_reminder()
        self.assertEqual(len(self._finding_activities(finding)), count)

    def test_cron_finding_reminder_ignores_closed(self):
        finding = self._create_finding(
            due_date=fields.Date.add(fields.Date.today(), days=3)
        )
        finding.action_close()
        self.env["od19.iso.audit.finding"]._cron_finding_due_reminder()
        self.assertFalse(self._finding_activities(finding))
