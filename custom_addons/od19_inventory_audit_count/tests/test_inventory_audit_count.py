from odoo.exceptions import ValidationError
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
