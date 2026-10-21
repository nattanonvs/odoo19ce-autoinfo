# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Accounting - Payment Voucher & Receipt Reports",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "Thai payment voucher (ใบสำคัญจ่าย) and payment receipt (ใบสำคัญรับเงิน) QWeb reports with Thai document numbers",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "account",
        "od19_thai_font_support",
        "od19_accounting_document_sequence",
    ],
    "data": [
        "views/account_payment_views.xml",
        "report/payment_voucher_report.xml",
    ],
    "installable": True,
    "application": False,
}
