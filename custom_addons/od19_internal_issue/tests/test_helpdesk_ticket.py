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

    def test_emergency_creates_notification(self):
        # NOTE (T11): ใช้ base.user_admin แทน self.env.user เพราะ self.env.user
        # (superuser) มี partner เป็น inactive -> notify() จะกรองทิ้ง; admin มี
        # partner active และเป็นสมาชิกทีม Triage ที่ ticket ถูก route ไป
        admin = self.env.ref("base.user_admin")
        ticket = self._create_ticket(emergency=True, user_id=admin.id)
        queue = self.env["od19.notification.queue"].search(
            [("event", "=", "issue_updated")]
        )
        self.assertTrue(queue)

    def test_assign_notifies_assignee(self):
        # NOTE (T11): ใช้ base.user_admin (partner active) แทน self.env.user
        admin = self.env.ref("base.user_admin")
        ticket = self._create_ticket()
        ticket.write({"user_id": admin.id})
        queue = self.env["od19.notification.queue"].search(
            [("event", "=", "issue_assigned")]
        )
        self.assertTrue(queue)

    # ------------------------------------------------------------------
    # Phase 2 follow-ups: emergency fan-out (M2) / stage notify (M3) / minors
    # ------------------------------------------------------------------
    def _active_user(self, name, login):
        return self.env["res.users"].create({"name": name, "login": login})

    def test_emergency_notifies_team_leader(self):
        # M2: เรื่องฉุกเฉินต้อง fan-out ไปหัวหน้าทีมเจ้าของเรื่อง
        # (หัวหน้าทีมไม่ใช่ผู้แจ้ง/ผู้รับผิดชอบ จึงไม่ถูกแจ้งในเส้นทางปกติ)
        reporter = self._active_user("Esc Reporter", "esc_reporter_test")
        leader = self._active_user("Esc Leader", "esc_leader_test")
        team = self.env["helpdesk.ticket.team"].create(
            {"name": "Esc Team", "user_id": leader.id}
        )
        self._create_ticket(
            team_id=team.id, emergency=True, reported_by_id=reporter.id
        )
        queue = self.env["od19.notification.queue"].search(
            [
                ("event", "=", "issue_updated"),
                ("partner_id", "=", leader.partner_id.id),
            ]
        )
        self.assertTrue(queue, "เรื่องฉุกเฉินต้องแจ้งหัวหน้าทีมเจ้าของเรื่อง")

    def test_non_emergency_skips_team_leader(self):
        # คุม M2: เรื่องปกติต้องไม่ fan-out ไปหัวหน้าทีม
        reporter = self._active_user("Norm Reporter", "norm_reporter_test")
        leader = self._active_user("Norm Leader", "norm_leader_test")
        team = self.env["helpdesk.ticket.team"].create(
            {"name": "Norm Team", "user_id": leader.id}
        )
        self._create_ticket(team_id=team.id, reported_by_id=reporter.id)
        queue = self.env["od19.notification.queue"].search(
            [
                ("event", "=", "issue_updated"),
                ("partner_id", "=", leader.partner_id.id),
            ]
        )
        self.assertFalse(queue, "เรื่องปกติไม่ต้องแจ้งหัวหน้าทีม")

    def test_stage_change_notifies_reporters(self):
        # M3: เปลี่ยน stage_id ต้องแจ้งเตือน (นับเพิ่มจากตอนสร้าง)
        reporter = self._active_user("Stage Reporter", "stage_reporter_test")
        ticket = self._create_ticket(reported_by_id=reporter.id)
        domain = [
            ("event", "=", "issue_updated"),
            ("partner_id", "=", reporter.partner_id.id),
        ]
        before = self.env["od19.notification.queue"].search_count(domain)
        stage = self.env["helpdesk.ticket.stage"].create(
            {"name": "Stage Notify (test)"}
        )
        ticket.write({"stage_id": stage.id})
        after = self.env["od19.notification.queue"].search_count(domain)
        self.assertGreater(after, before, "เปลี่ยนสถานะต้องแจ้งผู้เกี่ยวข้อง")

    def test_assign_same_user_twice_notifies_once(self):
        # m4: มอบหมายผู้เดิมซ้ำต้องไม่ notify ซ้ำ
        reporter = self._active_user("Dedup Reporter", "dedup_reporter_test")
        assignee = self._active_user("Dedup Assignee", "dedup_assignee_test")
        team = self.env["helpdesk.ticket.team"].create(
            {"name": "Dedup Team", "user_ids": [(4, assignee.id)]}
        )
        ticket = self._create_ticket(team_id=team.id, reported_by_id=reporter.id)
        ticket.write({"user_id": assignee.id})
        first = self.env["od19.notification.queue"].search_count(
            [("event", "=", "issue_assigned")]
        )
        ticket.write({"user_id": assignee.id})
        second = self.env["od19.notification.queue"].search_count(
            [("event", "=", "issue_assigned")]
        )
        self.assertGreater(first, 0)
        self.assertEqual(first, second, "มอบหมายผู้เดิมซ้ำต้องไม่แจ้งเตือนซ้ำ")

    def test_priority_recompute_writes_audit_message(self):
        # m6: audit ต้องครอบการ recompute จาก impact/urgency ด้วย
        ticket = self._create_ticket(impact="I1", urgency="U1")
        ticket.impact = "I3"
        ticket.urgency = "U3"
        self.assertTrue(
            any("ปรับความสำคัญ" in (m.body or "") for m in ticket.message_ids),
            "การ recompute priority ต้องมี audit log",
        )
