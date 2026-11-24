from lxml import etree

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProjectKanbanNavigation(TransactionCase):
    """Clicking a project card must open the project form (summary/details)
    instead of jumping straight to the task list.

    Core wires the card click to the task list through the ``action`` attribute
    on ``project.view_project_kanban``. The module removes that attribute so the
    default behaviour (open the record) is restored.
    """

    def _kanban_node(self):
        view = self.env.ref("project.view_project_kanban")
        arch = etree.fromstring(view.get_combined_arch())
        kanban = arch if arch.tag == "kanban" else arch.find(".//kanban")
        self.assertIsNotNone(kanban, "Project kanban node not found")
        return kanban

    def test_project_kanban_card_opens_form(self):
        kanban = self._kanban_node()
        self.assertNotIn(
            "action",
            kanban.attrib,
            "The project kanban must not define an 'action' attribute; otherwise "
            "clicking a card opens the task list instead of the project form.",
        )

    def test_project_kanban_tasks_still_reachable_from_menu(self):
        # The task shortcut must remain available in the card's "..." menu.
        kanban = self._kanban_node()
        names = kanban.xpath(".//a[@name='action_view_tasks']/@name")
        self.assertTrue(
            names,
            "The 'Tasks' shortcut must stay reachable from the project card menu.",
        )
