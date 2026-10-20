from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectAnalytic(TransactionCase):
    def setUp(self):
        super().setUp()
        self.owner = self.env["res.partner"].create(
            {
                "name": "Project Owner",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        self.contractor = self.env["res.partner"].create(
            {
                "name": "Main Contractor",
                "is_company": True,
                "od19_is_contractor": True,
            }
        )
        self.invalid_owner = self.env["res.partner"].create(
            {"name": "Invalid Owner", "is_company": True}
        )
        self.invalid_contractor = self.env["res.partner"].create(
            {"name": "Invalid Contractor", "is_company": True}
        )

    def test_project_creates_analytic_account(self):
        project = self.env["project.project"].create(
            {
                "name": "Airport Expansion",
                "job_no": "JOB-2026-001",
            }
        )
        self.assertTrue(
            project.account_id,
            "An analytic account should be auto-created on project creation.",
        )

    def test_job_no_optional_for_core_compatibility(self):
        # job_no is required at the UI level (view) but optional at the model
        # level so core modules (e.g. sale_project) can create projects.
        project = self.env["project.project"].create(
            {
                "name": "Core Module Project",
            }
        )
        self.assertFalse(project.job_no)

    def test_job_no_must_be_unique(self):
        self.env["project.project"].create(
            {
                "name": "First Project",
                "job_no": "JOB-DUP-001",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["project.project"].create(
                {
                    "name": "Second Project",
                    "job_no": "JOB-DUP-001",
                }
            )

    def test_project_owner_must_have_owner_role(self):
        with self.assertRaises(ValidationError):
            self.env["project.project"].create(
                {
                    "name": "Invalid Owner Project",
                    "job_no": "JOB-OWNER-001",
                    "project_owner_id": self.invalid_owner.id,
                }
            )

    def test_contractor_must_have_contractor_role(self):
        with self.assertRaises(ValidationError):
            self.env["project.project"].create(
                {
                    "name": "Invalid Contractor Project",
                    "job_no": "JOB-CONTRACTOR-001",
                    "contractor_ids": [(6, 0, self.invalid_contractor.ids)],
                }
            )

    def test_valid_project_fields(self):
        department = self.env["hr.department"].create({"name": "Engineering"})
        project = self.env["project.project"].create(
            {
                "name": "Valid Project",
                "job_no": "JOB-VALID-001",
                "od19_department_id": department.id,
                "project_owner_id": self.owner.id,
                "contractor_ids": [(6, 0, self.contractor.ids)],
            }
        )
        self.assertEqual(project.job_no, "JOB-VALID-001")
        self.assertEqual(project.od19_department_id, department)
        self.assertEqual(project.project_owner_id, self.owner)
        self.assertIn(self.contractor, project.contractor_ids)
        self.assertTrue(project.account_id)
