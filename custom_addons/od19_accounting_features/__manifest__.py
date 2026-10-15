# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Accounting Features",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Accounting/Localizations",
    "summary": "Cancel reason wizard, payer/payee, BOT URL, prepayment due date, "
    "payment number, WHT base computed, and WHT PDF reports",
    "description": """
OD19 Accounting Features
========================

Provides several accounting features for the Thai localization:

* Cancel reason wizard on invoices (all move types).
* Payer / Payee partner fields on prepayments.
* BOT (Revenue Department) URL configuration with a smart link on invoices.
* Prepayment actual due date (invoice date + 30 days).
* Payment number displayed on vendor bills.
* Withholding tax (WHT) base amount computed from selected invoices.
* Thai WHT PDF reports: ภงด.1 (PND1), ภงด.3 (PND3),
  ภงด.53 (PND53) and ภงด.53 ทริส (PND53 Tris).
    """,
    "depends": [
        "account",
        "account_payment",
        "mail",
        "l10n_th_account_tax",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/account_move_cancel_reason_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "report/wht_report_templates.xml",
        "report/wht_report_actions.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
