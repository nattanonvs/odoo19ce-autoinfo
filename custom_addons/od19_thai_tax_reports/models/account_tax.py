# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models

# กลุ่มภาษีของ ภ.พ.36 (ภาษีมูลค่าเพิ่มที่ผู้จ่ายเงินนำส่งแทนผู้รับเงินจากต่างประเทศ)
OD19_PP36_TAX_GROUP_XMLID = "od19_thai_tax_reports.tax_group_vat_pp36"

# ผังบัญชีมาตรฐาน l10n_th ที่ใช้ลงภาษีขาย / ภาษีซื้อ
OD19_PP36_OUTPUT_VAT = ("l10n_th_account_213200", "213200")  # ภาษีขาย
OD19_PP36_INPUT_VAT = ("l10n_th_account_114200", "114200")  # ภาษีซื้อ


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _od19_pp36_resolve_account(self, template_xmlid, code):
        """ค้นบัญชี VAT ของบริษัทจาก xmlid ของผังบัญชี l10n_th

        ถ้าไม่พบ xmlid (เช่นบริษัทลูกใช้ผังบัญชีร่วม) จะค้นจากรหัสบัญชีแทน
        """
        self.ensure_one()
        company = self.company_id or self.env.company
        account = self.env.ref(
            "account.%s_%s" % (company.id, template_xmlid),
            raise_if_not_found=False,
        )
        if not account:
            account = (
                self.env["account.account"]
                .with_company(company)
                .search(
                    [("code", "=", code), ("company_ids", "in", company.id)],
                    limit=1,
                )
            )
        return account

    def _od19_pp36_ensure_repartition(self):
        """จัดโครงสร้าง repartition line ของภาษี reverse charge (ม.83/6)

        โครงสร้างที่ถูกต้องคือ base (100) + tax (+100 -> บัญชีภาษีขาย)
        + tax (-100 -> บัญชีภาษีซื้อ) การมี line ที่ factor ติดลบทำให้ Odoo
        มองภาษีนี้เป็น reverse charge (has_negative_factor = True) และลง
        ภาษีขาย/ภาษีซื้อให้อัตโนมัติโดยไม่กระทบยอดรวมของเอกสาร
        """
        self.ensure_one()
        output_account = self._od19_pp36_resolve_account(*OD19_PP36_OUTPUT_VAT)
        input_account = self._od19_pp36_resolve_account(*OD19_PP36_INPUT_VAT)
        if not output_account or not input_account:
            # ยังไม่ติดตั้งผังบัญชีไทยของบริษัทนี้ ข้ามไปก่อน
            return

        RepLine = self.env["account.tax.repartition.line"]
        for field_name, document_type in (
            ("invoice_repartition_line_ids", "invoice"),
            ("refund_repartition_line_ids", "refund"),
        ):
            lines = self[field_name]
            lines.filtered(
                lambda line: line.repartition_type == "base"
            ).write({"tag_ids": [(5, 0, 0)]})

            tax_lines = lines.filtered(lambda line: line.repartition_type == "tax")
            positive = tax_lines.filtered(lambda line: line.factor_percent >= 0.0)[:1]
            if positive:
                positive.write(
                    {
                        "factor_percent": 100.0,
                        "account_id": output_account.id,
                        "tag_ids": [(5, 0, 0)],
                        "sequence": 1,
                    }
                )
            else:
                positive = RepLine.create(
                    {
                        "tax_id": self.id,
                        "document_type": document_type,
                        "repartition_type": "tax",
                        "factor_percent": 100.0,
                        "account_id": output_account.id,
                        "sequence": 1,
                    }
                )

            negative = tax_lines.filtered(lambda line: line.factor_percent < 0.0)[:1]
            if negative:
                negative.write(
                    {
                        "factor_percent": -100.0,
                        "account_id": input_account.id,
                        "tag_ids": [(5, 0, 0)],
                        "sequence": 2,
                    }
                )
            else:
                RepLine.create(
                    {
                        "tax_id": self.id,
                        "document_type": document_type,
                        "repartition_type": "tax",
                        "factor_percent": -100.0,
                        "account_id": input_account.id,
                        "sequence": 2,
                    }
                )

    @api.model
    def _od19_setup_reverse_charge_taxes(self):
        """Setup ภาษี ภ.พ.36 ให้พร้อมใช้ (เรียกจาก data file ตอน install/upgrade)"""
        tax_group = self.env.ref(OD19_PP36_TAX_GROUP_XMLID, raise_if_not_found=False)
        if not tax_group:
            return
        for tax in self.search([("tax_group_id", "=", tax_group.id)]):
            tax._od19_pp36_ensure_repartition()
