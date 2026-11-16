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

    def test_queue_position_orders_by_priority_then_sequence(self):
        team = self.env["helpdesk.ticket.team"].create({"name": "Queue Test Team"})
        t_crit = self._create_ticket(team_id=team.id, impact="I3", urgency="U3")  # P3
        t_low_a = self._create_ticket(team_id=team.id, impact="I1", urgency="U1")  # P0, seq 10
        t_low_b = self._create_ticket(
            team_id=team.id, impact="I1", urgency="U1", queue_sequence=5
        )  # P0, seq 5

        self.assertEqual(t_crit.queue_position, 1)
        self.assertEqual(t_crit.queue_ahead_count, 0)
        self.assertEqual(t_low_b.queue_position, 2)
        self.assertEqual(t_low_b.queue_ahead_count, 1)
        self.assertEqual(t_low_a.queue_position, 3)
        self.assertEqual(t_low_a.queue_ahead_count, 2)

    def test_queue_position_excludes_closed_stage(self):
        team = self.env["helpdesk.ticket.team"].create({"name": "Queue Close Team"})
        closed_stage = self.env["helpdesk.ticket.stage"].create(
            {"name": "Closed", "closed": True}
        )
        t_open = self._create_ticket(team_id=team.id)
        t_closed = self._create_ticket(team_id=team.id, stage_id=closed_stage.id)

        self.assertEqual(t_open.queue_position, 1)
        self.assertEqual(t_closed.queue_position, 0)

    def test_queue_position_zero_without_team(self):
        # ต้องส่ง user_id=False เพื่อกัน OCA _compute_team_id auto-assign ทีม
        # จาก user_id.helpdesk_team_ids
        # seed data จะ route 'unsure' ไปทีม Triage — เคลียร์ team_id ออกเพื่อทดสอบ
        # สาขา "ไม่มีทีม" ของ _compute_queue_position
        ticket = self._create_ticket(user_id=False)
        ticket.team_id = False
        self.assertFalse(ticket.team_id)
        self.assertEqual(ticket.queue_position, 0)
        self.assertEqual(ticket.queue_ahead_count, 0)
