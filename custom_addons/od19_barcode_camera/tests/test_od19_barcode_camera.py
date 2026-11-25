# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOd19BarcodeCamera(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.uom = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create(
            {
                "name": "OD19 Test Widget",
                "barcode": "2000000000015",
                "type": "consu",
                "is_storable": True,
                "uom_id": cls.uom.id,
            }
        )
        cls.location_src = cls.env["stock.location"].create(
            {
                "name": "OD19 Vendor",
                "usage": "supplier",
                "barcode": "OD19-LOC-SRC",
            }
        )
        cls.location_dest = cls.env["stock.location"].create(
            {
                "name": "OD19 Stock",
                "usage": "internal",
                "barcode": "OD19-LOC-DEST",
            }
        )
        cls.lot = cls.env["stock.lot"].create(
            {
                "name": "OD19-LOT-1",
                "product_id": cls.product.id,
                "company_id": cls.company.id,
            }
        )
        cls.package = cls.env["stock.package"].create({"name": "OD19-PKG-1"})
        cls.picking_type = cls.env["stock.picking.type"].create(
            {
                "name": "OD19 Receipts",
                "code": "incoming",
                "sequence_code": "OD19IN",
                "default_location_src_id": cls.location_src.id,
                "default_location_dest_id": cls.location_dest.id,
            }
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "picking_type_id": cls.picking_type.id,
                "location_id": cls.location_src.id,
                "location_dest_id": cls.location_dest.id,
            }
        )
        cls.move = cls.env["stock.move"].create(
            {
                "product_id": cls.product.id,
                "product_uom_qty": 5.0,
                "product_uom": cls.uom.id,
                "picking_id": cls.picking.id,
                "location_id": cls.location_src.id,
                "location_dest_id": cls.location_dest.id,
            }
        )
        cls.picking.action_confirm()
        # Confirming an incoming transfer auto-assigns it, which creates the
        # move line. Reuse that line instead of creating a duplicate.
        cls.move_line = cls.picking.move_line_ids.filtered(
            lambda line: line.product_id == cls.product
        )[:1]
        cls.wizard = cls.env["od19.barcode.scan.wizard"]

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------
    def test_resolve_product(self):
        result = self.wizard.resolve_barcode(self.product.barcode)
        self.assertTrue(result["matched"])
        self.assertEqual(result["type"], "product")
        self.assertEqual(result["res_model"], "product.product")
        self.assertEqual(result["res_id"], self.product.id)
        self.assertEqual(result["product_id"], self.product.id)

    def test_resolve_lot(self):
        result = self.wizard.resolve_barcode("OD19-LOT-1")
        self.assertTrue(result["matched"])
        self.assertEqual(result["type"], "lot")
        self.assertEqual(result["lot_id"], self.lot.id)
        self.assertEqual(result["product_id"], self.product.id)

    def test_resolve_location(self):
        result = self.wizard.resolve_barcode("OD19-LOC-DEST")
        self.assertTrue(result["matched"])
        self.assertEqual(result["type"], "location")
        self.assertEqual(result["location_id"], self.location_dest.id)

    def test_resolve_package(self):
        result = self.wizard.resolve_barcode("OD19-PKG-1")
        self.assertTrue(result["matched"])
        self.assertEqual(result["type"], "package")
        self.assertEqual(result["package_id"], self.package.id)

    def test_resolve_unknown(self):
        result = self.wizard.resolve_barcode("NO-SUCH-BARCODE")
        self.assertFalse(result["matched"])
        self.assertEqual(result["type"], "unknown")
        self.assertFalse(result["product_id"])

    def test_resolve_with_picking_attaches_move_line(self):
        result = self.wizard.resolve_barcode(self.product.barcode, self.picking.id)
        self.assertTrue(result["picking"])
        self.assertEqual(result["picking"]["move_line_id"], self.move_line.id)
        self.assertEqual(result["picking"]["picking_id"], self.picking.id)

    # ------------------------------------------------------------------
    # Apply to a transfer
    # ------------------------------------------------------------------
    def test_apply_scan_to_picking_sets_quantity(self):
        outcome = self.wizard.apply_scan_to_picking(
            self.picking.id, self.product.barcode, 3.0
        )
        self.assertTrue(outcome["success"], outcome.get("message"))
        self.assertAlmostEqual(self.move_line.quantity, 3.0)
        self.assertTrue(self.move_line.picked)

    def test_apply_scan_defaults_to_demand(self):
        outcome = self.wizard.apply_scan_to_picking(
            self.picking.id, self.product.barcode
        )
        self.assertTrue(outcome["success"], outcome.get("message"))
        self.assertEqual(outcome["move_line_id"], self.move_line.id)

    def test_apply_scan_with_lot_sets_lot(self):
        outcome = self.wizard.apply_scan_to_picking(
            self.picking.id, "OD19-LOT-1", 2.0
        )
        self.assertTrue(outcome["success"], outcome.get("message"))
        self.assertEqual(self.move_line.lot_id, self.lot)

    def test_apply_scan_unknown_barcode_fails(self):
        outcome = self.wizard.apply_scan_to_picking(
            self.picking.id, "NO-SUCH-BARCODE", 1.0
        )
        self.assertFalse(outcome["success"])

    def test_apply_scan_missing_picking_fails(self):
        outcome = self.wizard.apply_scan_to_picking(0, self.product.barcode, 1.0)
        self.assertFalse(outcome["success"])

    # ------------------------------------------------------------------
    # Logging and transfer helpers
    # ------------------------------------------------------------------
    def test_scan_creates_log_entry(self):
        self.wizard.resolve_barcode(self.product.barcode, self.picking.id)
        log = self.env["od19.barcode.scan.log"].search(
            [("barcode", "=", self.product.barcode)]
        )
        self.assertTrue(log)
        self.assertEqual(log[0].product_id, self.product)
        self.assertEqual(log[0].picking_id, self.picking)
        self.assertEqual(log[0].scan_type, "product")

    def test_picking_scan_count(self):
        self.wizard.resolve_barcode(self.product.barcode, self.picking.id)
        self.assertEqual(self.picking.od19_scan_count, 1)

    def test_open_scanner_action(self):
        action = self.picking.action_od19_open_barcode_scanner()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "od19_barcode_camera.scan")
        self.assertEqual(action["params"]["picking_id"], self.picking.id)
