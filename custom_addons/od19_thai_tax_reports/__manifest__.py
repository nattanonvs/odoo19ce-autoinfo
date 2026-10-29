# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Thai Tax Reports",
    "version": "19.0.1.9.0",
    "category": "Localization",
    "summary": "Thai tax reports: VAT Sales/Purchase Register, WHT Register, "
    "WHT Certificate (หนังสือรับรองการหักภาษี ณ ที่จ่าย), PND54 Register, "
    "PND50/PND51 Register (ภาษีเงินได้นิติบุคคล), "
    "Deferred Tax Worksheet (TAS 12 ภาษีเงินได้รอตัดบัญชี), "
    "e-Withholding Tax submission",
    "author": "Custom",
    "website": "https://github.com/OCA/l10n-thailand",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
        "l10n_th_account_tax",
        "od19_partner_thai_fields",
        "od19_accounting_dncn",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/od19_vat_non_deductible_data.xml",
        "data/od19_reverse_charge_data.xml",
        "wizard/tax_report_wizard_views.xml",
        "report/vat_sales_register.xml",
        "report/vat_purchase_register.xml",
        "report/wht_register.xml",
        "report/wht_certificate.xml",
        "report/pp36_register.xml",
        "report/pnd54_register.xml",
        "report/pnd50_register.xml",
        "report/pnd51_register.xml",
        "report/tax_invoice_forms.xml",
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "views/ewht_submission_views.xml",
        "views/deferred_tax_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
}
