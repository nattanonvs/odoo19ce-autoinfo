# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class WhtRegister(models.AbstractModel):
    _name = "report.od19_thai_tax_reports.wht_register"
    _description = "WHT Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        domain = [
            ("state", "=", "posted"),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
            ("wht_amount", ">", 0),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        payments = self.env["account.payment"].search(domain, order="date, name")

        lines = []
        total_base = 0.0
        total_wht = 0.0

        for payment in payments:
            base = payment.wht_base_amount or 0.0
            wht = payment.wht_amount or 0.0
            lines.append(
                {
                    "date": payment.date,
                    "name": payment.name,
                    "partner_name": payment.partner_id.name or "",
                    "partner_vat": payment.partner_id.vat or "",
                    "wht_type": payment.wht_type_id.name or "",
                    "wht_percent": payment.wht_type_id.percent if payment.wht_type_id else 0.0,
                    "base_amount": base,
                    "wht_amount": wht,
                }
            )
            total_base += base
            total_wht += wht

        return {
            "doc_ids": payments.ids,
            "doc_model": "account.payment",
            "docs": payments,
            "date_from": date_from,
            "date_to": date_to,
            "company": self.env["res.company"].browse(company_id) if company_id else self.env.company,
            "lines": lines,
            "total_base": total_base,
            "total_wht": total_wht,
        }
