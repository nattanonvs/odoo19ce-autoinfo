# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError

# Context key used to skip the Section 86/4 check (migrations, data imports,
# speed imports). e.g. env["account.move"].with_context(od19_skip_86_4_validation=True)
OD19_SKIP_86_4_CONTEXT = "od19_skip_86_4_validation"

# Thai legal document types carried by a customer document.
OD19_TAX_DOC_TYPE_SELECTION = [
    ("full", "ใบกำกับภาษีเต็มรูป (ม.86/4)"),
    ("abbreviated", "ใบกำกับภาษีอย่างย่อ (ม.86/6)"),
    ("debit_note", "ใบเพิ่มหนี้ (ม.86/9)"),
    ("credit_note", "ใบลดหนี้ (ม.86/10)"),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_tax_invoice_doc_type = fields.Selection(
        selection=OD19_TAX_DOC_TYPE_SELECTION,
        string="ประเภทเอกสารทางภาษี",
        compute="_compute_od19_tax_invoice_doc_type",
    )

    @api.depends("move_type", "dncn", "partner_id.vat")
    def _compute_od19_tax_invoice_doc_type(self):
        for move in self:
            move.od19_tax_invoice_doc_type = move._od19_get_tax_invoice_doc_type()

    def _od19_get_tax_invoice_doc_type(self):
        """Return the Thai legal document type (ม.86) for this entry."""
        self.ensure_one()
        if self.dncn == "dn":
            return "debit_note"
        if self.dncn == "cn" or self.move_type == "out_refund":
            return "credit_note"
        if self.move_type == "out_invoice":
            # A VAT-registered buyer must receive a full-form tax invoice,
            # otherwise the abbreviated form (ม.86/6) is allowed.
            return "full" if self.partner_id.vat else "abbreviated"
        return False

    # ------------------------------------------------------------------
    # Section 86/4 - Full-form tax invoice required particulars (8 items)
    # ------------------------------------------------------------------
    # A "full-form" tax invoice (ใบกำกับภาษีเต็มรูป) must be issued when the
    # buyer is a VAT-registered operator (has a Thai tax ID). Retail sales to
    # consumers may use the abbreviated form instead (Section 86/6).
    def _od19_has_sale_vat(self):
        self.ensure_one()
        return bool(
            self.line_ids.filtered(
                lambda line: line.tax_line_id
                and line.tax_line_id.type_tax_use == "sale"
            )
        )

    def _od19_requires_full_tax_invoice(self):
        """True when this move must carry a full-form tax invoice."""
        self.ensure_one()
        if not self.company_id.od19_enforce_86_4_validation:
            return False
        if self.move_type not in ("out_invoice", "out_refund"):
            return False
        # The buyer is a VAT-registered operator -> full-form tax invoice.
        if not self.partner_id.vat:
            return False
        return self._od19_has_sale_vat()

    def _od19_tax_invoice_missing_items(self):
        """Return the list of missing particulars (labels) per Section 86/4."""
        self.ensure_one()
        missing = []
        seller = self.company_id.partner_id
        buyer = self.partner_id

        # (1) คำว่า "ใบกำกับภาษี" — มาจากเทมเพลตรายงานใบกำกับภาษีของ l10n_th
        if not self.env.ref(
            "l10n_th.report_invoice_document", raise_if_not_found=False
        ):
            missing.append("(1) ไม่พบเทมเพลตรายงาน 'ใบกำกับภาษี' (Tax Invoice)")

        # (2) ชื่อ ที่อยู่ และเลขประจำตัวผู้เสียภาษีของผู้ขาย
        if not (seller.name and seller.street and seller.vat):
            missing.append(
                "(2) ชื่อ/ที่อยู่/เลขประจำตัวผู้เสียภาษีของผู้ขาย ไม่ครบถ้วน"
            )

        # (3) ชื่อ ที่อยู่ และเลขประจำตัวผู้เสียภาษีของผู้ซื้อ
        if not (buyer.name and buyer.street and buyer.vat):
            missing.append(
                "(3) ชื่อ/ที่อยู่/เลขประจำตัวผู้เสียภาษีของผู้ซื้อ ไม่ครบถ้วน"
            )

        # (4) หมายเลขลำดับของใบกำกับภาษี
        tax_number = self.tax_invoice_ids.filtered("tax_invoice_number")[:1]
        if not tax_number and self.name in (False, "/"):
            missing.append("(4) ไม่พบหมายเลขลำดับของใบกำกับภาษี")

        # (5) ชื่อ ชนิด ประเภท ปริมาณ และมูลค่าของสินค้าหรือบริการ
        incomplete_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and (not line.name or not line.quantity)
        )
        if incomplete_lines:
            missing.append(
                "(5) รายการสินค้า/บริการ ขาดชื่อ หรือปริมาณ "
                "(บรรทัดที่ %s)" % ", ".join(str(i) for i in range(1, len(incomplete_lines) + 1))
            )

        # (6) จำนวนภาษีมูลค่าเพิ่ม แยกออกจากมูลค่าสินค้าให้เห็นชัดเจน
        if not self._od19_has_sale_vat():
            missing.append("(6) ไม่พบจำนวนภาษีมูลค่าเพิ่มที่แสดงแยกต่างหาก")

        # (7) วัน เดือน ปี ที่ออกใบกำกับภาษี
        if not self.invoice_date:
            missing.append("(7) ไม่พบวัน เดือน ปี ที่ออกใบกำกับภาษี")

        # (8) ข้อความอื่นตามประกาศอธิบดี — เลขสาขาของผู้ขาย/ผู้ซื้อ
        if not (seller.l10n_th_branch_name or seller.company_registry):
            missing.append("(8) ไม่พบเลขสาขาของผู้ขาย ตามประกาศอธิบดี")
        if buyer.is_company and not (
            buyer.l10n_th_branch_name or buyer.company_registry
        ):
            missing.append("(8) ไม่พบเลขสาขาของผู้ซื้อ ตามประกาศอธิบดี")

        return missing

    def _od19_validate_tax_invoice_86_4(self):
        """Raise a UserError listing every missing Section 86/4 particular."""
        for move in self:
            if not move._od19_requires_full_tax_invoice():
                continue
            missing = move._od19_tax_invoice_missing_items()
            if missing:
                raise UserError(
                    self.env._(
                        "ไม่สามารถออกใบกำกับภาษีเต็มรูป %(name)s ได้ "
                        "เนื่องจากขาดรายการตามมาตรา 86/4:\n- %(items)s",
                        name=move.name,
                        items="\n- ".join(missing),
                    )
                )

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        if not self.env.context.get(OD19_SKIP_86_4_CONTEXT):
            self._od19_validate_tax_invoice_86_4()
        return res
