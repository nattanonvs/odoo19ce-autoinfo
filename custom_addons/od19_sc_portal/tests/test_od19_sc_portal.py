# -*- coding: utf-8 -*-
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestOd19ScPortal(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.template = cls.env["od19.sc.template"].create({
            "name": "Portal Test Template", "code": "PT-01"})
        cls.page = cls.env["od19.sc.portal.page"].create({
            "name": "Portal Test Page", "template_id": cls.template.id})

    def _make_kpi(self, **vals):
        base = {
            "page_id": self.page.id,
            "name": "Partners",
            "target_model": "res.partner",
            "aggregate": "count",
            "domain_filter": "[]",
        }
        base.update(vals)
        return self.env["od19.sc.portal.kpi"].create(base)

    # ------------------------------------------------------------------
    # KPI computation
    # ------------------------------------------------------------------
    def test_kpi_count_matches_search_count(self):
        kpi = self._make_kpi()
        card = kpi._card_values()
        self.assertFalse(card["error"], card["error"])
        self.assertEqual(
            card["value"], float(self.env["res.partner"].search_count([])))
        self.assertEqual(kpi.value, card["value"])

    def test_kpi_sum_on_integer_field(self):
        partners = self.env["res.partner"].search([])
        kpi = self._make_kpi(aggregate="sum", measure_field="id")
        card = kpi._card_values()
        self.assertFalse(card["error"], card["error"])
        self.assertEqual(card["value"], float(sum(partners.ids)))

    def test_kpi_min_on_integer_field(self):
        partners = self.env["res.partner"].search([])
        kpi = self._make_kpi(aggregate="min", measure_field="id")
        card = kpi._card_values()
        self.assertFalse(card["error"], card["error"])
        self.assertEqual(card["value"], float(min(partners.ids)))

    def test_kpi_domain_filter(self):
        kpi = self._make_kpi(
            domain_filter="[('name', 'like', 'od19-nonexistent-xyz')]")
        card = kpi._card_values()
        self.assertEqual(card["value"], 0.0)

    def test_kpi_unknown_model_reports_error(self):
        kpi = self._make_kpi(target_model="not.a.real.model")
        card = kpi._card_values()
        self.assertTrue(card["error"])
        self.assertEqual(card["value"], 0.0)

    def test_kpi_missing_measure_field_reports_error(self):
        kpi = self._make_kpi(aggregate="sum", measure_field="")
        card = kpi._card_values()
        self.assertTrue(card["error"])

    def test_value_display_includes_unit(self):
        kpi = self._make_kpi(unit="รายการ")
        card = kpi._card_values()
        self.assertTrue(card["value_display"].endswith("รายการ"))

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------
    def test_visibility_requires_publication(self):
        Page = self.env["od19.sc.portal.page"]
        domain = Page._visible_domain(self.env.user)
        self.assertIn(self.page, Page.search(domain))
        self.page.is_published = False
        self.assertNotIn(self.page, Page.search(domain))

    def test_visibility_group_restriction(self):
        Page = self.env["od19.sc.portal.page"]
        group = self.env["res.groups"].create({"name": "SC Portal Limited"})
        self.page.group_ids = [(6, 0, [group.id])]
        user = self.env["res.users"].create({
            "name": "SC Portal Outsider",
            "login": "sc_portal_outsider",
            "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.assertNotIn(self.page, Page.search(Page._visible_domain(user)))
        user.group_ids = [(4, group.id)]
        self.assertIn(self.page, Page.search(Page._visible_domain(user)))
