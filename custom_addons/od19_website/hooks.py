import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Configure the website top navigation right after installation.

    The actual logic lives on ``website.menu.od19_configure_menus`` so that it
    can also be replayed on every module upgrade through a ``<function>`` tag
    in ``data/website_menus.xml``.
    """
    try:
        env["website.menu"].od19_configure_menus()
    except Exception:  # noqa: BLE001 - never break the installation
        _logger.exception("Failed to configure the website menus.")

    try:
        env["blog.blog"].od19_setup_blog()
    except Exception:  # noqa: BLE001 - never break the installation
        _logger.exception("Failed to set up the News & Events blog.")
