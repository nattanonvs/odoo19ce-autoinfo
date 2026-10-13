import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Configure website menus and branding after module installation."""
    website = env.ref('website.default_website', raise_if_not_found=False)
    if not website:
        _logger.warning("Default website not found, skipping menu configuration.")
        return

    # Set the website menu root to the default main menu so our custom menus appear
    main_menu = env.ref('website.main_menu', raise_if_not_found=False)
    if main_menu:
        website.menu_id = main_menu.id

    # Remove default Odoo menu items that conflict with our custom navigation
    default_menus = env['website.menu'].sudo().search([
        ('website_id', '=', website.id),
        ('url', 'in', ['/blog', '/jobs', '/contactus']),
        ('parent_id', '!=', main_menu.id if main_menu else False),
    ])
    if default_menus:
        default_menus.unlink()
        _logger.info("Removed %d default website menu items.", len(default_menus))
