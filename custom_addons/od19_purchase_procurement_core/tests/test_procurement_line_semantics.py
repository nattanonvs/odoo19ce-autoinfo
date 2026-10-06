from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProcurementLineSemantics(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Procurement Vendor", "company_type": "company"}
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Project Customer",
                "company_type": "company",
                "is_company": True,
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
                "od19_is_contractor": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Project Owner",
                "company_type": "company",
                "is_company": True,
                "email": "owner@example.com",
                "od19_is_project_owner": True,
            }
        )
        self.project = self.env["od19.sales.project"].create(
            {
                "name": "Procurement Project",
                "project_owner_id": self.owner.id,
                "contractor_ids": [(6, 0, [self.customer.id])],
            }
        )
        self.sale_order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": self.project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Purchase Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        self.service = self.env["product.product"].create(
            {
                "name": "Purchase Service",
                "purchase_ok": True,
                "type": "service",
            }
        )

    def test_internal_line_does_not_require_project_context(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 1,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom_id": self.product.uom_id.id,
                "od19_procurement_purpose": "internal",
                "od19_item_kind": "product",
            }
        )
        self.assertEqual(line.od19_procurement_purpose, "internal")
        self.assertFalse(line.od19_project_id)

    def test_project_line_requires_project_reference(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        with self.assertRaises(ValidationError):
            self.env["purchase.order.line"].create(
                {
                    "order_id": order.id,
                    "name": self.product.display_name,
                    "product_id": self.product.id,
                    "product_qty": 1,
                    "price_unit": 100,
                    "date_planned": "2026-10-06 00:00:00",
                    "product_uom_id": self.product.uom_id.id,
                    "od19_procurement_purpose": "project",
                    "od19_item_kind": "product",
                }
            )

    def test_project_line_accepts_project_and_sale_reference(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.service.display_name,
                "product_id": self.service.id,
                "product_qty": 1,
                "price_unit": 500,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom_id": self.service.uom_id.id,
                "od19_procurement_purpose": "project",
                "od19_item_kind": "service",
                "od19_project_id": self.project.id,
                "od19_sale_order_id": self.sale_order.id,
            }
        )
        self.assertEqual(line.od19_project_id, self.project)
        self.assertEqual(line.od19_sale_order_id, self.sale_order)
