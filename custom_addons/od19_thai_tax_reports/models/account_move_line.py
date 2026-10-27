# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    # ------------------------------------------------------------------
    # Section 82/5 - Non-deductible input VAT (ภาษีซื้อต้องห้าม)
    # ------------------------------------------------------------------
    # The flag follows the tax applied on the line: when the line carries
    # the "VAT 7% (Non-Deductible)" tax (see data/od19_vat_non_deductible
    # _data.xml) the input VAT cannot be claimed against output VAT and
    # must be included in the expense/cost instead.
    od19_vat_deductible = fields.Boolean(
        string="ภาษีซื้อหักได้ / VAT Deductible",
        compute="_compute_od19_vat_deductible",
        store=True,
        readonly=False,
        tracking=True,
        help="Untick when the input VAT on this line is not deductible "
        "(Section 82/5 of the Thai Revenue Code), e.g. entertainment, "
        "passenger cars with fewer than 10 seats, or private expenses.\n"
        "ภาษีซื้อต้องห้ามไม่สามารถขอคืน/หักลบกับภาษีขายได้ ต้องบันทึกเป็น "
        "ต้นทุน/ค่าใช้จ่ายของกิจการ",
    )

    @api.depends("tax_ids", "tax_line_id")
    def _compute_od19_vat_deductible(self):
        non_deductible_group = self.env.ref(
            "od19_thai_tax_reports.tax_group_vat_non_deductible",
            raise_if_not_found=False,
        )
        for line in self:
            if not non_deductible_group:
                line.od19_vat_deductible = True
                continue
            taxes = line.tax_ids | line.tax_line_id
            line.od19_vat_deductible = (
                non_deductible_group not in taxes.tax_group_id
            )

    @api.onchange("od19_vat_deductible")
    def _onchange_od19_vat_deductible(self):
        """Swap the input VAT tax between the deductible and non-deductible
        variant so the accounting entry stays in line with the flag."""
        non_deductible_tax = self.env.ref(
            "od19_thai_tax_reports.tax_input_vat_non_deductible",
            raise_if_not_found=False,
        )
        if not non_deductible_tax:
            return
        for line in self:
            company = line.move_id.company_id or line.company_id or self.env.company
            # The standard deductible input VAT is the company's default
            # purchase tax (set by the Thai localization).
            standard_tax = company.account_purchase_tax_id
            # Drop any 7% purchase VAT currently present so the correct
            # variant is applied below whatever the previous state was.
            vat_taxes = line.tax_ids.filtered(
                lambda tax: tax.type_tax_use == "purchase"
                and tax.amount_type == "percent"
                and tax.amount == non_deductible_tax.amount
            )
            target = standard_tax if line.od19_vat_deductible else non_deductible_tax
            line.tax_ids = (line.tax_ids - vat_taxes) | target
