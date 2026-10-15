from odoo.tests.common import TransactionCase

from odoo.addons.od19_project_document_sequence.models.project_project import (
    _insert_initials_before_year,
)


class TestProjectDocumentSequence(TransactionCase):
    """Basic tests for project document sequence generation."""

    def test_insert_initials_before_year(self):
        # Sequence: JB26-0001, initials: NV -> JBNV26-0001
        result = _insert_initials_before_year("JB26-0001", "NV")
        self.assertEqual(result, "JBNV26-0001")

    def test_insert_initials_no_year_match(self):
        # No 2-digit year found -> return unchanged
        result = _insert_initials_before_year("JOB-0001", "NV")
        self.assertEqual(result, "JOB-0001")

    def test_insert_initials_empty_generated(self):
        result = _insert_initials_before_year("", "NV")
        self.assertEqual(result, "")

    def test_insert_initials_none_generated(self):
        result = _insert_initials_before_year(None, "NV")
        self.assertIsNone(result)

    def test_insert_initials_empty_initials(self):
        result = _insert_initials_before_year("JB26-0001", "")
        self.assertEqual(result, "JB26-0001")

    def test_user_has_initials_field(self):
        user = self.env["res.users"].create({
            "name": "Test User",
            "login": "test_initials_user",
            "od19_initials": "TV",
        })
        self.assertEqual(user.od19_initials, "TV")

    def test_department_has_project_sequence_fields(self):
        department = self.env["hr.department"].create({"name": "Test Dept"})
        self.assertFalse(department.project_job_sequence_id)
        self.assertFalse(department.project_server_sequence_id)
        self.assertFalse(department.project_pm_sequence_id)
        self.assertFalse(department.project_service_sequence_id)

    def test_project_has_type_and_department_fields(self):
        department = self.env["hr.department"].create({"name": "Test Project Dept"})
        project = self.env["project.project"].create({
            "name": "Test Project",
            "od19_department_id": department.id,
        })
        self.assertEqual(project.od19_project_type, "job")
        self.assertEqual(project.od19_department_id, department)
