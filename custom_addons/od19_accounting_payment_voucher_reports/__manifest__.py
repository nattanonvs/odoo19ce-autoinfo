# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Accounting - Payment Voucher & Receipt Reports",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "QWeb reports for Payment Voucher and Payment Receipt",
    "author": "OD19",
    "license": "LGPL-3",
    "depends": [
        "account",
        "od19_partner_thai_fields",
    ],
    "data": [
        "data/ir_sequence_data.xml",
        "report/payment_voucher_report.xml",
        "report/payment_receipt_report.xml",
        "views/account_payment_views.xml",
    ],
    "installable": True,
    "application": False,
}
