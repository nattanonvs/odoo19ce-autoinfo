# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestFifoLotTracking(TransactionCase):
    """FIFO-costed products must be tracked by lot or serial."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fifo_category = cls.env["product.category"].create(
            {
                "name": "FIFO Category",
                "property_cost_method": "fifo",
                "property_valuation": "manual_periodic",
            }
        )
        cls.lot_category = cls.env["product.category"].create(
            {
                "name": "Standard Category",
                "property_cost_method": "standard",
            }
        )

    def test_fifo_product_without_tracking_is_rejected(self):
        """A FIFO storable product with tracking=none cannot be saved."""
        with self.assertRaises(ValidationError):
            self.env["product.product"].create(
                {
                    "name": "FIFO Without Lot",
                    "type": "consu",
                    "is_storable": True,
                    "categ_id": self.fifo_category.id,
                    "tracking": "none",
                }
            )

    def test_fifo_product_with_lot_tracking_is_allowed(self):
        """A FIFO product tracked by lot can be created."""
        product = self.env["product.product"].create(
            {
                "name": "FIFO With Lot",
                "type": "consu",
                "is_storable": True,
                "categ_id": self.fifo_category.id,
                "tracking": "lot",
            }
        )
        self.assertEqual(product.tracking, "lot")
        self.assertTrue(product.od19_tracking_required)

    def test_fifo_product_with_serial_tracking_is_allowed(self):
        """A FIFO product tracked by serial number can be created."""
        product = self.env["product.product"].create(
            {
                "name": "FIFO With Serial",
                "type": "consu",
                "is_storable": True,
                "categ_id": self.fifo_category.id,
                "tracking": "serial",
            }
        )
        self.assertEqual(product.tracking, "serial")

    def test_standard_cost_product_without_tracking_is_allowed(self):
        """Non-FIFO products are not forced to use lot tracking."""
        product = self.env["product.product"].create(
            {
                "name": "Standard No Lot",
                "type": "consu",
                "is_storable": True,
                "categ_id": self.lot_category.id,
                "tracking": "none",
            }
        )
        self.assertFalse(product.od19_tracking_required)

    def test_changing_cost_method_to_fifo_without_tracking_fails(self):
        """Switching a non-tracked product's category to FIFO is rejected."""
        product = self.env["product.product"].create(
            {
                "name": "Will Become FIFO",
                "type": "consu",
                "is_storable": True,
                "categ_id": self.lot_category.id,
                "tracking": "none",
            }
        )
        with self.assertRaises(ValidationError):
            product.categ_id = self.fifo_category


class TestValuationByLotReport(TransactionCase):
    """The valuation-by-lot view aggregates on-hand quantity per lot."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env["product.category"].create(
            {
                "name": "Test Category",
                "property_cost_method": "standard",
                "property_valuation": "manual_periodic",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Lot Valuation Product",
                "type": "consu",
                "is_storable": True,
                "categ_id": cls.category.id,
                "standard_price": 10.0,
                "tracking": "lot",
            }
        )
        cls.location = cls.env.ref("stock.stock_location_stock")

    def test_report_aggregates_quantity_and_value_per_lot(self):
        lot = self.env["stock.production.lot"].create(
            {
                "name": "LOT-001",
                "product_id": self.product.id,
                "company_id": self.env.company.id,
            }
        )
        self.env["stock.quant"].create(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
                "lot_id": lot.id,
                "quantity": 5.0,
            }
        )
        report_line = self.env["od19.stock.valuation.by.lot"].search(
            [("lot_id", "=", lot.id)], limit=1
        )
        self.assertTrue(report_line)
        self.assertEqual(report_line.quantity, 5.0)
        self.assertEqual(report_line.unit_cost, 10.0)
        self.assertEqual(report_line.total_value, 50.0)
