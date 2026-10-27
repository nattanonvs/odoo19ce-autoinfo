# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class Pp36Register(models.AbstractModel):
    _name = "report.od19_thai_tax_reports.pp36_register"
    _description = "PP36 (VAT Self-Assessed) Register"

    def _get_report_values(self, docids, data=None):
        date_from = self.env.context.get("date_from")
        date_to = self.env.context.get("date_to")
        company_id = self.env.context.get("company_id")

        tax_group = self.env.ref(
            "od19_thai_tax_reports.tax_group_vat_pp36",
            raise_if_not_found=False,
        )

        domain = [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", date_from),
            ("invoice_date", "<=", date_to),
        ]
        if company_id:
            domain.append(("company_id", "=", company_id))

        moves = self.env["account.move"].search(domain, order="invoice_date, name")

        lines = []
        total_tax_base = 0.0
        total_vat_amount = 0.0

        for move in moves:
            # ภาษีที่ต้องนำส่ง (ด้านภาษีขาย) คือ repartition line ที่ factor เป็นบวก
            vat_amount = 0.0
            has_reverse_charge = False
            if tax_group:
                for tax_line in move.line_ids.filtered("tax_repartition_line_id"):
                    repartition = tax_line.tax_repartition_line_id
                    if (
                        repartition.tax_id.tax_group_id == tax_group
                        and repartition.factor_percent > 0.0
                    ):
                        has_reverse_charge = True
                        vat_amount += abs(tax_line.balance)

            if not has_reverse_charge:
                continue

            tax_base = abs(move.amount_untaxed_signed)

            lines.append(
                {
                    "invoice_date": move.invoice_date,
                    "name": move.name,
                    "ref": move.ref or "",
                    "partner_name": move.partner_id.name or "",
                    "partner_vat": move.partner_id.vat or "",
                    "tax_base": tax_base,
                    "vat_amount": vat_amount,
                }
            )
            total_tax_base += tax_base
            total_vat_amount += vat_amount

        return {
            "doc_ids": moves.ids,
            "doc_model": "account.move",
            "docs": moves,
            "date_from": date_from,
            "date_to": date_to,
            "company": self.env["res.company"].browse(company_id) if company_id else self.env.company,
            "lines": lines,
            "total_tax_base": total_tax_base,
            "total_vat_amount": total_vat_amount,
        }
