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

    def _create_project(self, name, owner=None, contractor=None, job_no=None):
        vals = {
            "name": name,
            "job_no": job_no or f"JOB-{name[:4].upper()}-001",
        }
        if owner:
            vals["project_owner_id"] = owner.id
        if contractor:
            vals["contractor_ids"] = [(6, 0, contractor.ids)]
        return self.env["project.project"].create(vals)

    def test_sale_order_requires_project_context_consistency(self):
        project = self._create_project("Airport Expansion", owner=self.owner)

        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": self.owner.id,
            }
        )

        self.assertEqual(
            order.od19_project_id.project_owner_id, order.od19_project_owner_id
        )

    def test_project_owner_mismatch_is_blocked(self):
        project = self._create_project("Hospital Retrofit", owner=self.owner)
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

    def test_sale_order_accepts_any_partner_for_core_compatibility(self):
        """Core Odoo modules create sale orders with regular partners.

        Partner role validation is enforced at the view level (domain on
        partner_id), not at the model level, to preserve core compatibility.
        """
        regular_partner = self.env["res.partner"].create(
            {"name": "Regular Partner", "is_company": True}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": regular_partner.id,
                "od19_sale_mode": "one_time",
            }
        )
        self.assertEqual(order.partner_id, regular_partner)

    def test_onchange_project_sets_project_owner(self):
        project = self._create_project("Onchange Project", owner=self.owner)
        order = self.env["sale.order"].new(
            {
                "partner_id": self.customer.id,
                "od19_sale_mode": "one_time",
            }
        )
        order.od19_project_id = project
        order._onchange_od19_project_id()
        self.assertEqual(order.od19_project_owner_id, self.owner)
