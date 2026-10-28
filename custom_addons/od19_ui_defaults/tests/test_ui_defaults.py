from odoo.tests.common import TransactionCase

from odoo.addons.od19_ui_defaults.models.ir_ui_menu import (
    APP_MENU_ORDER,
    APP_MENU_SEQUENCE_START,
    APP_MENU_SEQUENCE_STEP,
    CONFIGURATION_MENU_LABELS,
)


class TestUiDefaults(TransactionCase):
    """Project-wide UI defaults enforced by ``od19_ui_defaults``."""

    def test_configuration_menus_are_last(self):
        """Every Configuration menu must be the last menu of its parent."""
        menu_model = self.env["ir.ui.menu"].with_context(lang="en_US")
        menus = menu_model.search([
            ("name", "in", CONFIGURATION_MENU_LABELS),
            ("parent_id", "!=", False),
        ])
        self.assertTrue(menus, "Expected at least one Configuration menu")
        for menu in menus:
            siblings = menu_model.search([
                ("parent_id", "=", menu.parent_id.id),
                ("id", "!=", menu.id),
            ])
            self.assertTrue(
                all(sibling.sequence <= menu.sequence for sibling in siblings),
                "%s must be the last menu of %s"
                % (menu.complete_name, menu.parent_id.name),
            )

    def test_discount_group_granted_to_internal_users(self):
        """The Sales Discounts setting must be enabled for internal users."""
        discount_group = self.env.ref("sale.group_discount_per_so_line")
        employee_group = self.env.ref("base.group_user")
        self.assertIn(
            discount_group,
            employee_group.implied_ids,
            "sale.group_discount_per_so_line must be implied by base.group_user",
        )

    def test_app_menus_follow_business_flow(self):
        """Installed apps must be sequenced in the order of ``APP_MENU_ORDER``."""
        for index, xmlid in enumerate(APP_MENU_ORDER):
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            expected = APP_MENU_SEQUENCE_START + index * APP_MENU_SEQUENCE_STEP
            self.assertEqual(
                menu.sequence,
                expected,
                "%s must be sequenced at %s" % (xmlid, expected),
            )

    def test_app_menus_come_before_administration(self):
        """The curated apps must stay ahead of the Apps and Settings menus."""
        apps = self.env.ref("base.menu_management", raise_if_not_found=False)
        settings = self.env.ref("base.menu_administration", raise_if_not_found=False)
        self.assertTrue(apps, "Expected the Apps menu to be installed")
        self.assertTrue(settings, "Expected the Settings menu to be installed")
        for xmlid in APP_MENU_ORDER:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
            self.assertLess(menu.sequence, apps.sequence, xmlid)
            self.assertLess(menu.sequence, settings.sequence, xmlid)

    def test_app_menu_order_is_enforced_on_write(self):
        """A manual reorder of a curated app must be reverted automatically."""
        menu = self.env.ref("mail.menu_root_discuss", raise_if_not_found=False)
        if not menu:
            self.skipTest("The Discuss app is not installed")
        menu.sequence = 10000
        self.assertEqual(menu.sequence, APP_MENU_SEQUENCE_START)
