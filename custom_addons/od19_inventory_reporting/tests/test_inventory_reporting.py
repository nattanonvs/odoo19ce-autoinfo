from odoo.tests.common import TransactionCase


class TestInventoryReporting(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Inventory Report Vendor", "company_type": "company"}
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Inventory Report Product",
                "type": "consu",
                "is_storable": True,
            }
        )
        self.in_type = self.env.ref("stock.picking_type_in")
        self.out_type = self.env.ref("stock.picking_type_out")
        self.location = self.env.ref("stock.stock_location_stock")
        self.quant = self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
                "quantity": 10.0,
            }
        )

    def _create_picking(self, picking_type, state="draft", origin=None):
        picking = self.env["stock.picking"].create(
            {
                "partner_id": self.vendor.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "origin": origin,
            }
        )
        picking.write({"state": state})
        return picking

    def test_movement_backlog_report_only_shows_open_pickings(self):
        open_picking = self._create_picking(
            self.in_type, state="assigned", origin="PO-OPEN-001"
        )
        self._create_picking(self.out_type, state="done", origin="SO-DONE-001")

        report_line = self.env["od19.report.inventory.movement.backlog"].search(
            [("picking_id", "=", open_picking.id)]
        )

        self.assertEqual(len(report_line), 1)
        self.assertEqual(report_line.flow_class, "receipt")
        self.assertEqual(report_line.execution_state, "ready")
        self.assertEqual(report_line.reference_document, "PO-OPEN-001")

    def test_accuracy_report_aggregates_session_variance(self):
        session = self.env["od19.stock.count.session"].create(
            {
                "name": "Cycle Count A",
                "location_id": self.location.id,
                "state": "variance",
            }
        )
        self.env["od19.stock.count.line"].create(
            {
                "session_id": session.id,
                "quant_id": self.quant.id,
                "counted_qty": 8.0,
            }
        )

        report_line = self.env["od19.report.inventory.accuracy"].search(
            [("session_id", "=", session.id)]
        )

        self.assertEqual(len(report_line), 1)
        self.assertEqual(report_line.state, "variance")
        self.assertEqual(report_line.line_count, 1)
        self.assertEqual(report_line.variance_line_count, 1)
        self.assertEqual(report_line.total_variance_qty, -2.0)
