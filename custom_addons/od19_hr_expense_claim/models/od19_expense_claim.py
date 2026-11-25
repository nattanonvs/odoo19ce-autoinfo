# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Od19ExpenseClaim(models.Model):
    """ใบเบิกค่าใช้จ่าย (หัวใบ) — รวมบรรทัด ``hr.expense`` หลายรายการ.

    การอนุมัติ 3 ชั้นทำที่หัวใบครั้งเดียว (ผ่าน OCA ``tier.validation``)
    เมื่ออนุมัติครบจะ propagate ``approval_state='approved'`` ลงทุกบรรทัด
    เพื่อให้ core ``hr.expense`` โพสต์บัญชีได้ตามปกติ
    """

    _name = "od19.expense.claim"
    _description = "Expense Claim / ใบเบิกค่าใช้จ่าย"
    _inherit = ["mail.thread", "mail.activity.mixin", "tier.validation"]
    _order = "date desc, id desc"

    # OCA tier.validation — อนุมัติ 3 ชั้นที่หัวใบ
    # ``_state_from=['submitted']`` -> ต้องส่ง (submitted) ก่อนจึงขอ validation
    # ``_state_to=['approved']``   -> validate ครบแล้วเปลี่ยนเป็น approved ได้
    # ``_cancel_state='refused'``  -> ปฏิเสธแล้วล้าง review อัตโนมัติ
    _state_field = "state"
    _state_from = ["submitted"]
    _state_to = ["approved"]
    _cancel_state = "refused"
    _tier_validation_manual_config = False

    name = fields.Char(
        string="Claim Number", default="/", readonly=True, copy=False, index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department", string="Department",
        related="employee_id.department_id", store=True, readonly=True,
    )
    company_id = fields.Many2one(
        "res.company", string="Company", required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string="Claim Date", required=True,
        default=fields.Date.context_today, tracking=True,
    )
    submit_date = fields.Datetime(string="Submitted On", readonly=True, copy=False)
    approval_date = fields.Datetime(string="Approved On", readonly=True, copy=False)
    transfer_date = fields.Datetime(
        string="Sent to Accounting On", readonly=True, copy=False,
        help="เวลาที่พนักงานยืนยันส่งใบเบิกให้ฝ่ายบัญชี (รอยต่อ approved -> sent)")
    line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="Expense Lines",
    )
    total_amount = fields.Monetary(
        string="Total", currency_field="currency_id",
        compute="_compute_total_amount", store=True,
    )
    payment_mode = fields.Selection(
        [("own_account", "Employee (to reimburse)"),
         ("company_account", "Company")],
        string="Paid By", default="own_account", required=True, tracking=True,
    )
    state = fields.Selection(
        [("draft", "Draft"),
         ("submitted", "Submitted"),
         ("approved", "Approved"),
         ("sent", "Sent to Accounting"),
         ("posted", "Posted"),
         ("paid", "Paid"),
         ("refused", "Refused")],
        string="Status", default="draft", tracking=True, copy=False,
    )
    note = fields.Text(string="Notes")

    # ------------------------------------------------------------------
    # Compute / create
    # ------------------------------------------------------------------
    @api.depends("line_ids.total_amount")
    def _compute_total_amount(self):
        for claim in self:
            claim.total_amount = sum(claim.line_ids.mapped("total_amount"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("od19.expense.claim") or "/"
                )
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains("line_ids")
    def _check_single_payment_mode(self):
        for claim in self:
            modes = set(claim.line_ids.mapped("payment_mode"))
            if len(modes) > 1:
                raise ValidationError(
                    _("ทุกบรรทัดในใบเบิกต้องใช้วิธีจ่าย (Paid By) เดียวกัน")
                )

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        """ส่งใบเบิกเพื่อขออนุมัติ 3 ชั้นที่หัวใบ."""
        for claim in self:
            if claim.state != "draft":
                raise UserError(_("ส่งได้เฉพาะใบเบิกที่เป็นฉบับร่าง"))
            if not claim.line_ids:
                raise UserError(_("ใบเบิกต้องมีอย่างน้อย 1 บรรทัด"))
            missing_analytic = claim.line_ids.filtered(
                lambda line: not line.analytic_distribution)
            if missing_analytic:
                raise UserError(_(
                    "ต้องระบุ Analytic Account ให้ครบทุกรายการก่อนส่งอนุมัติ "
                    "(ขาด %s รายการ)", len(missing_analytic)))
            claim.line_ids.write({"approval_state": "submitted"})
            claim.write({
                "state": "submitted",
                "submit_date": fields.Datetime.now(),
            })
            claim.invalidate_recordset(["need_validation"])
            if claim.need_validation:
                claim.request_validation()
        return True

    def action_refuse(self):
        """ปฏิเสธใบเบิก -> บรรทัดทุกตัวถูกปฏิเสธ (review ล้างอัตโนมัติ)."""
        for claim in self:
            if claim.state in ("posted", "paid"):
                raise UserError(_("ไม่สามารถปฏิเสธใบเบิกที่โพสต์/จ่ายแล้ว"))
            claim.line_ids.write({"approval_state": "refused"})
            claim.write({"state": "refused"})
        return True

    def action_reset(self):
        """ดึงใบเบิกที่ถูกปฏิเสธกลับเป็นฉบับร่างเพื่อแก้ไข/ส่งใหม่."""
        for claim in self:
            if claim.state != "refused":
                raise UserError(_("ดึงกลับได้เฉพาะใบเบิกที่ถูกปฏิเสธ"))
            claim.line_ids.write({"approval_state": False})
            claim.write({
                "state": "draft",
                "submit_date": False,
                "approval_date": False,
            })
        return True

    def action_send_to_accounting(self):
        """รอยต่อ: พนักงานยืนยันส่งใบเบิกที่อนุมัติแล้วให้ฝ่ายบัญชี (approved -> sent).

        พนักงานเป็นผู้กดยืนยันว่าพร้อมให้บัญชีจ่ายคืน หลังจากนี้ฝ่ายบัญชี
        จะเป็นผู้บันทึกบัญชีและจัดสรรเงินคืนให้พนักงานเอง
        """
        for claim in self:
            if claim.state != "approved":
                raise UserError(_(
                    "ยืนยันส่งบัญชีได้เฉพาะใบเบิกที่อนุมัติครบแล้ว"))
            claim.write({
                "state": "sent",
                "transfer_date": fields.Datetime.now(),
            })
            claim.message_post(body=_(
                "พนักงานยืนยันส่งใบเบิกให้ฝ่ายบัญชีแล้ว — รอฝ่ายบัญชีบันทึกบัญชีและจ่ายคืน"))
        return True

    def action_post(self):
        """บันทึกบัญชีที่บรรทัด (กลไก core เดิม) — เฉพาะฝ่ายบัญชีเท่านั้น."""
        self.ensure_one()
        if not self.env.user.has_group("account.group_account_manager"):
            raise UserError(_(
                "การบันทึกบัญชี (Post) เป็นหน้าที่ของฝ่ายบัญชีเท่านั้น"))
        if self.state != "sent":
            raise UserError(_(
                "บันทึกบัญชีได้เฉพาะใบเบิกที่พนักงานยืนยันส่งบัญชีแล้ว (สถานะ ส่งบัญชีแล้ว)"))
        lines = self.line_ids
        # core action_post() คืน wizard (ไม่โพสต์ทันที) สำหรับบรรทัดที่พนักงานออกเงินเอง
        # จึงเรียก _post_without_wizard() เพื่อโพสต์จากหัวใบแบบ headless
        employee_lines = lines.filtered(lambda l: l.payment_mode == "own_account")
        company_lines = lines - employee_lines
        if employee_lines:
            employee_lines._post_without_wizard()
        if company_lines:
            company_lines.action_post()
        self.state = "posted"
        return True

    # ------------------------------------------------------------------
    # Tier validation hook — propagate ลงบรรทัดเมื่ออนุมัติครบ
    # ------------------------------------------------------------------
    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers=tiers)
        for claim in self:
            claim.invalidate_recordset(["validation_status"])
            if claim.validation_status == "validated" and claim.state == "submitted":
                claim._od19_on_validation_complete()
        return res

    def _od19_on_validation_complete(self):
        """หัวใบอนุมัติครบ -> ตั้ง approved + propagate ลงทุกบรรทัด (K5)."""
        self.ensure_one()
        self.write({
            "state": "approved",
            "approval_date": fields.Datetime.now(),
        })
        # propagate ด้วย sudo — ผู้อนุมัติชั้นสุดท้าย (เช่น CEO) อาจไม่มีสิทธิ์อ่านบรรทัด hr.expense
        # ต้อง sudo() ที่ self ก่อนอ่าน line_ids มิฉะนั้น line_ids จะถูกกรองด้วยสิทธิ์ของผู้อนุมัติ
        self.sudo().line_ids.write({"approval_state": "approved"})
