import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Configure website menus and branding after module installation.

    ``website.menu_id`` is a computed (non-stored) field: it resolves to the
    first top-level ``website.menu`` (``parent_id=False``) whose ``website_id``
    matches the current website.  The shared ``website.main_menu`` record has
    ``website_id=False`` and is therefore **not** the website's root menu, so
    menus parented to it never render on the website.

    This hook re-parents our custom menus (created under ``website.main_menu``)
    to the website's actual top-level menu and removes the default Odoo menu
    items that conflict with our custom navigation.
    """
    website = env.ref('website.default_website', raise_if_not_found=False)
    if not website:
        _logger.warning("Default website not found, skipping menu configuration.")
        return

    # The website's actual top-level menu (the one rendered in the header).
    top_menu = website.menu_id
    if not top_menu:
        _logger.warning("Website %s has no top-level menu; skipping.", website.name)
        return

    main_menu = env.ref('website.main_menu', raise_if_not_found=False)

    # Re-parent all menus that currently live under the shared main menu
    # to the website-specific top menu so they actually render.
    if main_menu:
        orphan_menus = env['website.menu'].sudo().search([
            ('parent_id', '=', main_menu.id),
        ])
        if orphan_menus:
            orphan_menus.write({'parent_id': top_menu.id})
            _logger.info(
                "Re-parented %d menus to website top menu.",
                len(orphan_menus),
            )

    # Remove default Odoo menu items that conflict with our custom navigation.
    default_menus = env['website.menu'].sudo().search([
        ('parent_id', '=', top_menu.id),
        ('name', 'in', ['Blog', 'Jobs', 'Contact us']),
    ])
    if default_menus:
        default_menus.unlink()
        _logger.info("Removed %d default website menu items.", len(default_menus))
