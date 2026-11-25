from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectTitleDisplay(TransactionCase):
    """The combined '(job_no) project name' title is shown on the kanban card and
    in the list. On the form, the heading is a Hero Panel wrapping an inline
    "job pill" (editable Job Number) next to the editable Project Name.
    """

    def _combined(self, xmlid):
        view = self.env.ref(xmlid)
        return etree.fromstring(view.get_combined_arch())

    def test_title_combines_job_no_and_name(self):
        project = self.env["project.project"].create({
            "name": "Tower A",
            "job_no": "JOB-2026-001",
        })
        self.assertEqual(project.od19_title, "(JOB-2026-001) Tower A")

    def test_title_without_job_no_is_just_the_name(self):
        project = self.env["project.project"].create({"name": "No Job Yet"})
        self.assertEqual(project.od19_title, "No Job Yet")

    def test_form_heading_uses_hero_panel_with_job_pill(self):
        form = self._combined("project.edit_project")
        self.assertTrue(
            form.xpath("//*[contains(@class,'od19-hero')]"),
            "The form heading must be wrapped in the Hero Panel container.",
        )
        self.assertTrue(
            form.xpath("//h1[contains(@class,'od19-inline-title')]//field[@name='job_no']"),
            "The Job Number must stay editable inside the inline job pill.",
        )
        self.assertTrue(
            form.xpath("//h1[contains(@class,'od19-inline-title')]//field[@name='name']"),
            "The Project Name must stay editable next to the job pill.",
        )
        self.assertTrue(
            form.xpath("//*[contains(@class,'od19-job-pill')]")
            and form.xpath("//*[contains(@class,'od19-pencil')]"),
            "The heading must render the job pill and the hover pencil affordance.",
        )

    def test_kanban_card_uses_combined_title(self):
        kanban = self._combined("project.view_project_kanban")
        self.assertTrue(
            kanban.xpath("//span[contains(@class,'fs-4')]//field[@name='od19_title']"),
            "The kanban card heading must display the combined title.",
        )
        self.assertTrue(
            kanban.xpath("//div[contains(@class,'od19-kanban-project-meta')]"),
            "The kanban card must repeat Job Number / Project Name below the title.",
        )

    def test_list_shows_combined_title(self):
        lst = self._combined("project.view_project")
        self.assertTrue(
            lst.xpath("//field[@name='od19_title']"),
            "The project list must show the combined '(job_no) name' column.",
        )
