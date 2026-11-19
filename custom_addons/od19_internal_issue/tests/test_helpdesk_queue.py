from odoo.tests.common import TransactionCase, tagged


# ค่า impact/urgency ที่ให้ priority ตามที่ต้องการ (score_to_priority: ผลรวม 2..6)
#   P0 = I1+U1 (score 2), P1 = I2+U1 (score 3),
#   P2 = I3+U2 (score 5), P3 = I3+U3 (score 6)
#
# หมายเหตุ (deviation จากแผน): ฟิลด์ priority เป็น compute+store readonly=False
# ที่ขึ้นกับ impact/urgency (ซึ่งมี default I1/U1) การส่ง priority ตรง ๆ ใน create
# อาจถูก compute เขียนทับ จึงควบคุม priority ผ่าน impact/urgency แทน แล้ว assert
# ว่าได้ priority ตรงตามเจตนาเดิม (priority desc -> queue_sequence asc)
PRIORITY_VALS = {
    "0": {"impact": "I1", "urgency": "U1"},
    "1": {"impact": "I2", "urgency": "U1"},
    "2": {"impact": "I3", "urgency": "U2"},
    "3": {"impact": "I3", "urgency": "U3"},
}


@tagged("post_install", "-at_install")
class TestInternalIssueQueue(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Ticket = cls.env["helpdesk.ticket"]
        cls.Team = cls.env["helpdesk.ticket.team"]
        cls.Stage = cls.env["helpdesk.ticket.stage"]
        cls.team = cls.Team.create(
            {"name": "Queue Team (test)", "is_triage_team": True}
        )
        # สร้าง stage เองทั้งหมด (ไม่พึ่ง demo data) เพื่อความ deterministic
        cls.open_stage = cls.Stage.create({"name": "Open (test)", "closed": False})
        cls.closed_stage = cls.Stage.create({"name": "Closed (test)", "closed": True})

    def _create(self, name, priority, queue_sequence=10):
        vals = {
            "name": name,
            "description": "<p>t</p>",
            "team_id": self.team.id,
            "stage_id": self.open_stage.id,
            "queue_sequence": queue_sequence,
        }
        vals.update(PRIORITY_VALS[priority])
        ticket = self.Ticket.create(vals)
        # precondition: ยืนยันว่า priority ที่ต้องการถูกใช้จริง
        self.assertEqual(ticket.priority, priority)
        return ticket

    def test_order_priority_then_fifo(self):
        low = self._create("low", "0", 10)
        high = self._create("high", "3", 10)
        high2 = self._create("high2", "3", 20)
        # high (seq10) มาก่อน high2 (seq20) ตาม FIFO; ทั้งคู่อยู่ก่อน low
        self.assertEqual(high.queue_position, 1)
        self.assertEqual(high2.queue_position, 2)
        self.assertEqual(low.queue_position, 3)

    def test_ahead_count(self):
        first = self._create("first", "1", 10)
        second = self._create("second", "1", 20)
        self.assertEqual(first.queue_ahead_count, 0)
        self.assertEqual(second.queue_ahead_count, 1)

    def test_closed_stage_not_counted(self):
        a = self._create("a", "1", 10)
        b = self._create("b", "1", 20)
        b.stage_id = self.closed_stage
        self.assertEqual(b.queue_position, 0)
        self.assertEqual(a.queue_position, 1)
