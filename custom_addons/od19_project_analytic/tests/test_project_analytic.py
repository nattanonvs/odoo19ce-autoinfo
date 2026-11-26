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

    def test_analytic_code_equals_job_no(self):
        # The auto-created analytic uses the job number as its code so it
        # shows up as the "[code]" prefix of the analytic display name.
        project = self.env["project.project"].create(
            {"name": "Airport Expansion", "job_no": "JOB-2026-042"}
        )
        self.assertEqual(project.account_id.code, "JOB-2026-042")

    def test_od19_project_ref_lists_project(self):
        project = self.env["project.project"].create(
            {"name": "Airport Expansion", "job_no": "JOB-2026-043"}
        )
        self.assertEqual(
            project.account_id.od19_project_ref,
            "JOB-2026-043 · Airport Expansion",
        )

    def test_action_create_analytic_links_missing_project(self):
        project = self.env["project.project"].create(
            {"name": "Airport Expansion", "job_no": "JOB-2026-044"}
        )
        project.account_id = False
        self.assertFalse(project.account_id)
        project.action_od19_create_analytic()
        self.assertTrue(project.account_id)
        self.assertEqual(project.account_id.code, "JOB-2026-044")

    def test_project_searchable_by_job_no(self):
        """Regression: the Sales search bar resolves a relational filter
        (the "Project" card) through name_search, which reads the project
        display name via _rec_names_search. The job number must be part of
        that so a job number typed into the search bar finds the linked
        order instead of returning an empty list.
        """
        project = self.env["project.project"].create(
            {"name": "Harbour Bridge", "job_no": "JOB-SEARCH-001"}
        )
        matches = self.env["project.project"].name_search("JOB-SEARCH-001")
        self.assertIn(project.id, [record_id for record_id, _label in matches])
        self.assertIn(
            project,
            self.env["project.project"].search(
                [("display_name", "ilike", "JOB-SEARCH-001")]
            ),
        )
