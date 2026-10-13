# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Thai Tax Reports",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "Thai tax reports: VAT Sales/Purchase Register, WHT Register",
    "author": "Custom",
    "website": "https://github.com/OCA/l10n-thailand",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_th_account_tax",
        "od19_partner_thai_fields",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/tax_report_wizard_views.xml",
        "report/vat_sales_register.xml",
        "report/vat_purchase_register.xml",
        "report/wht_register.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
