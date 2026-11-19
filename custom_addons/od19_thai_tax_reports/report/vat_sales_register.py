# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class VatSalesRegister(models.AbstractModel):
    _name = "report.od19_thai_tax_reports.vat_sales_register"
    _description = "VAT Sales Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        # ทะเบียนภาษีขายต้องรวม "ใบเพิ่มหนี้" (debit note = out_invoice ที่ dncn='dn')
        # และ "ใบลดหนี้" (credit note = out_refund) ไม่ใช่เฉพาะใบกำกับภาษีขาย
        domain = [
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("state", "=", "posted"),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        moves = self.env["account.move"].search(domain, order="invoice_date, name")

        lines = []
        total_tax_base = 0.0
        total_tax_amount = 0.0
        total_amount = 0.0

        doc_type_labels = {
            "dn": "ใบเพิ่มหนี้",
            "cn": "ใบลดหนี้",
            "re": "ใบแจ้งหนี้ใหม่",
        }

        for move in moves:
            # ใบลดหนี้ (out_refund) แสดงเป็นค่าลบเพื่อหักลบกับยอดขาย/ภาษีขาย
            sign = -1.0 if move.move_type == "out_refund" else 1.0
            tax_base = sign * abs(move.amount_untaxed_signed)
            tax_amount = sign * abs(move.amount_tax_signed)
            amount_total = sign * abs(move.amount_total_signed)

            if move.dncn == "cn" or move.move_type == "out_refund":
                doc_type = "ใบลดหนี้"
            else:
                doc_type = doc_type_labels.get(move.dncn, "ใบกำกับภาษีขาย")

            lines.append(
                {
                    "invoice_date": move.invoice_date,
                    "name": move.name,
                    "doc_type": doc_type,
                    "partner_name": move.partner_id.name or "",
                    "partner_vat": move.partner_id.vat or "",
                    "tax_base": tax_base,
                    "tax_amount": tax_amount,
                    "amount_total": amount_total,
                }
            )
            total_tax_base += tax_base
            total_tax_amount += tax_amount
            total_amount += amount_total

        return {
            "doc_ids": moves.ids,
            "doc_model": "account.move",
            "docs": moves,
            "date_from": date_from,
            "date_to": date_to,
            "company": self.env["res.company"].browse(company_id) if company_id else self.env.company,
            "lines": lines,
            "total_tax_base": total_tax_base,
            "total_tax_amount": total_tax_amount,
            "total_amount": total_amount,
        }
