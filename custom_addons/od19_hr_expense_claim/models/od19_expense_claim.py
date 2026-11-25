# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Od19ExpenseClaim(models.Model):
    """ใบเบิกค่าใช้จ่าย (หัวใบ) — รวมบรรทัด ``hr.expense`` หลายรายการ.

    การอนุมัติ 3 ชั้นทำที่หัวใบครั้งเดียว (ผ่าน OCA ``tier.validation``)
    เมื่ออนุมัติครบจะ propagate ``approval_state='approved'`` ลงทุกบรรทัด
    เพื่อให้ core ``hr.expense`` โพสต์บัญชีได้ตามปกติ

    P2: หัวใบนี้เป็น **จุดเดียว** ของทุกเรื่องเงิน-พนักงาน — แยก ``claim_type``
    เป็น ขอเบิกคืน (``reimbursement``) / ขอเงินทดรอง (``advance``) /
    เงินสดย่อย (``petty_cash``) และติดตาม "วงเงินที่พนักงานถืออยู่" (``cash_state``)
    ที่หัวใบเดียว (ยุบแนวคิดจาก ``od19.hr.advance`` + ``od19_cash_state``)
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
    partner_id = fields.Many2one(
        "res.partner", string="Employee Contact",
        compute="_compute_partner_id", store=True, readonly=True,
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

    # ------------------------------------------------------------------
    # P2 — ประเภท/แหล่งที่มาของใบ (จุดเดียวของทุกเรื่องเงิน-พนักงาน)
    # ------------------------------------------------------------------
    claim_type = fields.Selection(
        [("reimbursement", "Reimbursement / เบิกคืน"),
         ("advance", "Cash Advance / เงินทดรอง"),
         ("petty_cash", "Petty Cash / เงินสดย่อย")],
        string="Claim Type", default="reimbursement", required=True, tracking=True,
    )
    claim_source = fields.Selection(
        [("self_service", "Employee (Self Service)"),
         ("on_behalf", "Accounting (On Behalf)")],
        string="Source", default="self_service", required=True, tracking=True,
    )
    submitted_for_id = fields.Many2one(
        "hr.employee", string="Submitted For",
        help="พนักงานที่เบิกแทน (เมื่อฝ่ายบัญชีทำใบแทนให้)",
    )
    purpose = fields.Char(
        string="Purpose",
        help="วัตถุประสงค์ของการขอเงินทดรอง (จำเป็นเมื่อ claim_type=advance)",
    )
    cash_fund_id = fields.Many2one(
        "account.journal", string="Petty Cash Fund",
        domain="[('type', '=', 'cash')]",
        help="กองทุนเงินสดย่อยที่จ่ายเงิน (เมื่อ claim_type=petty_cash)",
    )
    advance_account_id = fields.Many2one(
        "account.account", string="Employee Advance Account",
        tracking=True,
        help="บัญชีลูกหนี้พนักงาน/เงินทดรองจ่าย ที่ใช้ติดตามยอดคงค้างจนกว่าจะเคลียร์ครบ",
    )
    amount = fields.Monetary(
        string="Requested Amount", currency_field="currency_id", tracking=True,
        help="จำนวนเงินที่ขอ (เงินทดรอง/เงินสดย่อย) — สำหรับเบิกคืนใช้ยอดรวมบรรทัด",
    )

    line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="Expense Lines",
    )

    # ------------------------------------------------------------------
    # ประเภทบรรทัด — 4 แท็บของหน้า /odoo/expenses
    # ------------------------------------------------------------------
    # Odoo 19 ไม่ใช้ ``domain`` ที่ประกาศบน view ในการกรองบรรทัดที่โหลดในฟอร์ม
    # (ยืนยันจาก odoo/orm/fields_relational.py::One2many.read ที่กรองด้วย
    # ``get_comodel_domain`` = domain ใน field definition เท่านั้น) จึงแยก
    # One2many ต่อประเภทแล้วประกาศ domain ที่นี่ — รูปแบบเดียวกับ
    # account.move.line_ids / invoice_line_ids (หลายฟิลด์ใช้ inverse เดียวกัน)
    # แต่ละแท็บจึงแสดงเฉพาะบรรทัดของตัวเองและยังเพิ่ม/แก้ไขได้ตามปกติ
    general_line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="General Lines",
        domain=[("od19_is_per_diem", "=", False),
                ("od19_is_mileage", "=", False),
                ("od19_is_toll", "=", False)],
        help="รายการเบิกทั่วไป (ไม่ใช่เบี้ยเลี้ยง/ไมเลจ/ค่าผ่านทาง)",
    )
    per_diem_line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="Per Diem Lines",
        domain=[("od19_is_per_diem", "=", True),
                ("od19_is_mileage", "=", False),
                ("od19_is_toll", "=", False)],
        help="รายการเบี้ยเลี้ยง ม.42(3)",
    )
    mileage_line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="Mileage Lines",
        domain=[("od19_is_mileage", "=", True),
                ("od19_is_toll", "=", False)],
        help="รายการค่าเดินทางตามระยะทาง (ไมเลจ)",
    )
    toll_line_ids = fields.One2many(
        "hr.expense", "od19_claim_id", string="Toll Lines",
        domain=[("od19_is_toll", "=", True)],
        help="รายการค่าผ่านทาง (ทางด่วน/ทางพิเศษ) ตามใบเสร็จในมือ",
    )

    total_amount = fields.Monetary(
        string="Total", currency_field="currency_id",
        compute="_compute_total_amount", store=True,
    )

    # ยอดแยกตามประเภท + ยอดเบิกรวมสุทธิของทั้งเอกสาร (แสดงบนหัวใบ)
    general_total = fields.Monetary(
        string="General Total", currency_field="currency_id",
        compute="_compute_breakdown_totals", store=True,
    )
    per_diem_total = fields.Monetary(
        string="Per Diem Total", currency_field="currency_id",
        compute="_compute_breakdown_totals", store=True,
    )
    mileage_total = fields.Monetary(
        string="Mileage Total", currency_field="currency_id",
        compute="_compute_breakdown_totals", store=True,
    )
    toll_total = fields.Monetary(
        string="Toll Total", currency_field="currency_id",
        compute="_compute_breakdown_totals", store=True,
    )
    net_total = fields.Monetary(
        string="Net Total / ยอดเบิกรวมสุทธิ", currency_field="currency_id",
        compute="_compute_breakdown_totals", store=True,
        help="ยอดเบิกรวมสุทธิของเอกสารเบิกนี้ "
             "= รายการทั่วไป + เบี้ยเลี้ยง + ไมเลจ + ค่าผ่านทาง",
    )

    payment_mode = fields.Selection(
        [("own_account", "Employee (to reimburse)"),
         ("company_account", "Company")],
        string="Paid By", default="own_account", required=True, tracking=True,
    )

    # ------------------------------------------------------------------
    # P2 — การจ่ายเงิน / เงินค้างมือพนักงาน ("วงเงินที่พนักงานถืออยู่")
    # ------------------------------------------------------------------
    payment_id = fields.Many2one(
        "account.payment", string="Payment", readonly=True, copy=False,
    )
    payment_date = fields.Date(
        string="Payment Date", readonly=True, copy=False, tracking=True,
    )
    journal_id = fields.Many2one(
        "account.journal", string="Payment Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
    )
    payment_method = fields.Selection(
        [("cash", "Cash"), ("bank_transfer", "Bank Transfer"),
         ("cheque", "Cheque")],
        string="Payment Method", default="cash", tracking=True,
    )
    reimbursement_date = fields.Date(
        string="Reimbursement Date", readonly=True, copy=False,
    )
    cash_state = fields.Selection(
        [("not_issued", "Not Issued"),
         ("issued", "Issued"),
         ("partially_used", "Partially Used"),
         ("settled", "Settled")],
        string="Cash State", default="not_issued", tracking=True, copy=False,
        help="สถานะเงินที่พนักงานถืออยู่ (เงินทดรอง/เงินสดย่อย): "
             "ยังไม่จ่าย -> จ่ายแล้ว -> ใช้ไปบางส่วน -> เคลียร์ครบ",
    )
    cleared_amount = fields.Monetary(
        string="Cleared Amount", currency_field="currency_id",
        compute="_compute_cleared_amount", store=True,
    )
    remaining_amount = fields.Monetary(
        string="Remaining Amount", currency_field="currency_id",
        compute="_compute_remaining_amount", store=True,
    )
    clear_move_id = fields.Many2one(
        "account.move", string="Clearing Entry", readonly=True, copy=False,
    )
    clear_date = fields.Date(
        string="Clearing Date", readonly=True, copy=False, tracking=True,
    )
    advance_id = fields.Many2one(
        "od19.expense.claim", string="Cleared Against Advance",
        index="btree_not_null", copy=False,
        help="ใบทดรองที่ใบเบิกคืนนี้นำมาเคลียร์",
    )
    clearing_claim_ids = fields.One2many(
        "od19.expense.claim", "advance_id", string="Clearing Claims",
    )

    # P4 — ตัวกรองพร้อมใช้ของศูนย์งานฝ่ายบัญชี (§10.3):
    # ใบที่ค้างอนุมัติอยู่ที่ชั้นฝ่ายบัญชี (ชั้นที่ 2) — ไม่เก็บลง DB คำนวณจาก tier.review
    od19_waiting_accounting_approval = fields.Boolean(
        string="Waiting Accounting Approval",
        compute="_compute_od19_waiting_accounting_approval",
        search="_search_od19_waiting_accounting_approval",
        help="ใบที่ค้างอนุมัติอยู่ที่ชั้นฝ่ายบัญชี (ชั้นที่ 2)",
    )

    state = fields.Selection(
        [("draft", "Draft"),
         ("submitted", "Submitted"),
         ("approved", "Approved"),
         ("sent", "Sent to Accounting"),
         ("posted", "Posted"),
         ("paid", "Paid"),
         ("cleared", "Cleared"),
         ("refused", "Refused")],
        string="Status", default="draft", tracking=True, copy=False,
    )
    note = fields.Text(string="Notes")

    # ------------------------------------------------------------------
    # Compute / create
    # ------------------------------------------------------------------
    @api.depends("employee_id", "employee_id.work_contact_id")
    def _compute_partner_id(self):
        for claim in self:
            employee = claim.employee_id
            claim.partner_id = (
                employee.work_contact_id or employee.user_id.partner_id
            )

    @api.depends("line_ids.total_amount")
    def _compute_total_amount(self):
        for claim in self:
            claim.total_amount = sum(claim.line_ids.mapped("total_amount"))

    @api.depends(
        "line_ids.total_amount",
        "line_ids.od19_is_per_diem",
        "line_ids.od19_is_mileage",
        "line_ids.od19_is_toll",
    )
    def _compute_breakdown_totals(self):
        """ยอดแยกตามประเภท (ให้ตรงกับ domain ของทั้ง 4 แท็บ) + ยอดรวมสุทธิ.

        การจัดประเภทใช้ลำดับความสำคัญ toll > mileage > per diem > general
        เหมือนกันทั้งใน domain ของแต่ละแท็บและที่นี่ เพื่อไม่ให้ยอดซ้ำกัน
        """
        for claim in self:
            lines = claim.line_ids
            toll = lines.filtered("od19_is_toll")
            mileage = (lines - toll).filtered("od19_is_mileage")
            per_diem = (lines - toll - mileage).filtered("od19_is_per_diem")
            general = lines - toll - mileage - per_diem
            claim.toll_total = sum(toll.mapped("total_amount"))
            claim.mileage_total = sum(mileage.mapped("total_amount"))
            claim.per_diem_total = sum(per_diem.mapped("total_amount"))
            claim.general_total = sum(general.mapped("total_amount"))
            claim.net_total = (
                claim.general_total + claim.per_diem_total
                + claim.mileage_total + claim.toll_total
            )

    @api.depends(
        "amount",
        "advance_account_id",
        "payment_id.move_id.line_ids.amount_residual",
        "payment_id.move_id.line_ids.account_id",
    )
    def _compute_cleared_amount(self):
        """ยอดที่เคลียร์แล้ว = ยอดเบิก - ยอดคงเหลือในบัญชีลูกหนี้พนักงาน."""
        for claim in self:
            residual = 0.0
            move = claim.payment_id.move_id
            if move and claim.advance_account_id:
                advance_lines = move.line_ids.filtered(
                    lambda line: line.account_id == claim.advance_account_id
                )
                residual = sum(abs(line.amount_residual) for line in advance_lines)
            claim.cleared_amount = (
                claim.amount - residual if claim.amount else 0.0
            )

    @api.depends("amount", "cleared_amount")
    def _compute_remaining_amount(self):
        for claim in self:
            claim.remaining_amount = claim.amount - claim.cleared_amount

    @api.depends("state", "review_ids.status", "review_ids.definition_id")
    def _compute_od19_waiting_accounting_approval(self):
        accounting_group = self.env.ref(
            "account.group_account_manager", raise_if_not_found=False)
        for claim in self:
            pending = claim.review_ids.filtered(
                lambda review: review.status == "pending"
            ).sorted("sequence")[:1]
            claim.od19_waiting_accounting_approval = bool(
                claim.state == "submitted"
                and pending
                and pending.definition_id.reviewer_group_id == accounting_group
            )

    def _search_od19_waiting_accounting_approval(self, operator, value):
        if operator not in ("=", "!="):
            raise UserError(_("Unsupported operator for this filter."))
        if not isinstance(value, bool):
            value = bool(value)
        accounting_group = self.env.ref(
            "account.group_account_manager", raise_if_not_found=False)
        reviews = self.env["tier.review"].search([
            ("model", "=", "od19.expense.claim"),
            ("status", "=", "pending"),
            ("definition_id.reviewer_group_id", "=", accounting_group.id),
        ])
        ids = [review.res_id for review in reviews if review.res_id]
        if (operator == "=") == value:
            return [("id", "in", ids)]
        return [("id", "not in", ids)]

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
    @api.constrains("line_ids", "claim_type")
    def _check_single_payment_mode(self):
        for claim in self:
            # K6: ใบเบิกคืนห้ามผสมวิธีจ่าย (Paid By) — เงินทดรอง/เงินสดย่อยไม่มีบรรทัดแบบนี้
            if claim.claim_type != "reimbursement":
                continue
            modes = set(claim.line_ids.mapped("payment_mode"))
            if len(modes) > 1:
                raise ValidationError(
                    _("ทุกบรรทัดในใบเบิกต้องใช้วิธีจ่าย (Paid By) เดียวกัน")
                )

    @api.constrains("claim_type", "claim_source", "payment_mode", "purpose",
                    "advance_account_id", "cash_fund_id")
    def _check_claim_type_rules(self):
        for claim in self:
            if claim.claim_type == "advance":
                if claim.payment_mode != "company_account":
                    raise ValidationError(_(
                        "เงินทดรองต้องจ่ายโดยบริษัทก่อน (Paid By = Company)"))
                if not claim.purpose:
                    raise ValidationError(_(
                        "ต้องระบุวัตถุประสงค์ (Purpose) สำหรับเงินทดรอง"))
                if not claim.advance_account_id:
                    raise ValidationError(_(
                        "ต้องระบุบัญชีเงินทดรอง/ลูกหนี้พนักงาน"))
            elif claim.claim_type == "petty_cash":
                if claim.claim_source != "on_behalf":
                    raise ValidationError(_(
                        "เงินสดย่อยต้องเป็นรายการที่ฝ่ายบัญชีทำแทน (On Behalf)"))
                if not claim.cash_fund_id:
                    raise ValidationError(_("ต้องระบุกองทุนเงินสดย่อย"))

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        """ส่งใบเบิกเพื่อขออนุมัติ 3 ชั้นที่หัวใบ."""
        for claim in self:
            if claim.state != "draft":
                raise UserError(_("ส่งได้เฉพาะใบเบิกที่เป็นฉบับร่าง"))
            if claim.claim_type == "advance":
                # เงินทดรองยังไม่มีบรรทัดตอนสร้าง -> บังคับเฉพาะข้อมูลหัวใบ
                # (บังคับ analytic ตอนเคลียร์ที่มีบรรทัดจริง — §9)
                if not claim.amount or claim.amount <= 0:
                    raise UserError(_("ต้องระบุจำนวนเงินทดรองที่ต้องการเบิก"))
                if not claim.purpose:
                    raise UserError(_("ต้องระบุวัตถุประสงค์ (Purpose) ก่อนส่งอนุมัติ"))
                if not claim.advance_account_id:
                    raise UserError(_("ต้องระบุบัญชีเงินทดรอง/ลูกหนี้พนักงานก่อนส่งอนุมัติ"))
            else:
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
            if claim.state in ("posted", "paid", "cleared"):
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
    # P2 — จ่ายเงินทดรอง / เงินสดย่อย (ย้ายจาก od19.hr.advance)
    # ------------------------------------------------------------------
    def _od19_get_payment_journal(self):
        self.ensure_one()
        if self.cash_fund_id:
            return self.cash_fund_id
        if self.journal_id:
            return self.journal_id
        Journal = self.env["account.journal"].with_company(self.company_id)
        journal = Journal.search(
            Journal._check_company_domain(self.company_id)
            + [("type", "in", ("bank", "cash"))],
            limit=1,
        )
        if not journal:
            raise UserError(_(
                "Please configure a bank or cash journal to pay this advance."))
        return journal

    def _od19_get_payment_method_line(self, journal):
        """เลือก outbound payment method line ที่มีบัญชีค้างจ่ายครบถ้วน."""
        self.ensure_one()
        lines = journal.outbound_payment_method_line_ids
        if not lines:
            raise UserError(_(
                "The journal %s has no outbound payment method configured.")
                % journal.display_name)
        method_line = lines.filtered("payment_account_id")[:1] or lines[:1]
        if not method_line.payment_account_id:
            outstanding = (
                self.env["account.chart.template"]
                .with_company(self.company_id)
                .ref("account_journal_payment_credit_account_id",
                     raise_if_not_found=False)
                or self.company_id.transfer_account_id
            )
            if not outstanding:
                raise UserError(_(
                    "No outstanding payments account is configured for the "
                    "journal %s.") % journal.display_name)
            method_line.payment_account_id = outstanding
        return method_line

    def action_pay(self):
        """จ่ายเงินทดรอง/เงินสดย่อยให้พนักงานด้วย ``account.payment`` จริง.

        เดบิตบัญชีลูกหนี้พนักงาน (``advance_account_id``) เครดิตบัญชีเงินสด/ธนาคาร
        เพื่อให้ยอดคงค้างถูกติดตามจนกว่าจะเคลียร์ (``cash_state='issued'``)
        """
        for claim in self:
            if claim.claim_type not in ("advance", "petty_cash"):
                raise UserError(_(
                    "จ่ายเงินจากหัวใบได้เฉพาะเงินทดรอง/เงินสดย่อย "
                    "(ใบเบิกคืนใช้กลไกจ่ายคืนปกติ)"))
            if claim.state != "approved":
                raise UserError(_("จ่ายได้เฉพาะใบที่อนุมัติครบแล้ว"))
            if not claim.partner_id:
                raise UserError(_(
                    "No contact is linked to the employee %s, please configure one.")
                    % claim.employee_id.name)
            if not claim.advance_account_id:
                raise UserError(_("ต้องระบุบัญชีเงินทดรอง/ลูกหนี้พนักงาน"))
            if not claim.amount or claim.amount <= 0:
                raise UserError(_("ต้องระบุจำนวนเงินที่จ่าย"))
            journal = claim._od19_get_payment_journal()
            method_line = claim._od19_get_payment_method_line(journal)
            date = claim.payment_date or fields.Date.context_today(claim)
            payment = self.env["account.payment"].create({
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": claim.partner_id.id,
                "amount": claim.amount,
                "currency_id": claim.currency_id.id,
                "date": date,
                "journal_id": journal.id,
                "payment_method_line_id": method_line.id,
                "destination_account_id": claim.advance_account_id.id,
                "memo": claim.name,
                # เงินทดรองให้พนักงานไม่ใช่การจ่ายชำระเจ้าหนี้ จึงไม่ต้องมี
                # Vendor Bill ก่อน (ข้ามกติกา AP bill-first)
                "od19_is_expense_payment": True,
            })
            payment.action_post()
            claim.write({
                "payment_id": payment.id,
                "payment_date": date,
                "journal_id": journal.id,
                "state": "paid",
                "cash_state": "issued",
            })
            claim.invalidate_recordset(["cleared_amount", "remaining_amount"])
        return True

    def action_open_clear_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Clear Advance"),
            "res_model": "od19.expense.claim.clear",
            "view_mode": "form",
            "target": "new",
            "context": {"default_claim_id": self.id},
        }

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
