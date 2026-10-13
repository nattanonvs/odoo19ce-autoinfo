from odoo.tests.common import TransactionCase


class TestProcurementIntegration(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env["res.partner"].create(
            {"name": "Integrated Vendor", "company_type": "company"}
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Integrated Customer",
                "company_type": "company",
                "is_company": True,
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
                "od19_is_contractor": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Integrated Owner",
                "company_type": "company",
                "is_company": True,
                "email": "owner@example.com",
                "od19_is_project_owner": True,
            }
        )
        self.project = self.env["project.project"].create(
            {
                "name": "Integrated Project",
                "project_owner_id": self.owner.id,
                "contractor_ids": [(6, 0, [self.customer.id])],
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "Integrated Product",
                "purchase_ok": True,
                "type": "consu",
            }
        )
        self.service = self.env["product.product"].create(
            {
                "name": "Integrated Service",
                "purchase_ok": True,
                "type": "service",
            }
        )

    def test_service_line_sets_service_acceptance_flag(self):
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
                "od19_project_id": self.project.id,
            }
        )
        self.assertTrue(line.od19_requires_service_acceptance)

    def test_project_line_without_budget_reference_raises_warning_flag(self):
        order = self.env["purchase.order"].create({"partner_id": self.vendor.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "name": self.product.display_name,
                "product_id": self.product.id,
                "product_qty": 2,
                "price_unit": 100,
                "date_planned": "2026-10-06 00:00:00",
                "product_uom_id": self.product.uom_id.id,
                "od19_procurement_purpose": "project",
                "od19_project_id": self.project.id,
            }
        )
        self.assertTrue(line.od19_budget_warning)
        self.assertIn("budget reference", line.od19_budget_warning_message.lower())
        self.assertEqual(order.od19_budget_warning_count, 1)
        self.assertIn(line.name, order.od19_budget_warning_summary)
        self.assertIn("budget reference", order.od19_budget_warning_summary.lower())
