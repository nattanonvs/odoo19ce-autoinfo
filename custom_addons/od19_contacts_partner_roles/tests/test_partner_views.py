from lxml import etree

from odoo.tests.common import TransactionCase


class TestPartnerViews(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.partner_form_view = cls.env.ref("base.view_partner_form")
        cls.partner_search_view = cls.env.ref("base.view_res_partner_filter")

    def _get_partner_arch(self, view, view_type):
        view_data = self.partner_model.get_view(view_id=view.id, view_type=view_type)
        return etree.fromstring(view_data["arch"])

    def test_partner_form_places_role_group_on_sales_purchase_page(self):
        arch = self._get_partner_arch(self.partner_form_view, "form")
        role_groups = arch.xpath("//page[@name='sales_purchases']//group[@name='od19_partner_roles']")
        self.assertEqual(
            len(role_groups),
            1,
            "Partner role fields should be grouped once on the Sales & Purchase page.",
        )
        role_group = role_groups[0]

        for field_name in (
            "od19_is_commercial_customer",
            "od19_is_project_owner",
            "od19_is_contractor",
        ):
            self.assertTrue(
                role_group.xpath(f".//field[@name='{field_name}']"),
                f"Missing partner role field {field_name} on the partner form view.",
            )

    def test_company_only_roles_are_hidden_for_non_companies(self):
        arch = self._get_partner_arch(self.partner_form_view, "form")
        role_group = arch.xpath("//group[@name='od19_partner_roles']")[0]

        commercial_field = role_group.xpath(
            ".//field[@name='od19_is_commercial_customer']"
        )[0]
        project_owner_field = role_group.xpath(
            ".//field[@name='od19_is_project_owner']"
        )[0]
        contractor_field = role_group.xpath(".//field[@name='od19_is_contractor']")[0]

        self.assertIsNone(
            commercial_field.get("invisible"),
            "Commercial customer should remain visible on both companies and contacts.",
        )
        self.assertEqual(project_owner_field.get("invisible"), "not is_company")
        self.assertEqual(contractor_field.get("invisible"), "not is_company")

    def test_partner_search_contains_role_filters(self):
        arch = self._get_partner_arch(self.partner_search_view, "search")

        expected_filters = {
            "od19_commercial_customers": "[('od19_is_commercial_customer', '=', True)]",
            "od19_project_owners": "[('od19_is_project_owner', '=', True)]",
            "od19_contractors": "[('od19_is_contractor', '=', True)]",
        }

        for filter_name, domain in expected_filters.items():
            nodes = arch.xpath(f"//filter[@name='{filter_name}']")
            self.assertTrue(
                nodes,
                f"Missing partner role filter {filter_name} on the partner search view.",
            )
            self.assertEqual(nodes[0].get("domain"), domain)

    def test_partner_search_inserts_role_filters_after_company_filter(self):
        arch = self._get_partner_arch(self.partner_search_view, "search")

        companies_filter = arch.xpath("//filter[@name='type_company']")[0]
        following_role_filters = companies_filter.xpath(
            "following-sibling::filter[position() <= 3]"
        )

        self.assertEqual(
            [node.get("name") for node in following_role_filters],
            [
                "od19_commercial_customers",
                "od19_project_owners",
                "od19_contractors",
            ],
        )
