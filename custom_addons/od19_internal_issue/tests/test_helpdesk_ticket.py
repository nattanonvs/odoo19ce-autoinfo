from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInternalIssueTicket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]

    def _create_ticket(self, **overrides):
        vals = {"name": "Test Issue", "description": "<p>desc</p>"}
        vals.update(overrides)
        return self.Ticket.create(vals)

    def test_defaults(self):
        ticket = self._create_ticket()
        self.assertEqual(ticket.visibility, "public")
        self.assertEqual(ticket.reported_by_id, self.env.user)
        self.assertFalse(ticket.emergency)
        self.assertEqual(ticket.consent_state, "accepted")
        self.assertEqual(ticket.issue_stream, "unsure")

    def test_priority_matrix_low(self):
        ticket = self._create_ticket(impact="I1", urgency="U1")
        self.assertEqual(ticket.priority, "0")  # score 2 -> P0

    def test_priority_matrix_medium(self):
        ticket = self._create_ticket(impact="I2", urgency="U1")
        self.assertEqual(ticket.priority, "1")  # score 3 -> P1

    def test_priority_matrix_high(self):
        ticket = self._create_ticket(impact="I3", urgency="U2")
        self.assertEqual(ticket.priority, "2")  # score 5 -> P2

    def test_priority_matrix_critical(self):
        ticket = self._create_ticket(impact="I3", urgency="U3")
        self.assertEqual(ticket.priority, "3")  # score 6 -> P3

    def test_priority_recomputed_on_change(self):
        ticket = self._create_ticket(impact="I1", urgency="U1")
        self.assertEqual(ticket.priority, "0")
        ticket.impact = "I3"
        ticket.urgency = "U3"
        self.assertEqual(ticket.priority, "3")

    def test_jump_window_deadline_set_on_create(self):
        ticket = self._create_ticket()
        self.assertTrue(ticket.jump_window_deadline)
