from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSalesCompatibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_model = cls.env["od19.sales.project"]
        cls.sale_order_model = cls.env["sale.order"]
        cls.project_form_view = cls.env.ref(
            "od19_sales_project_context.view_od19_sales_project_form"
        )
        cls.sale_order_form_view = cls.env.ref("sale.view_order_form")

    def _get_arch(self, model, view, view_type):
        view_data = model.get_view(view_id=view.id, view_type=view_type)
        return etree.fromstring(view_data["arch"])

    def test_project_form_references_partner_role_domains(self):
        arch = self._get_arch(self.project_model, self.project_form_view, "form")

        expected_domains = {
            "project_owner_id": "[('od19_is_project_owner', '=', True)]",
            "contractor_ids": "[('od19_is_contractor', '=', True)]",
        }

        for field_name, expected_domain in expected_domains.items():
            nodes = arch.xpath(f"//field[@name='{field_name}']")
            self.assertTrue(nodes, f"Missing field {field_name} on sales project form.")
            self.assertEqual(
                nodes[0].get("domain"),
                expected_domain,
                f"Field {field_name} should filter partners by the expected role.",
            )

    def test_sale_order_form_references_partner_role_domains(self):
        arch = self._get_arch(self.sale_order_model, self.sale_order_form_view, "form")

        expected_domains = {
            "partner_id": "[('od19_is_commercial_customer', '=', True)]",
            "od19_project_owner_id": "[('od19_is_project_owner', '=', True)]",
        }

        for field_name, expected_domain in expected_domains.items():
            nodes = arch.xpath(f"//field[@name='{field_name}']")
            self.assertTrue(nodes, f"Missing field {field_name} on sale order form.")
            self.assertEqual(
                nodes[0].get("domain"),
                expected_domain,
                f"Field {field_name} should filter partners by the expected role.",
            )

    def test_sales_flow_accepts_role_ready_partners(self):
        commercial_customer = self.env["res.partner"].create(
            {
                "name": "Role Ready Customer",
                "is_company": True,
                "email": "customer@example.com",
                "od19_is_commercial_customer": True,
            }
        )
        project_owner = self.env["res.partner"].create(
            {
                "name": "Role Ready Owner",
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )
        contractor = self.env["res.partner"].create(
            {
                "name": "Role Ready Contractor",
                "is_company": True,
                "od19_is_contractor": True,
            }
        )

        project = self.project_model.create(
            {
                "name": "Compatibility Project",
                "project_owner_id": project_owner.id,
                "contractor_ids": [(6, 0, contractor.ids)],
            }
        )
        order = self.sale_order_model.create(
            {
                "partner_id": commercial_customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": project_owner.id,
            }
        )

        self.assertEqual(project.project_owner_id, project_owner)
        self.assertEqual(project.contractor_ids, contractor)
        self.assertEqual(order.partner_id, commercial_customer)
        self.assertEqual(order.od19_project_id, project)
        self.assertEqual(order.od19_project_owner_id, project_owner)
