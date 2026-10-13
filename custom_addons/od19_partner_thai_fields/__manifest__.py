# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Thai Partner Fields",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "Thai-specific partner fields: tax name, branch code, English name/address, fax",
    "author": "Custom",
    "website": "https://github.com/OCA/l10n-thailand",
    "license": "LGPL-3",
    "depends": [
        "base",
        "l10n_th",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}
