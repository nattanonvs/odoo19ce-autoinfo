# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


WHT_RATE_SELECTION = [
    ("1", "1%"),
    ("1.5", "1.5%"),
    ("2", "2%"),
    ("3", "3%"),
    ("5", "5%"),
]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ------------------------------------------------------------------
    # Feature 2: Payer / Payee (also available on payments)
    # ------------------------------------------------------------------
    od19_payer_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้จ่ายเงิน / Payer",
        help="Partner who actually pays.",
    )
    od19_payee_id = fields.Many2one(
        comodel_name="res.partner",
        string="ผู้รับเงิน / Payee",
        help="Partner who actually receives the payment.",
    )

    # ------------------------------------------------------------------
    # Receipt document type (inbound): drives the document number series
    # ------------------------------------------------------------------
    od19_receipt_doc_type = fields.Selection(
        selection=[
            ("tax_invoice", "ใบกำกับภาษี / Tax Invoice"),
            ("receipt", "ใบรับเงิน / Receipt"),
        ],
        string="ประเภทการเปิดเอกสาร / Receipt document type",
        help="เลือกประเภทการเปิดเอกสารรับชำระ เพื่อกำหนดชุดเลขที่เอกสาร "
        "(ใบรับเงิน RE… / ใบกำกับภาษี TI…). ฝั่งจ่ายชำระไม่ใช้ฟิลด์นี้",
    )

    # ------------------------------------------------------------------
    # Feature 6: WHT base computed from selected invoices
    # ------------------------------------------------------------------
    od19_wht_invoice_base_amount = fields.Monetary(
        string="WHT Base Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_invoice_base_amount",
        store=True,
        help="Sum of the untaxed amounts of the invoices reconciled "
        "with this payment.",
    )
    od19_wht_rate = fields.Selection(
        selection=WHT_RATE_SELECTION,
        string="WHT Rate",
        default="1",
        help="Withholding tax rate applied to the base amount.",
    )
    od19_wht_type_id = fields.Many2one(
        comodel_name="account.withholding.tax",
        string="WHT Type",
        help="Withholding tax type (OCA l10n_th_account_tax).",
    )
    od19_wht_invoice_amount = fields.Monetary(
        string="WHT Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_invoice_amount",
        store=True,
        help="Withholding tax amount = base amount x rate.",
    )

    # ------------------------------------------------------------------
    # Payment receipt totals, exchange rate and tax detail lines
    # (R5, R6/R7 detail, K4/K5/K9)
    # ------------------------------------------------------------------
    od19_exchange_rate = fields.Float(
        string="อัตราแลกเปลี่ยน / Exchange Rate",
        digits=(12, 6),
        compute="_compute_od19_exchange_rate",
        store=True,
        readonly=False,
        precompute=True,
        help="อัตราแลกเปลี่ยนเทียบสกุลเอกสารเป็นสกุลบริษัท ใช้แปลงยอดไปเป็น "
        "ยอดในบัญชี (balance) ตอน Post. ค่าเริ่มต้นดึงจากอัตราของบริษัท ณ "
        "วันชำระ และแก้ไขได้ (มติ K5).",
    )
    od19_wht_line_ids = fields.One2many(
        comodel_name="od19.payment.wht.line",
        inverse_name="payment_id",
        string="บรรทัดหัก ณ ที่จ่าย / WHT lines",
        copy=True,
    )
    od19_vat_line_ids = fields.One2many(
        comodel_name="od19.payment.vat.line",
        inverse_name="payment_id",
        string="บรรทัดภาษีมูลค่าเพิ่ม / VAT lines",
        copy=True,
    )
    od19_wht_amount = fields.Monetary(
        string="ยอดหัก ณ ที่จ่าย / WHT Amount",
        currency_field="currency_id",
        compute="_compute_od19_wht_amount",
        store=True,
        help="ผลรวมยอดหัก ณ ที่จ่ายจาก od19_wht_line_ids "
        "(ถ้าไม่มีบรรทัด ใช้ค่าเดิม od19_wht_invoice_amount).",
    )
    od19_vat_amount = fields.Monetary(
        string="ยอดภาษีมูลค่าเพิ่ม / VAT Amount",
        currency_field="currency_id",
        compute="_compute_od19_vat_amount",
        store=True,
        help="ผลรวมภาษีมูลค่าเพิ่มจาก od19_vat_line_ids.",
    )
    od19_amount_net = fields.Monetary(
        string="ยอดรับสุทธิ / Net Received",
        currency_field="currency_id",
        compute="_compute_od19_amount_net",
        store=True,
        help="ยอดรับ/จ่ายสุทธิ = amount − WHT − Fees. "
        "VAT ไม่หักออกจากยอดรับ (มติ K9).",
    )

    @api.depends(
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
        "reconciled_invoice_ids.amount_untaxed",
        "reconciled_bill_ids.amount_untaxed",
    )
    def _compute_od19_wht_invoice_base_amount(self):
        for payment in self:
            invoices = payment.reconciled_invoice_ids | payment.reconciled_bill_ids
            if not invoices:
                # Fallback: lines tagged with WHT on the payment move.
                wht_lines = payment.move_id.line_ids.filtered("wht_tax_id")
                base = 0.0
                for line in wht_lines:
                    base += abs(line.balance)
                payment.od19_wht_invoice_base_amount = base
            else:
                payment.od19_wht_invoice_base_amount = sum(
                    invoices.mapped("amount_untaxed")
                )

    @api.depends("od19_wht_invoice_base_amount", "od19_wht_rate")
    def _compute_od19_wht_invoice_amount(self):
        for payment in self:
            try:
                rate = float(payment.od19_wht_rate or 0.0)
            except (TypeError, ValueError):
                rate = 0.0
            payment.od19_wht_invoice_amount = (
                payment.od19_wht_invoice_base_amount * rate / 100.0
            )

    @api.depends("currency_id", "company_id", "date")
    def _compute_od19_exchange_rate(self):
        for payment in self:
            currency = payment.currency_id
            company_currency = payment.company_id.currency_id
            if not currency or not company_currency or currency == company_currency:
                payment.od19_exchange_rate = 1.0
                continue
            payment.od19_exchange_rate = currency._get_conversion_rate(
                currency, company_currency, payment.company_id, payment.date
            ) or 1.0

    @api.depends("od19_wht_line_ids.wht_amount", "od19_wht_invoice_amount")
    def _compute_od19_wht_amount(self):
        for payment in self:
            if payment.od19_wht_line_ids:
                payment.od19_wht_amount = sum(
                    payment.od19_wht_line_ids.mapped("wht_amount")
                )
            else:
                payment.od19_wht_amount = payment.od19_wht_invoice_amount

    @api.depends("od19_vat_line_ids.vat_amount")
    def _compute_od19_vat_amount(self):
        for payment in self:
            payment.od19_vat_amount = sum(
                payment.od19_vat_line_ids.mapped("vat_amount")
            )

    @api.depends("amount", "od19_wht_amount")
    def _compute_od19_amount_net(self):
        # Fee is subtracted by the fee module (the field lives there).
        for payment in self:
            payment.od19_amount_net = payment.amount - payment.od19_wht_amount

    # ------------------------------------------------------------------
    # Journal preparation helpers (WHT lines + manual exchange rate)
    # ------------------------------------------------------------------
    def _od19_convert_amount(self, amount_currency):
        """Convert an amount in the payment currency to the company currency.

        Applies the manual exchange rate (K5) when set, otherwise the standard
        company rate for the payment date.
        """
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if self.currency_id == company_currency:
            return company_currency.round(amount_currency)
        if self.od19_exchange_rate:
            return company_currency.round(amount_currency * self.od19_exchange_rate)
        return self.currency_id._convert(
            amount_currency, company_currency, self.company_id, self.date
        )

    def _od19_get_wht_move_lines(self):
        """WHT journal items: one line per WHT detail line, on its WHT account.

        Inbound: the customer withholds tax on our behalf, so we debit the WHT
        receivable (positive balance). Outbound: we withhold from the vendor,
        so we credit the WHT payable (negative balance).
        """
        self.ensure_one()
        sign = 1.0 if self.payment_type == "inbound" else -1.0
        lines = []
        for line in self.od19_wht_line_ids:
            if not line.account_id or not line.wht_amount:
                continue
            amount_currency = sign * line.wht_amount
            lines.append({
                "name": _("WHT: %s") % (line.tax_id.name or ""),
                "date_maturity": self.date,
                "partner_id": self.partner_id.id,
                "account_id": line.account_id.id,
                "currency_id": self.currency_id.id,
                "balance": self._od19_convert_amount(amount_currency),
                "amount_currency": amount_currency,
            })
        # Fallback: the legacy single-field WHT when no detail line is set.
        if not lines and self.od19_wht_invoice_amount and self.od19_wht_type_id:
            account = self.od19_wht_type_id.account_id
            if account:
                amount_currency = sign * self.od19_wht_invoice_amount
                lines.append({
                    "name": _("WHT: %s") % (self.od19_wht_type_id.name or ""),
                    "date_maturity": self.date,
                    "partner_id": self.partner_id.id,
                    "account_id": account.id,
                    "currency_id": self.currency_id.id,
                    "balance": self._od19_convert_amount(amount_currency),
                    "amount_currency": amount_currency,
                })
        return lines

    def _prepare_move_withholding_lines(self, default_values):
        # EXTENDS 'account'
        res = super()._prepare_move_withholding_lines(default_values)
        return res + self._od19_get_wht_move_lines()

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        # EXTENDS 'account' — apply the manual exchange rate (K5) to the
        # whole entry: every line keeps its amount_currency, only the company
        # currency balance is recomputed, so the entry stays balanced.
        line_vals = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )
        if (
            not self.od19_exchange_rate
            or self.currency_id == self.company_id.currency_id
            or write_off_line_vals
            or force_balance is not None
        ):
            return line_vals
        company_currency = self.company_id.currency_id
        for vals in line_vals:
            if vals.get("currency_id") and vals.get("amount_currency") is not None:
                vals["balance"] = company_currency.round(
                    vals["amount_currency"] * self.od19_exchange_rate
                )
        return line_vals

    # ------------------------------------------------------------------
    # Bill-first rule (AP / ฝั่งทำจ่าย): require ตั้งหนี้ before payment
    # ------------------------------------------------------------------
    def _od19_requires_vendor_bill(self):
        """AP bill-first rule applies to outbound payments (จ่ายชำระเจ้าหนี้)."""
        self.ensure_one()
        return (
            self.payment_type == "outbound"
            and self.company_id.od19_require_vendor_bill_for_payment
        )

    def _od19_is_expense_reimbursement(self):
        """Expense reimbursements paid to employees are out of the AP rule."""
        self.ensure_one()
        if "od19_is_expense_payment" not in self._fields:
            return False
        return bool(self.od19_is_expense_payment)

    def _od19_has_linked_vendor_bill(self):
        """True when the payment settles at least one Vendor Bill (ตั้งหนี้)."""
        self.ensure_one()
        bills = self.invoice_ids.filtered(
            lambda move: move.is_purchase_document(include_receipts=True)
        )
        if bills or self.reconciled_bill_ids:
            return True
        # Payments staged by the "Prepare payment" option of the Register
        # Payment wizard (``od19_accounting_payment_voucher_reports``) keep
        # their source document lines until they are posted, so the vendor bill
        # link is not materialised yet at posting time.
        if "od19_pending_reconcile_line_ids" in self._fields:
            staged_bills = self.od19_pending_reconcile_line_ids.move_id.filtered(
                lambda move: move.is_purchase_document(include_receipts=True)
            )
            if staged_bills:
                return True
        return False

    def _od19_check_vendor_bill_required(self):
        """Block outbound payments that are not linked to a Vendor Bill.

        ``od19_skip_vendor_bill_check`` is set by the "Register Payment" wizard,
        which always starts from an existing invoice/bill.
        """
        if self.env.context.get("od19_skip_vendor_bill_check"):
            return
        for payment in self:
            if not payment._od19_requires_vendor_bill():
                continue
            if payment._od19_is_expense_reimbursement():
                continue
            if payment._od19_has_linked_vendor_bill():
                continue
            raise UserError(
                _(
                    "ไม่สามารถยืนยันการจ่ายชำระได้ เนื่องจากไม่พบการตั้งหนี้ "
                    "(Vendor Bill)\n\n"
                    "การจ่ายชำระฝั่งเจ้าหนี้ต้องอ้างอิงใบแจ้งหนี้ของผู้ขายที่ "
                    "post แล้วเท่านั้น กรุณาใช้ปุ่ม \"ชำระเงิน\" (Register "
                    "Payment) จากใบแจ้งหนี้ผู้ขาย\n\n"
                    "Payment %(name)s (คู่ค้า: %(partner)s) ไม่ได้ผูกกับ "
                    "Vendor Bill",
                    name=payment.name or payment.display_name,
                    partner=payment.partner_id.display_name or "-",
                )
            )

    def action_post(self):
        self._od19_check_vendor_bill_required()
        return super().action_post()
