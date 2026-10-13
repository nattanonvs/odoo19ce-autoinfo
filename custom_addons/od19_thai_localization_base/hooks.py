# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Set default company font to Sarabun and enable Buddhist year."""
    companies = env["res.company"].sudo().search([])
    for company in companies:
        vals = {}
        if company.font != "Sarabun":
            vals["font"] = "Sarabun"
        if not company.l10n_th_buddhist_year:
            vals["l10n_th_buddhist_year"] = True
        if vals:
            company.write(vals)
            _logger.info(
                "Company %s: updated Thai localization config %s",
                company.name,
                vals,
            )
