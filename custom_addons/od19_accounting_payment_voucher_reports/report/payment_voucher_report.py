# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ReportPaymentVoucher(models.AbstractModel):
    _name = "report.od19_accounting_payment_voucher_reports.payment_voucher_document"
    _description = "Payment Voucher Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["account.payment"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "account.payment",
            "docs": docs,
            "data": data,
        }


class ReportPaymentReceipt(models.AbstractModel):
    _name = "report.od19_accounting_payment_voucher_reports.payment_receipt_document"
    _description = "Payment Receipt Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["account.payment"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "account.payment",
            "docs": docs,
            "data": data,
        }
