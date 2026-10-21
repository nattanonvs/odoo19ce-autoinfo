import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# Default Odoo top-level menu names that duplicate our own navigation and
# must therefore be removed from the website header.
DEFAULT_MENU_NAMES = {"blog", "jobs", "contact us", "our job offers", "shop"}


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    @api.model
    def od19_configure_menus(self):
        """Re-parent and clean up the website's top navigation.

        ``website.menu_id`` is a computed (non-stored) field resolving to the
        first top-level ``website.menu`` (``parent_id = False``) belonging to
        the website.  The shared ``website.main_menu`` record has
        ``website_id = False`` and is *not* the website root, so menus declared
        under it would never render.

        This method is called both from the module's ``post_init_hook`` and
        from a ``<function>`` tag in ``data/website_menus.xml`` so it is applied
        on every install **and** on every module upgrade.
        """
        website = self.env.ref("website.default_website", raise_if_not_found=False)
        if not website:
            _logger.warning("Default website not found, skipping menu configuration.")
            return

        top_menu = website.menu_id
        if not top_menu:
            _logger.warning("Website %s has no top-level menu; skipping.", website.name)
            return

        menu_model = self.env["website.menu"].sudo()
        main_menu = self.env.ref("website.main_menu", raise_if_not_found=False)

        # 1) Re-parent our own menus (declared under the shared main menu for
        #    this website) onto the website's real top-level menu.
        if main_menu:
            ours = menu_model.search([
                ("parent_id", "=", main_menu.id),
                ("website_id", "=", website.id),
            ])
            if ours:
                ours.write({"parent_id": top_menu.id})
                _logger.info("Re-parented %d menu(s) to the website top menu.", len(ours))

        # 2) Remove the default Odoo menus that would duplicate our navigation
        #    (Blog / Jobs / Contact us ...).  Both possible parents are checked
        #    because the defaults may still hang off the shared main menu.
        parent_ids = [top_menu.id]
        if main_menu:
            parent_ids.append(main_menu.id)
        candidates = menu_model.search([("parent_id", "in", parent_ids)])
        defaults = candidates.filtered(
            lambda m: (m.name or "").strip().lower() in DEFAULT_MENU_NAMES
        )
        if defaults:
            _logger.info("Removed %d default website menu item(s).", len(defaults))
            defaults.unlink()
