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

    def test_partner_form_contains_role_fields(self):
        arch = self._get_partner_arch(self.partner_form_view, "form")

        for field_name in (
            "od19_is_commercial_customer",
            "od19_is_project_owner",
            "od19_is_contractor",
        ):
            self.assertTrue(
                arch.xpath(f"//field[@name='{field_name}']"),
                f"Missing partner role field {field_name} on the partner form view.",
            )

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
