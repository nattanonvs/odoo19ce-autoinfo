# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class Od19PaymentFeeLine(models.Model):
    _name = "od19.payment.fee.line"
    _description = "Payment Fee Line"
    _check_company_auto = True
    _inherit = ["analytic.mixin"]
    _order = "id"

    payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Payment",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="payment_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="payment_id.currency_id",
        store=True,
        readonly=True,
    )
    name = fields.Char(
        string="รายละเอียด / Description",
        required=True,
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        string="บัญชีค่าธรรมเนียม / Fee Account",
        required=True,
        ondelete="restrict",
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost'))]",
        check_company=True,
    )
    percent = fields.Float(
        string="เปอร์เซ็นต์ / Percent",
        digits=(5, 2),
        help="ระบุเปอร์เซ็นต์เพื่อคำนวณยอดค่าธรรมเนียมจากยอดรับสุทธิ "
        "ก่อนหักค่าธรรมเนียม (amount − WHT) ถ้าไม่ระบุจะใช้ยอดที่กรอกเอง",
    )
    amount = fields.Monetary(
        string="จำนวน / Amount",
        currency_field="currency_id",
        compute="_compute_amount",
        store=True,
        readonly=False,
        help="ยอดค่าธรรมเนียม คำนวณจากเปอร์เซ็นต์เมื่อระบุ ไม่เช่นนั้นกรอกเอง",
    )
    is_profit = fields.Boolean(
        string="เป็นรายได้ / Profit",
        help="เปิดเมื่อค่าธรรมเนียมนี้เป็นรายได้ที่บริษัทได้รับ (เช่น "
        "ค่าบริการเพิ่มที่เก็บจากลูกค้า) แทนที่จะเป็นค่าใช้จ่าย",
    )

    @api.depends(
        "percent",
        "payment_id.amount",
        "payment_id.od19_wht_amount",
        "payment_id.currency_id",
    )
    def _compute_amount(self):
        for line in self:
            if line.percent and line.payment_id:
                base = (line.payment_id.amount or 0.0) - (
                    line.payment_id.od19_wht_amount or 0.0
                )
                line.amount = line.currency_id.round(base * line.percent / 100.0)
