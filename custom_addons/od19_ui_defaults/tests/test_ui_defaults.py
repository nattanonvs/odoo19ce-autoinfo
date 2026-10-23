from odoo.tests.common import TransactionCase

from odoo.addons.od19_ui_defaults.models.ir_ui_menu import (
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
