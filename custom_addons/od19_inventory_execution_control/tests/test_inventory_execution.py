from odoo.tests.common import TransactionCase


class TestInventoryExecution(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Receipt Vendor", "company_type": "company"}
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Delivery Customer",
                "company_type": "company",
                "is_company": True,
                "email": "delivery.customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Project Owner",
                "company_type": "company",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Tracked Product",
                "type": "consu",
                "is_storable": True,
                "sale_ok": True,
                "purchase_ok": True,
            }
        )
        self.in_type = self.env.ref("stock.picking_type_in")
        self.out_type = self.env.ref("stock.picking_type_out")
        self.internal_type = self.env.ref("stock.picking_type_internal")

    def _create_picking(self, picking_type, partner=None, origin=None, return_id=None):
        values = {
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
        }
        if partner:
            values["partner_id"] = partner.id
        if origin:
            values["origin"] = origin
        if return_id:
            values["return_id"] = return_id.id
        return self.env["stock.picking"].create(values)

    def _create_move(self, picking, origin=None):
        values = {
            "description_picking": self.product.display_name,
            "product_id": self.product.id,
            "product_uom_qty": 1.0,
            "product_uom": self.product.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "picking_id": picking.id,
        }
        if origin:
            values["origin"] = origin
        return self.env["stock.move"].create(values)

    def _create_project(self):
        return self.env["project.project"].create(
            {
                "name": "Inventory Execution Project",
                "project_owner_id": self.owner.id,
            }
        )

    def test_receipt_flow_class_is_computed_from_operation_type(self):
        picking = self._create_picking(self.in_type, partner=self.vendor)
        self.assertEqual(picking.od19_flow_class, "receipt")
        self.assertEqual(picking.od19_execution_state, "waiting")

    def test_internal_transfer_flow_class_is_computed(self):
        picking = self._create_picking(self.internal_type)
        self.assertEqual(picking.od19_flow_class, "transfer")

    def test_done_picking_is_reported_as_done_execution_state(self):
        picking = self._create_picking(self.out_type, partner=self.customer)
        picking.write({"state": "done"})
        self.assertEqual(picking.od19_execution_state, "done")

    def test_assigned_picking_is_reported_as_ready_execution_state(self):
        picking = self._create_picking(self.out_type, partner=self.customer)
        picking.write({"state": "assigned"})
        self.assertEqual(picking.od19_execution_state, "ready")

    def test_cancelled_picking_is_reported_as_exception_execution_state(self):
        picking = self._create_picking(self.out_type, partner=self.customer)
        picking.write({"state": "cancel"})
        self.assertEqual(picking.od19_execution_state, "exception")

    def test_return_picking_is_classified_from_return_id(self):
        original_picking = self._create_picking(
            self.out_type, partner=self.customer, origin="SO-RETURN-001"
        )
        return_picking = self._create_picking(
            self.in_type,
            partner=self.customer,
            origin="Return of SO-RETURN-001",
            return_id=original_picking,
        )
        self.assertEqual(return_picking.od19_flow_class, "return")

    def test_move_inherits_reference_document_from_origin(self):
        picking = self._create_picking(self.out_type, partner=self.customer, origin="SO0001")
        move = self._create_move(picking)
        self.assertEqual(move.od19_reference_document, "SO0001")

    def test_move_recomputes_reference_document_from_picking_origin(self):
        picking = self._create_picking(self.out_type, partner=self.customer, origin="SO0001")
        move = self._create_move(picking)
        self.assertEqual(move.od19_reference_document, "SO0001")
        picking.write({"origin": "SO0002"})
        self.assertEqual(move.od19_reference_document, "SO0002")

    def test_purchase_stock_confirmation_creates_receipt_picking_truth(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 2.0,
                "price_unit": 50.0,
                "date_planned": "2026-10-07 00:00:00",
                "product_uom_id": self.product.uom_id.id,
            }
        )

        order.action_od19_submit_for_approval()
        order.action_od19_approve()
        order.button_confirm()

        picking = order.picking_ids.filtered(
            lambda candidate: candidate.picking_type_code == "incoming"
        ).ensure_one()
        self.assertEqual(picking.od19_flow_class, "receipt")
        self.assertEqual(picking.move_ids[:1].od19_reference_document, order.name)

    def test_sale_stock_confirmation_creates_delivery_picking_truth(self):
        project = self._create_project()
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "name": self.product.display_name,
                "product_uom_qty": 1.0,
                "product_uom_id": self.product.uom_id.id,
                "price_unit": 100.0,
            }
        )

        order.action_confirm()

        picking = order.picking_ids.filtered(
            lambda candidate: candidate.picking_type_code == "outgoing"
        ).ensure_one()
        self.assertEqual(picking.od19_flow_class, "delivery")
        self.assertEqual(picking.move_ids[:1].od19_reference_document, order.name)
