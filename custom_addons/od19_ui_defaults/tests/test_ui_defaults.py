from odoo.tests.common import TransactionCase

from odoo.addons.od19_ui_defaults.models.ir_ui_menu import (
    APP_MENU_CLUSTERS,
    APP_MENU_CLUSTER_GAP,
    APP_MENU_SEQUENCE_START,
    APP_MENU_SEQUENCE_STEP,
    CONFIGURATION_MENU_LABELS,
    NAVBAR_GROUPS,
    NAVBAR_GROUP_MODULE,
    NAVBAR_MOVES,
    NAVBAR_RENAMES,
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

    def test_navbar_groups_gather_sections(self):
        """Each installed group must own its sections as a single dropdown."""
        self.env["ir.ui.menu"]._od19_apply_navbar_groups()
        for group_name, _label_en, label_th, parent_xmlid, sequence, child_xmlids in NAVBAR_GROUPS:
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            children = [self.env.ref(x, raise_if_not_found=False) for x in child_xmlids]
            if not parent or not all(children):
                continue
            group = self.env.ref(
                "%s.%s" % (NAVBAR_GROUP_MODULE, group_name), raise_if_not_found=False
            )
            self.assertTrue(group, "Missing NavBar group %s" % group_name)
            self.assertEqual(group.parent_id, parent)
            self.assertFalse(group.action, "A NavBar group must not carry an action")
            self.assertEqual(group.sequence, sequence)
            self.assertEqual(group.with_context(lang="th_TH").name, label_th)
            for child in children:
                self.assertEqual(child.parent_id, group)
                self.assertNotIn(child, parent.child_id)

    def test_navbar_groups_are_idempotent(self):
        """Re-applying the grouping must not create duplicate sections."""
        menu_model = self.env["ir.ui.menu"]
        data_model = self.env["ir.model.data"]
        domain = [("module", "=", NAVBAR_GROUP_MODULE), ("model", "=", "ir.ui.menu")]
        menu_model._od19_apply_navbar_groups()
        count = data_model.search_count(domain)
        self.assertLessEqual(count, len(NAVBAR_GROUPS))
        menu_model._od19_apply_navbar_groups()
        self.assertEqual(data_model.search_count(domain), count)

    def test_navbar_grouping_is_reapplied_on_write(self):
        """Moving a grouped section back to its app must be reverted."""
        for group_name, _label_en, _label_th, parent_xmlid, _sequence, child_xmlids in NAVBAR_GROUPS:
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            child = self.env.ref(child_xmlids[0], raise_if_not_found=False)
            group = self.env.ref(
                "%s.%s" % (NAVBAR_GROUP_MODULE, group_name), raise_if_not_found=False
            )
            if not parent or not child or not group:
                continue
            child.parent_id = parent
            self.assertNotEqual(
                child.parent_id,
                parent,
                "%s must be pulled back inside its NavBar group" % child_xmlids[0],
            )
            self.assertEqual(child.parent_id, group)
            break

    def test_navbar_moves_are_applied(self):
        """A moved section must sit inside its target section, in order."""
        menu_model = self.env["ir.ui.menu"]
        menu_model._od19_apply_navbar_groups()
        for menu_xmlid, parent_xmlid, sequence in NAVBAR_MOVES:
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            parent = self.env.ref(parent_xmlid, raise_if_not_found=False)
            if not menu or not parent:
                continue
            self.assertEqual(menu.parent_id, parent)
            self.assertEqual(menu.sequence, sequence)

    def test_navbar_renames_are_applied(self):
        """A renamed section must carry the new label in both languages."""
        self.env["ir.ui.menu"]._od19_apply_navbar_groups()
        for menu_xmlid, label_en, label_th in NAVBAR_RENAMES:
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            if not menu:
                continue
            self.assertEqual(menu.with_context(lang="en_US").name, label_en)
            self.assertEqual(menu.with_context(lang="th_TH").name, label_th)

    def test_navbar_rename_is_reapplied_on_write(self):
        """Renaming a managed section manually must be reverted."""
        menu_xmlid, label_en, _label_th = NAVBAR_RENAMES[0]
        menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
        if not menu:
            self.skipTest("%s is not installed" % menu_xmlid)
        menu.name = "ZZZ"
        self.assertEqual(menu.with_context(lang="en_US").name, label_en)
