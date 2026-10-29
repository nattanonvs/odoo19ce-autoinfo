from odoo.tests.common import TransactionCase

from odoo.addons.od19_ui_defaults.models.ir_ui_menu import (
    APP_MENU_CLUSTERS,
    APP_MENU_CLUSTER_GAP,
    APP_MENU_SEQUENCE_START,
    APP_MENU_SEQUENCE_STEP,
    CONFIGURATION_MENU_LABELS,
    od19_app_menu_sequences,
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

    def test_app_menu_clusters_have_no_duplicate_apps(self):
        """An app must be listed once, in a single cluster."""
        xmlids = [xmlid for _label, cluster in APP_MENU_CLUSTERS for xmlid in cluster]
        self.assertEqual(
            len(xmlids),
            len(set(xmlids)),
            "An app xmlid is listed more than once in APP_MENU_CLUSTERS",
        )

    def test_cluster_apps_stay_inside_their_sequence_block(self):
        """Each cluster must fit in its own block and never overlap the next."""
        blocks = []
        for index, (label, cluster) in enumerate(APP_MENU_CLUSTERS):
            base = APP_MENU_SEQUENCE_START + index * APP_MENU_CLUSTER_GAP
            last = base + (len(cluster) - 1) * APP_MENU_SEQUENCE_STEP
            self.assertLess(
                last,
                base + APP_MENU_CLUSTER_GAP,
                "Cluster %r does not fit in its sequence block" % label,
            )
            blocks.append((label, base, last))
        for (previous_label, _base, previous_last), (label, base, _last) in zip(
            blocks, blocks[1:]
        ):
            self.assertLess(
                previous_last,
                base,
                "Cluster %r overlaps the following cluster %r"
                % (previous_label, label),
            )

    def test_app_menu_sequences_are_strictly_increasing(self):
        """The computed sequences must be unique and sorted."""
        sequences = [sequence for _xmlid, sequence in od19_app_menu_sequences()]
        self.assertEqual(sequences, sorted(sequences))
        self.assertEqual(len(sequences), len(set(sequences)))
        self.assertEqual(sequences[0], APP_MENU_SEQUENCE_START)

    def test_app_menus_follow_business_flow(self):
        """Installed apps must carry the sequence assigned by the clusters."""
        for xmlid, expected in od19_app_menu_sequences():
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if not menu:
                continue
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
        self.assertLess(apps.sequence, settings.sequence)
        for xmlid, _sequence in od19_app_menu_sequences():
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
