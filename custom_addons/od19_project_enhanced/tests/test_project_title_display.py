from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectTitleDisplay(TransactionCase):
    """The project heading must render as '(job_no) project name'. The form title
    bar keeps the Job Number and Project Name as separate, editable fields; the
    list uses a single combined column; and the kanban card shows complementary
    context (project category / department) instead of repeating the title.
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

    def test_form_heading_uses_combined_title(self):
        form = self._combined("project.edit_project")
        self.assertTrue(
            form.xpath("//h1//field[@name='od19_title']"),
            "The form heading must display the combined '(job_no) name' title.",
        )
        self.assertFalse(
            form.xpath("//h1//field[@name='job_no']"),
            "The Job Number field must not sit in the heading anymore.",
        )
        self.assertTrue(
            form.xpath("//field[@name='job_no']") and form.xpath("//field[@name='name']"),
            "Job Number and Project Name must stay editable as separate fields.",
        )

    def test_kanban_card_uses_combined_title(self):
        kanban = self._combined("project.view_project_kanban")
        self.assertTrue(
            kanban.xpath("//span[contains(@class,'fs-4')]//field[@name='od19_title']"),
            "The kanban card heading must display the combined title.",
        )
        self.assertFalse(
            kanban.xpath("//div[contains(@class,'od19-kanban-project-meta')]"),
            "The kanban card must not repeat Job Number / Project Name below the title.",
        )
        self.assertTrue(
            kanban.xpath("//field[@name='od19_project_type_id']"),
            "The kanban card must show complementary context (project category).",
        )

    def test_list_shows_combined_title(self):
        lst = self._combined("project.view_project")
        self.assertTrue(
            lst.xpath("//field[@name='od19_title']"),
            "The project list must show the combined '(job_no) name' column.",
        )
        self.assertTrue(
            lst.xpath("//field[@name='name'][@optional='hide']"),
            "The core 'name' column must be hidden by default (shown via od19_title).",
        )
