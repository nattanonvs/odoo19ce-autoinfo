from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create(
            {
                "name": "Main Contractor",
                "is_company": True,
                "od19_is_contractor": True,
            }
        )
        self.owner = self.env["res.partner"].create(
            {
                "name": "Project Owner",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        self.customer = self.env["res.partner"].create(
            {
                "name": "Commercial Customer",
                "is_company": True,
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        self.invalid_owner = self.env["res.partner"].create(
            {
                "name": "Invalid Owner",
                "is_company": True,
            }
        )
        self.invalid_contractor = self.env["res.partner"].create(
            {
                "name": "Invalid Contractor",
                "is_company": True,
            }
        )
        self.invalid_customer = self.env["res.partner"].create(
            {
                "name": "Invalid Customer",
                "is_company": True,
                "email": "invalid@example.com",
            }
        )

    def test_sale_order_requires_project_context_consistency(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Airport Expansion",
                "project_owner_id": self.owner.id,
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

        self.assertEqual(order.od19_project_id.project_owner_id, order.od19_project_owner_id)

    def test_project_owner_mismatch_is_blocked(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Hospital Retrofit",
                "project_owner_id": self.owner.id,
            }
        )
        another_owner = self.env["res.partner"].create({"name": "Another Owner"})

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": self.customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": another_owner.id,
                }
            )

    def test_project_create_rejects_partner_without_owner_role(self):
        with self.assertRaises(ValidationError):
            self.env["od19.sales.project"].create(
                {
                    "name": "Role Invalid Owner Project",
                    "project_owner_id": self.invalid_owner.id,
                }
            )

    def test_project_create_rejects_partner_without_contractor_role(self):
        with self.assertRaises(ValidationError):
            self.env["od19.sales.project"].create(
                {
                    "name": "Role Invalid Contractor Project",
                    "project_owner_id": self.owner.id,
                    "contractor_ids": [(6, 0, self.invalid_contractor.ids)],
                }
            )

    def test_project_write_rejects_partner_without_owner_role(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Writable Project",
                "project_owner_id": self.owner.id,
            }
        )

        with self.assertRaises(ValidationError):
            project.write({"project_owner_id": self.invalid_owner.id})

    def test_project_write_rejects_partner_without_contractor_role(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Writable Contractor Project",
                "project_owner_id": self.owner.id,
            }
        )

        with self.assertRaises(ValidationError):
            project.write({"contractor_ids": [(6, 0, self.invalid_contractor.ids)]})

    def test_sale_order_create_rejects_partner_without_customer_role(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Customer Role Project",
                "project_owner_id": self.owner.id,
            }
        )

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": self.invalid_customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": self.owner.id,
                }
            )

    def test_sale_order_create_rejects_partner_without_owner_role(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Owner Role Project",
                "project_owner_id": self.owner.id,
            }
        )

        with self.assertRaises(ValidationError):
            self.env["sale.order"].create(
                {
                    "partner_id": self.customer.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": self.invalid_owner.id,
                }
            )

    def test_sale_order_write_rejects_partner_without_customer_role(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Writable Order Project",
                "project_owner_id": self.owner.id,
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

        with self.assertRaises(ValidationError):
            order.write({"partner_id": self.invalid_customer.id})

    def test_sale_order_write_rejects_partner_without_owner_role(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Writable Order Owner Project",
                "project_owner_id": self.owner.id,
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

        with self.assertRaises(ValidationError):
            order.write({"od19_project_owner_id": self.invalid_owner.id})
