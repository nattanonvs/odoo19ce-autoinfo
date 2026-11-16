from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueRouting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Rule = cls.env["helpdesk.routing.rule"]

        # seed data มีทีมที่ใช้ stream เดียวกัน (it_support/improvement) อยู่แล้ว
        # ทีมของเทสต์จึงต้องมี sequence ต่ำกว่าเพื่อให้ชนะ search(..., limit=1)
        cls.team_it = cls.Team.create(
            {
                "name": "IT Support (test)",
                "issue_stream": "it_support",
                "sequence": 1,
            }
        )
        cls.team_triage = cls.Team.create(
            {"name": "Triage (test)", "is_triage_team": True, "sequence": 2}
        )

    def test_route_by_issue_stream(self):
        ticket = self.Ticket.create(
            {
                "name": "Printer down",
                "description": "<p>test</p>",
                "issue_stream": "it_support",
            }
        )
        self.assertEqual(ticket.team_id, self.team_it)

    def test_route_unsure_to_triage(self):
        ticket = self.Ticket.create(
            {
                "name": "ไม่รู้ว่าใครดูแล",
                "description": "<p>test</p>",
                "issue_stream": "unsure",
            }
        )
        self.assertEqual(ticket.team_id, self.team_triage)

    def test_explicit_team_id_is_respected(self):
        ticket = self.Ticket.create(
            {
                "name": "Explicit",
                "description": "<p>test</p>",
                "issue_stream": "it_support",
                "team_id": self.team_triage.id,
            }
        )
        self.assertEqual(ticket.team_id, self.team_triage)

    def test_routing_rule_keyword_fills_team(self):
        self.Rule.create(
            {
                "name": "Printer keyword",
                "keyword": "printer",
                "issue_stream": "unsure",
                "team_id": self.team_it.id,
                "sequence": 1,
            }
        )
        ticket = self.Ticket.create(
            {
                "name": "my printer is broken",
                "description": "<p>test</p>",
                "issue_stream": "unsure",
            }
        )
        self.assertEqual(ticket.team_id, self.team_it)

    def test_routing_rule_scoped_by_issue_stream(self):
        team_improve = self.Team.create(
            {"name": "Improve (test)", "issue_stream": "improvement", "sequence": 3}
        )
        self.Rule.create(
            {
                "name": "Alpha (IT only)",
                "keyword": "alpha",
                "issue_stream": "it_support",
                "team_id": self.team_triage.id,
                "sequence": 1,
            }
        )
        # stream ตรงกับกฎ -> กฎชนะ (override ทีมจาก stream)
        t_same = self.Ticket.create(
            {
                "name": "alpha issue",
                "description": "<p>x</p>",
                "issue_stream": "it_support",
            }
        )
        self.assertEqual(t_same.team_id, self.team_triage)
        # stream ไม่ตรงกับกฎ -> กฎต้องไม่ถูกใช้ -> fallback ไปทีมของ stream
        t_other = self.Ticket.create(
            {
                "name": "alpha issue",
                "description": "<p>x</p>",
                "issue_stream": "improvement",
            }
        )
        self.assertEqual(t_other.team_id, team_improve)

    def test_routing_rule_fills_category(self):
        category = self.env["helpdesk.ticket.category"].create(
            {"name": "Network (test)"}
        )
        self.Rule.create(
            {
                "name": "Net rule",
                "keyword": "network",
                "team_id": self.team_it.id,
                "category_id": category.id,
                "sequence": 1,
            }
        )
        ticket = self.Ticket.create(
            {
                "name": "network outage",
                "description": "<p>x</p>",
                "issue_stream": "unsure",
            }
        )
        self.assertEqual(ticket.category_id, category)
