from odoo import models


class PaymentVoucherReport(models.AbstractModel):
    _name = "report.od19_accounting_payment_voucher_reports.payment_voucher"
    _description = "Payment Voucher Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["account.payment"].browse(docids)
        return {
            "doc_ids": docs.ids,
            "doc_model": "account.payment",
            "docs": docs,
        }
