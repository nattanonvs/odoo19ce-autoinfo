from lxml import etree

from odoo.addons.od19_contacts_partner_roles import hooks
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSalesCompatibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_model = cls.env["project.project"]
        cls.sale_order_model = cls.env["sale.order"]
        cls.project_form_view = cls.env.ref("project.edit_project")
        cls.sale_order_form_view = cls.env.ref("sale.view_order_form")

    def _get_arch(self, model, view, view_type):
        view_data = model.get_view(view_id=view.id, view_type=view_type)
        return etree.fromstring(view_data["arch"])

    def _make_role_ready_customer(self, name="Role Ready Customer"):
        return self.env["res.partner"].create(
            {
                "name": name,
                "is_company": True,
                "email": f"{name.lower().replace(' ', '.')}@example.com",
                "od19_is_commercial_customer": True,
            }
        )

    def _make_role_ready_owner(self, name="Role Ready Owner"):
        return self.env["res.partner"].create(
            {
                "name": name,
                "is_company": True,
                "od19_is_project_owner": True,
            }
        )

    def _make_role_ready_contractor(self, name="Role Ready Contractor"):
        return self.env["res.partner"].create(
            {
                "name": name,
                "is_company": True,
                "od19_is_contractor": True,
            }
        )

    def _make_person_partner(self, name):
        return self.env["res.partner"].create(
            {
                "name": name,
                "company_type": "person",
            }
        )

    def test_backfill_is_noop_without_sales_models(self):
        class DummyPartnerModel:
            def __init__(self):
                self.invalidated_fields = None

            def invalidate_model(self, fields):
                self.invalidated_fields = fields

        class DummyEnv:
            def __init__(self):
                self.registry = {"res.partner": object()}
                self.partner_model = DummyPartnerModel()

            def __getitem__(self, model_name):
                if model_name != "res.partner":
                    raise KeyError(model_name)
                return self.partner_model

        dummy_env = DummyEnv()

        hooks.backfill_sales_partner_roles(dummy_env)

        self.assertIsNone(dummy_env.partner_model.invalidated_fields)

    def test_role_backfill_tolerates_absent_optional_fields(self):
        # ``project_owner_id``/``contractor_ids`` and ``od19_project_owner_id``
        # are contributed by companion modules this module does not depend on.
        # Reading them is therefore optional: a field that is missing from the
        # model must be skipped instead of raising ``KeyError`` while the
        # registry loads.
        self.assertEqual(
            hooks._field_ids(self.env["project.project"], "missing_field"), set()
        )
        role_ids = hooks._collect_sales_partner_role_ids(self.env)
        self.assertEqual(
            set(role_ids), {"commercial_customer", "project_owner", "contractor"}
        )

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
        commercial_customer = self._make_role_ready_customer()
        project_owner = self._make_role_ready_owner()
        contractor = self._make_role_ready_contractor()

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

    def test_backfill_marks_only_referenced_sales_partners(self):
        from odoo.addons.od19_contacts_partner_roles.hooks import (
            backfill_sales_partner_roles,
        )

        commercial_customer = self._make_role_ready_customer("Legacy Customer")
        project_owner = self._make_role_ready_owner("Legacy Owner")
        contractor = self._make_role_ready_contractor("Legacy Contractor")
        untouched_partner = self.env["res.partner"].create(
            {
                "name": "Untouched Partner",
                "is_company": True,
                "email": "untouched@example.com",
            }
        )

        project = self.project_model.create(
            {
                "name": "Legacy Compatibility Project",
                "project_owner_id": project_owner.id,
                "contractor_ids": [(6, 0, contractor.ids)],
            }
        )
        self.sale_order_model.create(
            {
                "partner_id": commercial_customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": project_owner.id,
            }
        )

        self.env.cr.execute(
            """
            UPDATE res_partner
               SET od19_is_commercial_customer = FALSE,
                   od19_is_project_owner = FALSE,
                   od19_is_contractor = FALSE
             WHERE id IN %s
            """,
            [tuple((commercial_customer + project_owner + contractor).ids)],
        )
        self.env["res.partner"].invalidate_model(
            [
                "od19_is_commercial_customer",
                "od19_is_project_owner",
                "od19_is_contractor",
            ]
        )

        self.assertFalse(commercial_customer.od19_is_commercial_customer)
        self.assertFalse(project_owner.od19_is_project_owner)
        self.assertFalse(contractor.od19_is_contractor)
        self.assertFalse(untouched_partner.od19_is_commercial_customer)
        self.assertFalse(untouched_partner.od19_is_project_owner)
        self.assertFalse(untouched_partner.od19_is_contractor)

        backfill_sales_partner_roles(self.env)

        self.assertTrue(commercial_customer.od19_is_commercial_customer)
        self.assertTrue(project_owner.od19_is_project_owner)
        self.assertTrue(contractor.od19_is_contractor)
        self.assertFalse(untouched_partner.od19_is_commercial_customer)
        self.assertFalse(untouched_partner.od19_is_project_owner)
        self.assertFalse(untouched_partner.od19_is_contractor)

    def test_backfill_marks_sale_order_project_owner_reference(self):
        commercial_customer = self._make_role_ready_customer("Legacy SO Customer")
        project_owner = self._make_role_ready_owner("Legacy SO Owner")
        project = self.project_model.create(
            {
                "name": "Legacy SO Project",
                "project_owner_id": project_owner.id,
            }
        )
        self.sale_order_model.create(
            {
                "partner_id": commercial_customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": project_owner.id,
            }
        )

        self.env.cr.execute(
            """
            UPDATE res_partner
               SET od19_is_project_owner = FALSE
             WHERE id = %s
            """,
            [project_owner.id],
        )
        self.env["res.partner"].invalidate_model(["od19_is_project_owner"])
        self.assertFalse(project_owner.od19_is_project_owner)

        hooks.backfill_sales_partner_roles(self.env)

        self.assertTrue(project_owner.od19_is_project_owner)

    def test_model_upgrade_hook_reuses_backfill_helper(self):
        original = hooks.backfill_sales_partner_roles
        calls = []

        def tracked_backfill(env):
            calls.append(env)
            return original(env)

        hooks.backfill_sales_partner_roles = tracked_backfill
        try:
            result = self.env["res.partner"]._run_od19_sales_partner_role_backfill()
        finally:
            hooks.backfill_sales_partner_roles = original

        self.assertIsNone(result)
        self.assertEqual(calls, [self.env])

    def test_model_upgrade_hook_backfill_is_idempotent(self):
        commercial_customer = self._make_role_ready_customer("Upgrade Customer")
        project_owner = self._make_role_ready_owner("Upgrade Owner")
        contractor = self._make_role_ready_contractor("Upgrade Contractor")
        project = self.project_model.create(
            {
                "name": "Upgrade Project",
                "project_owner_id": project_owner.id,
                "contractor_ids": [(6, 0, contractor.ids)],
            }
        )
        self.sale_order_model.create(
            {
                "partner_id": commercial_customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": project_owner.id,
            }
        )

        self.env["res.partner"]._run_od19_sales_partner_role_backfill()
        self.env["res.partner"].invalidate_model(
            [
                "od19_is_commercial_customer",
                "od19_is_project_owner",
                "od19_is_contractor",
            ]
        )
        first_state = (
            commercial_customer.od19_is_commercial_customer,
            project_owner.od19_is_project_owner,
            contractor.od19_is_contractor,
        )

        self.env["res.partner"]._run_od19_sales_partner_role_backfill()
        self.env["res.partner"].invalidate_model(
            [
                "od19_is_commercial_customer",
                "od19_is_project_owner",
                "od19_is_contractor",
            ]
        )
        second_state = (
            commercial_customer.od19_is_commercial_customer,
            project_owner.od19_is_project_owner,
            contractor.od19_is_contractor,
        )

        self.assertEqual(first_state, (True, True, True))
        self.assertEqual(second_state, first_state)

    def test_backfill_does_not_mark_person_as_project_owner(self):
        company_owner = self._make_role_ready_owner("Company Owner")
        person_owner = self._make_person_partner("Person Owner")
        customer = self._make_role_ready_customer("Project Owner Customer")
        project = self.project_model.create(
            {
                "name": "Person Owner Project",
                "project_owner_id": company_owner.id,
            }
        )
        order = self.sale_order_model.create(
            {
                "partner_id": customer.id,
                "od19_sale_mode": "one_time",
                "od19_project_id": project.id,
                "od19_project_owner_id": company_owner.id,
            }
        )

        self.env.cr.execute(
            """
            UPDATE project_project
               SET project_owner_id = %s
             WHERE id = %s
            """,
            [person_owner.id, project.id],
        )
        self.env.cr.execute(
            """
            UPDATE sale_order
               SET od19_project_owner_id = %s
             WHERE id = %s
            """,
            [person_owner.id, order.id],
        )
        self.env.cr.execute(
            """
            UPDATE res_partner
               SET od19_is_project_owner = FALSE
             WHERE id IN %s
            """,
            [tuple((company_owner + person_owner).ids)],
        )
        self.env["project.project"].invalidate_model(["project_owner_id"])
        self.env["sale.order"].invalidate_model(["od19_project_owner_id"])
        self.env["res.partner"].invalidate_model(["od19_is_project_owner"])

        hooks.backfill_sales_partner_roles(self.env)

        self.assertFalse(person_owner.od19_is_project_owner)
        self.assertFalse(company_owner.od19_is_project_owner)

    def test_backfill_does_not_mark_person_as_contractor(self):
        contractor_company = self._make_role_ready_contractor("Company Contractor")
        person_contractor = self._make_person_partner("Person Contractor")
        owner = self._make_role_ready_owner("Contractor Owner")
        project = self.project_model.create(
            {
                "name": "Person Contractor Project",
                "project_owner_id": owner.id,
                "contractor_ids": [(6, 0, contractor_company.ids)],
            }
        )

        self.env.cr.execute(
            """
            DELETE FROM project_contractor_rel
             WHERE project_id = %s
            """,
            [project.id],
        )
        self.env.cr.execute(
            """
            INSERT INTO project_contractor_rel
                (project_id, partner_id)
            VALUES (%s, %s)
            """,
            [project.id, person_contractor.id],
        )
        self.env.cr.execute(
            """
            UPDATE res_partner
               SET od19_is_contractor = FALSE
             WHERE id IN %s
            """,
            [tuple((contractor_company + person_contractor).ids)],
        )
        self.env["project.project"].invalidate_model(["contractor_ids"])
        self.env["res.partner"].invalidate_model(["od19_is_contractor"])

        hooks.backfill_sales_partner_roles(self.env)

        self.assertFalse(person_contractor.od19_is_contractor)
        self.assertFalse(contractor_company.od19_is_contractor)
