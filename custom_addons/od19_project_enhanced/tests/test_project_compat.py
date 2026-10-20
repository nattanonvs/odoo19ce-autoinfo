from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectCompat(TransactionCase):
    """Compatibility guardrails (spec 11.4): core/other modules keep working."""

    def test_sale_project_can_be_created_without_job_no_by_sale_project(self):
        # A project created by core sale_project has no job number and no
        # department; the Job Number must stay optional at the model level.
        project = self.env["project.project"].create({"name": "Sale Made Project"})
        self.assertTrue(project)
        self.assertFalse(project.job_no)

    def test_sales_project_context_owner_guard_still_raises(self):
        owner = self.env["res.partner"].create(
            {"name": "Compat Owner", "is_company": True, "od19_is_project_owner": True}
        )
        other_owner = self.env["res.partner"].create(
            {"name": "Compat Other Owner", "is_company": True}
        )
        customer = self.env["res.partner"].create(
            {"name": "Compat Customer", "is_company": True}
        )
        project = self.env["project.project"].create(
            {"name": "Compat Project", "project_owner_id": owner.id}
        )
        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": other_owner.id,
                }
            )
