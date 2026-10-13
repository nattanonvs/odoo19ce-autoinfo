from odoo.tests.common import TransactionCase, tagged


@tagged("standard", "at_install")
class TestKnowledgeArticle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Page = cls.env["document.page"]
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Category = cls.env["helpdesk.ticket.category"]

        cls.helpdesk_category = cls.Category.create(
            {"name": "Test Helpdesk", "active": True}
        )

        # document.page requires a category (parent_id of type category)
        cls.knowledge_category = cls.Page.create(
            {
                "name": "Knowledge Category",
                "type": "category",
            }
        )

    def _create_article(self, **overrides):
        vals = {
            "name": "Test Article",
            "parent_id": self.knowledge_category.id,
            "content": "<p>Test body content</p>",
            "draft_name": "1.0",
            "draft_summary": "Init",
        }
        vals.update(overrides)
        return self.Page.create(vals)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    def test_default_category(self):
        article = self._create_article()
        self.assertEqual(article.category, "general")

    def test_default_is_emergency_false(self):
        article = self._create_article()
        self.assertFalse(article.is_emergency)

    # ------------------------------------------------------------------
    # Content plain text
    # ------------------------------------------------------------------
    def test_content_plain_computed(self):
        article = self._create_article(
            content="<h1>Title</h1><p>Body text</p>"
        )
        self.assertIn("Body text", article.content_plain)
        self.assertNotIn("<p>", article.content_plain)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def test_search_emergency(self):
        article = self._create_article(
            name="Printer not working", is_emergency=True
        )
        results = self.Page.search_emergency("Printer")
        self.assertIn(article, results)

    def test_search_emergency_excludes_non_emergency(self):
        self._create_article(name="Normal article", is_emergency=False)
        results = self.Page.search_emergency("Normal")
        self.assertEqual(len(results), 0)

    # ------------------------------------------------------------------
    # Create from ticket
    # ------------------------------------------------------------------
    def test_create_from_ticket(self):
        ticket = self.Ticket.create(
            {
                "name": "Network down",
                "description": "<p>Cannot connect</p>",
                "category_id": self.helpdesk_category.id,
                "resolution": "<p>Restart router</p>",
            }
        )
        article = self.Page.create(
            {
                "name": ticket.name,
                "parent_id": self.knowledge_category.id,
                "content": ticket.resolution or ticket.description or "",
                "category": "troubleshooting",
                "ticket_id": ticket.id,
                "draft_name": "1.0",
                "draft_summary": "Created from ticket",
            }
        )
        self.assertEqual(article.name, "Network down")
        self.assertEqual(article.category, "troubleshooting")
        self.assertEqual(article.ticket_id, ticket)
