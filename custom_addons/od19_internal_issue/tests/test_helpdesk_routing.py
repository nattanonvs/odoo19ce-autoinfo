from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueRouting(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Rule = cls.env["helpdesk.routing.rule"]

        cls.team_it = cls.Team.create(
            {"name": "IT Support (test)", "issue_stream": "it_support"}
        )
        cls.team_triage = cls.Team.create(
            {"name": "Triage (test)", "is_triage_team": True}
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
