from odoo.tests.common import TransactionCase


class TestInventoryReturnsAndTracking(TransactionCase):
    def setUp(self):
        super().setUp()
        self.product_tmpl = self.env["product.template"].create(
            {"name": "Need Tracking", "type": "consu", "is_storable": True}
        )
        self.in_type = self.env.ref("stock.picking_type_in")
        self.out_type = self.env.ref("stock.picking_type_out")

    def test_product_with_lot_tracking_requires_reason(self):
        self.product_tmpl.write({"tracking": "lot"})
        self.assertTrue(self.product_tmpl.od19_tracking_required)
        self.assertFalse(self.product_tmpl.od19_tracking_required_reason)

    def test_product_with_serial_tracking_requires_reason(self):
        self.product_tmpl.write({"tracking": "serial"})
        self.assertTrue(self.product_tmpl.od19_tracking_required)
        self.assertFalse(self.product_tmpl.od19_tracking_required_reason)

    def test_product_tracking_requirement_recomputes_to_false_when_tracking_disabled(self):
        self.product_tmpl.write({"tracking": "lot"})
        self.assertTrue(self.product_tmpl.od19_tracking_required)

        self.product_tmpl.write({"tracking": "none"})
        self.assertFalse(self.product_tmpl.od19_tracking_required)

    def test_return_picking_is_classified_as_return(self):
        original = self.env["stock.picking"].create(
            {
                "picking_type_id": self.out_type.id,
                "location_id": self.out_type.default_location_src_id.id,
                "location_dest_id": self.out_type.default_location_dest_id.id,
            }
        )
        returned = self.env["stock.picking"].create(
            {
                "picking_type_id": self.in_type.id,
                "location_id": self.in_type.default_location_src_id.id,
                "location_dest_id": self.in_type.default_location_dest_id.id,
                "return_id": original.id,
            }
        )
        self.assertEqual(returned.od19_flow_class, "return")
