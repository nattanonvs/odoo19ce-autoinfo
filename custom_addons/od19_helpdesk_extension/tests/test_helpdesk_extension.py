# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestHelpdeskExtension(TransactionCase):
    """Tests for the Internal vs Customer Sales Services helpdesk split."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.partner = cls.env["res.partner"].create({"name": "Service Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Service Product",
                "sale_ok": True,
                "type": "service",
            }
        )

    def _create_team(self, **overrides):
        vals = {"name": "Test Team"}
        vals.update(overrides)
        return self.Team.create(vals)

    def _create_ticket(self, **overrides):
        vals = {
            "name": "Test Ticket",
            "description": "<p>Reported problem</p>",
            "partner_id": self.partner.id,
        }
        vals.update(overrides)
        return self.Ticket.create(vals)

    # ------------------------------------------------------------------
    # Team type
    # ------------------------------------------------------------------
    def test_team_type_default_is_internal(self):
        team = self._create_team()
        self.assertEqual(team.team_type, "internal")

    def test_team_type_customer_service(self):
        team = self._create_team(team_type="customer_service")
        self.assertEqual(team.team_type, "customer_service")

    # ------------------------------------------------------------------
    # Ticket related / computed fields
    # ------------------------------------------------------------------
    def test_ticket_team_type_is_related(self):
        team = self._create_team(team_type="customer_service")
        ticket = self._create_ticket(team_id=team.id)
        self.assertEqual(ticket.team_type, "customer_service")

    def test_is_customer_service_true_for_service_team(self):
        team = self._create_team(team_type="customer_service")
        ticket = self._create_ticket(team_id=team.id)
        self.assertTrue(ticket.is_customer_service)

    def test_is_customer_service_false_for_internal_team(self):
        team = self._create_team(team_type="internal")
        ticket = self._create_ticket(team_id=team.id)
        self.assertFalse(ticket.is_customer_service)

    # ------------------------------------------------------------------
    # Sales service fields
    # ------------------------------------------------------------------
    def test_service_fields_can_be_set(self):
        team = self._create_team(team_type="customer_service")
        ticket = self._create_ticket(
            team_id=team.id,
            service_type="repair",
            product_id=self.product.id,
            total_cost=1500.0,
        )
        self.assertEqual(ticket.service_type, "repair")
        self.assertEqual(ticket.product_id, self.product)
        self.assertEqual(ticket.total_cost, 1500.0)

    def test_currency_follows_company(self):
        ticket = self._create_ticket()
        self.assertEqual(ticket.currency_id, ticket.company_id.currency_id)

    # ------------------------------------------------------------------
    # action_create_invoice
    # ------------------------------------------------------------------
    def test_action_create_invoice(self):
        team = self._create_team(team_type="customer_service")
        ticket = self._create_ticket(
            team_id=team.id,
            service_type="repair",
            product_id=self.product.id,
            total_cost=2000.0,
        )
        action = ticket.action_create_invoice()
        self.assertEqual(action["res_model"], "account.move")
        self.assertTrue(ticket.invoice_id)
        self.assertEqual(ticket.invoice_id.move_type, "out_invoice")
        self.assertEqual(ticket.invoice_id.partner_id, self.partner)
        self.assertEqual(len(ticket.invoice_id.invoice_line_ids), 1)
        self.assertEqual(
            ticket.invoice_id.invoice_line_ids.price_unit,
            2000.0,
        )

    def test_action_create_invoice_without_partner_is_noop(self):
        team = self._create_team(team_type="customer_service")
        ticket = self._create_ticket(team_id=team.id)
        ticket.partner_id = False
        result = ticket.action_create_invoice()
        self.assertIsNone(result)
        self.assertFalse(ticket.invoice_id)
