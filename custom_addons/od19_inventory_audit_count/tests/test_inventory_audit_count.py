from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestInventoryAuditCount(TransactionCase):
    def setUp(self):
        super().setUp()
        self.location = self.env.ref("stock.stock_location_stock")
        self.other_location = self.env["stock.location"].create(
            {
                "name": "Audit Overflow",
                "usage": "internal",
                "location_id": self.location.id,
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Counted Product",
                "type": "consu",
                "is_storable": True,
            }
        )
        self.quant = self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
                "quantity": 10.0,
            }
        )
        self.other_quant = self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": self.other_location.id,
                "quantity": 3.0,
            }
        )
        base_user_group = self.env.ref("base.group_user")
        stock_user_group = self.env.ref("stock.group_stock_user")
        stock_manager_group = self.env.ref("stock.group_stock_manager")
        Users = self.env["res.users"].with_context(no_reset_password=True)
        self.stock_user = Users.create(
            {
                "name": "Stock User",
                "login": "stock.user.audit@example.com",
                "email": "stock.user.audit@example.com",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "group_ids": [(6, 0, [base_user_group.id, stock_user_group.id])],
            }
        )
        self.stock_manager = Users.create(
            {
                "name": "Stock Manager",
                "login": "stock.manager.audit@example.com",
                "email": "stock.manager.audit@example.com",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            base_user_group.id,
                            stock_user_group.id,
                            stock_manager_group.id,
                        ],
                    )
                ],
            }
        )

    def _create_session_with_line(self, counted_qty):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Audit Session", "location_id": self.location.id}
        )
        self.env["od19.stock.count.line"].create(
            {
                "session_id": session.id,
                "quant_id": self.quant.id,
                "counted_qty": counted_qty,
            }
        )
        return session

    def test_count_session_starts_in_scheduled_state(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Main Count", "location_id": self.location.id}
        )
        self.assertEqual(session.state, "scheduled")

    def test_session_line_computes_variance(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Variance Count", "location_id": self.location.id}
        )
        line = self.env["od19.stock.count.line"].create(
            {
                "session_id": session.id,
                "quant_id": self.quant.id,
                "counted_qty": 8.0,
            }
        )
        self.assertEqual(line.system_qty, 10.0)
        self.assertEqual(line.variance_qty, -2.0)

    def test_system_qty_keeps_snapshot_when_quant_changes_later(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Snapshot Count", "location_id": self.location.id}
        )
        line = self.env["od19.stock.count.line"].create(
            {
                "session_id": session.id,
                "quant_id": self.quant.id,
                "counted_qty": 8.0,
            }
        )

        self.quant.write({"quantity": 4.0})
        line.invalidate_recordset(["system_qty", "variance_qty"])

        self.assertEqual(line.system_qty, 10.0)
        self.assertEqual(line.variance_qty, -2.0)

    def test_session_line_rejects_quant_from_other_location(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Mismatch Count", "location_id": self.location.id}
        )

        with self.assertRaises(ValidationError):
            self.env["od19.stock.count.line"].create(
                {
                    "session_id": session.id,
                    "quant_id": self.other_quant.id,
                    "counted_qty": 3.0,
                }
            )

    def test_session_line_rejects_duplicate_quant_in_same_session(self):
        session = self.env["od19.stock.count.session"].create(
            {"name": "Duplicate Count", "location_id": self.location.id}
        )
        self.env["od19.stock.count.line"].create(
            {
                "session_id": session.id,
                "quant_id": self.quant.id,
                "counted_qty": 10.0,
            }
        )

        with self.assertRaises(ValidationError):
            self.env["od19.stock.count.line"].create(
                {
                    "session_id": session.id,
                    "quant_id": self.quant.id,
                    "counted_qty": 9.0,
                }
            )

    def test_workflow_counted_to_pending_approval(self):
        session = self._create_session_with_line(8.0)
        session.action_mark_counted()
        self.assertEqual(session.state, "counted")
        session.action_submit_for_approval()
        self.assertEqual(session.state, "pending_approval")

    def test_create_adjustment_updates_quant(self):
        session = self._create_session_with_line(8.0)
        session.action_mark_counted()
        session.action_submit_for_approval()
        session.action_create_adjustment()
        self.assertEqual(session.state, "adjusted")
        self.assertEqual(self.quant.quantity, 8.0)
        self.assertEqual(session.approved_by, self.env.user)

    def test_create_adjustment_with_positive_variance(self):
        session = self._create_session_with_line(12.0)
        session.action_mark_counted()
        session.action_submit_for_approval()
        session.action_create_adjustment()
        self.assertEqual(self.quant.quantity, 12.0)

    def test_create_adjustment_requires_manager(self):
        session = self._create_session_with_line(8.0)
        session.action_mark_counted()
        session.action_submit_for_approval()
        with self.assertRaises(AccessError):
            session.with_user(self.stock_user).action_create_adjustment()
        # Manager can apply
        session.with_user(self.stock_manager).action_create_adjustment()
        self.assertEqual(session.state, "adjusted")

    def test_create_adjustment_only_from_pending_approval(self):
        session = self._create_session_with_line(8.0)
        with self.assertRaises(UserError):
            session.action_create_adjustment()

    def test_cancelled_session_can_be_reset(self):
        session = self._create_session_with_line(8.0)
        session.action_cancel()
        self.assertEqual(session.state, "cancelled")
        session.action_reset_to_scheduled()
        self.assertEqual(session.state, "scheduled")

    def test_adjusted_session_cannot_be_cancelled(self):
        session = self._create_session_with_line(8.0)
        session.action_mark_counted()
        session.action_submit_for_approval()
        session.action_create_adjustment()
        with self.assertRaises(UserError):
            session.action_cancel()
