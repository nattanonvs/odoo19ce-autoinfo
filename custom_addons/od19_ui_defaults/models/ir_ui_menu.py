from odoo import api, models

# Labels used by an app for its "Configuration" menu. Thai labels are included
# because a few menus are named in Thai directly in the source XML.
CONFIGURATION_MENU_LABELS = ("Configuration", "ตั้งค่า", "การตั้งค่า")


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def _od19_place_configuration_menus_last(self):
        """Move every Configuration menu to the end of its parent menu.

        Odoo reloads menu data on each module update and resets the ``sequence``
        of the menus it owns, so the rule is re-applied from
        ``data/ui_defaults.xml`` on every install/upgrade.
        """
        # Search in the source language so the lookup is independent from the
        # language the data is loaded with.
        menus = self.with_context(lang="en_US").search([
            ("name", "in", CONFIGURATION_MENU_LABELS),
            ("parent_id", "!=", False),
        ])
        for menu in menus:
            siblings = self.search([
                ("parent_id", "=", menu.parent_id.id),
                ("id", "!=", menu.id),
            ])
            if not siblings:
                continue
            last_sequence = max(siblings.mapped("sequence"))
            if menu.sequence <= last_sequence:
                menu.sequence = last_sequence + 1
