# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "OD19 Payment Pull",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Accounting/Payments",
    "summary": "Pull open vendor bills and customer invoices into payment "
    "vouchers through a wizard, one draft voucher per partner.",
    "license": "LGPL-3",
    "depends": [
        "account",
        "od19_accounting_payment_voucher_reports",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/od19_payment_pull_views.xml",
    ],
    "installable": True,
    "application": False,
}
