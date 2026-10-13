# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ReportChequePrint(models.AbstractModel):
    _name = "report.od19_accounting_cheque.cheque_print"
    _description = "Cheque Print Report"

    def _get_report_values(self, docids, data=None):
        docs = self.env["account.cheque"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "account.cheque",
            "docs": docs,
            "data": data,
        }
