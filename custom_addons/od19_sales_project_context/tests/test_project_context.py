from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestProjectContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.contractor = self.env["res.partner"].create({"name": "Main Contractor"})
        self.owner = self.env["res.partner"].create({"name": "Project Owner"})

    def test_sale_order_requires_project_context_consistency(self):
        project = self.env["od19.sales.project"].create(
            {
                "name": "Airport Expansion",
                "project_owner_id": self.owner.id,
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": self.contractor.id,
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
                    "partner_id": self.contractor.id,
                    "od19_sale_mode": "one_time",
                    "od19_project_id": project.id,
                    "od19_project_owner_id": another_owner.id,
                }
            )
