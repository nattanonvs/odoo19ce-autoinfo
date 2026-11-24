from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class Od19BringForward(models.Model):
    _name = "od19.bring.forward"
    _description = "Bring Forward"
    _rec_name = "doc_no"
    _order = "doc_no desc"

    doc_no = fields.Char(string="Document No.", default="New", readonly=True, copy=False)
    name = fields.Char(string="Name")
    remark = fields.Text(string="Remark")
    date = fields.Date(string="Date", default=fields.Date.context_today)
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        default=lambda self: self.env.company.bring_forward_journal_id,
    )
    mode = fields.Selection(
        [("manual", "Manual"), ("auto", "Automatic")],
        string="Mode",
        default="manual",
        required=True,
        copy=False,
    )
    date_from = fields.Date(string="Period From", copy=False)
    date_to = fields.Date(string="Period To", copy=False)
    line_ids = fields.One2many(
        "od19.bring.forward.line",
        "bring_forward_id",
        string="Chart of Accounts",
        copy=False,
        default=lambda self: self._default_line_commands(),
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("computed", "Computed"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    stock_inventory_ids = fields.One2many("stock.quant", "od19_bf_id", copy=False)
    inven_adjust_count = fields.Integer(compute="_compute_inven_adjust_count")

    customer_invoice_ids = fields.One2many(
        "account.move", "od19_customer_bf_id", string="Customer Invoices", copy=False
    )
    customer_invoice_count = fields.Integer(compute="_compute_customer_invoice_count")

    vendor_bill_ids = fields.One2many(
        "account.move", "od19_vendor_bf_id", string="Vendor Bills", copy=False
    )
    vendor_bill_count = fields.Integer(compute="_compute_vendor_bill_count")

    payment_receipt_ids = fields.One2many(
        "account.payment", "od19_receipt_bf_id", string="Payment Receipts", copy=False
    )
    payment_receipt_count = fields.Integer(compute="_compute_payment_receipt_count")

    payment_send_ids = fields.One2many(
        "account.payment", "od19_bf_id", string="Payment Sends", copy=False
    )
    payment_send_count = fields.Integer(compute="_compute_payment_send_count")

    account_asset_asset_ids = fields.One2many(
        "account.asset", "od19_bf_id", string="Assets", copy=False
    )
    account_asset_asset_count = fields.Integer(compute="_compute_account_asset_asset_count")

    move_id = fields.Many2one("account.move", string="Journal Entry", copy=False, readonly=True)

    customer_credit_note_ids = fields.One2many(
        "account.move", "od19_customer_cn_bf_id", string="Customer Credit Notes", copy=False
    )
    customer_credit_note_count = fields.Integer(compute="_compute_customer_credit_note_count")

    customer_debit_note_ids = fields.One2many(
        "account.move", "od19_customer_dn_bf_id", string="Customer Debit Notes", copy=False
    )
    customer_debit_note_count = fields.Integer(compute="_compute_customer_debit_note_count")

    vendor_credit_note_ids = fields.One2many(
        "account.move", "od19_vendor_cn_bf_id", string="Vendor Credit Notes", copy=False
    )
    vendor_credit_note_count = fields.Integer(compute="_compute_vendor_credit_note_count")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _default_line_commands(self):
        """Pre-fill the Chart of Accounts tab with every account of the company."""
        company = self.env.company
        accounts = self.env["account.account"].search([("company_ids", "in", company.id)])
        return [
            (0, 0, {"account_id": acc.id, "account_id_show": acc.id, "is_create_manual": False})
            for acc in accounts
        ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.doc_no or rec.doc_no == "New":
                rec.doc_no = (
                    self.env["ir.sequence"]
                    .with_company(rec.company_id)
                    .with_context(ir_sequence_date=rec.date)
                    .next_by_code("account.bring.forward")
                    or "New"
                )
        return records

    @api.onchange("company_id")
    def _onchange_company_id(self):
        self.journal_id = False
        if self.company_id and self.company_id.bring_forward_journal_id:
            self.journal_id = self.company_id.bring_forward_journal_id.id

    def _add_amounts(self, move_lines):
        """Accumulate debit/credit of ``move_lines`` into the matching chart lines."""
        self.ensure_one()
        amounts = {}
        for ml in move_lines:
            account = ml.account_id
            if not account:
                continue
            debit, credit = amounts.get(account.id, (0.0, 0.0))
            amounts[account.id] = (debit + ml.debit, credit + ml.credit)
        for account_id, (debit, credit) in amounts.items():
            lines = self.line_ids.filtered(lambda l: l.account_id.id == account_id)
            for line in lines:
                line.write(
                    {
                        "compute_debit": line.compute_debit + debit,
                        "compute_credit": line.compute_credit + credit,
                    }
                )

    # ------------------------------------------------------------------
    # Automatic gathering (mode = auto)
    # ------------------------------------------------------------------
    def _check_period(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            raise UserError(
                _("Please set the period (Period From / Period To) for the automatic mode.")
            )
        if self.date_from > self.date_to:
            raise UserError(_("Period From must be earlier than Period To."))

    def _clear_links(self):
        self.ensure_one()
        (self.customer_invoice_ids + self.vendor_bill_ids).write(
            {"od19_customer_bf_id": False, "od19_vendor_bf_id": False}
        )
        (self.customer_credit_note_ids).write({"od19_customer_cn_bf_id": False})
        (self.customer_debit_note_ids).write({"od19_customer_dn_bf_id": False})
        (self.vendor_credit_note_ids).write({"od19_vendor_cn_bf_id": False})
        (self.payment_receipt_ids).write({"od19_receipt_bf_id": False})
        (self.payment_send_ids).write({"od19_bf_id": False})
        (self.account_asset_asset_ids).write({"od19_bf_id": False})
        (self.stock_inventory_ids).write({"od19_bf_id": False})

    def action_gather(self):
        """Link the posted documents of the period (automatic mode only)."""
        for rec in self:
            if rec.mode != "auto":
                raise UserError(_("Gathering is only available in Automatic mode."))
            rec._check_period()
            rec._clear_links()
            rec._gather_documents()
        return True

    def _gather_documents(self):
        self.ensure_one()
        company = self.company_id
        period = [
            ("company_id", "=", company.id),
            ("state", "=", "posted"),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]
        Move = self.env["account.move"]
        has_dncn = "dncn" in Move._fields
        plain_invoice_domain = [("dncn", "in", [False, "re"])] if has_dncn else []

        # Customer invoices (plain invoices + remaster)
        Move.search(
            period + [("move_type", "=", "out_invoice")] + plain_invoice_domain
        ).write({"od19_customer_bf_id": self.id})
        # Customer debit notes
        if has_dncn:
            Move.search(
                period + [("move_type", "=", "out_invoice"), ("dncn", "=", "dn")]
            ).write({"od19_customer_dn_bf_id": self.id})
        # Customer credit notes
        Move.search(period + [("move_type", "=", "out_refund")]).write(
            {"od19_customer_cn_bf_id": self.id}
        )
        # Vendor bills
        Move.search(
            period + [("move_type", "=", "in_invoice")] + plain_invoice_domain
        ).write({"od19_vendor_bf_id": self.id})
        # Vendor credit notes
        Move.search(period + [("move_type", "=", "in_refund")]).write(
            {"od19_vendor_cn_bf_id": self.id}
        )

        # Payments (posted means: not draft / canceled / rejected)
        Payment = self.env["account.payment"]
        payment_period = [
            ("company_id", "=", company.id),
            ("state", "in", ("in_process", "paid")),
            ("date", ">=", self.date_from),
            ("date", "<=", self.date_to),
        ]
        Payment.search(payment_period + [("payment_type", "=", "inbound")]).write(
            {"od19_receipt_bf_id": self.id}
        )
        Payment.search(payment_period + [("payment_type", "=", "outbound")]).write(
            {"od19_bf_id": self.id}
        )

        # Fixed assets (open assets of the company)
        self.env["account.asset"].search(
            [("company_id", "=", company.id), ("state", "=", "open")]
        ).write({"od19_bf_id": self.id})

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    def _reset_compute(self):
        self.line_ids.write({"compute_debit": 0.0, "compute_credit": 0.0})

    def _compute_invoices(self, moves):
        self._add_amounts(moves.filtered(lambda m: m.state == "posted").line_ids)

    def _compute_payments(self, payments):
        for payment in payments.filtered(lambda p: p.state in ("in_process", "paid")):
            self._add_amounts(payment.move_id.line_ids)

    def _compute_fixed_assets(self):
        for asset in self.account_asset_asset_ids:
            posted_lines = asset.depreciation_line_ids.filtered(
                lambda l: l.move_id and l.move_id.state == "posted"
            )
            for line in posted_lines:
                self._add_amounts(line.move_id.line_ids)

    def _compute_inventory_adjust(self):
        moves = self.env["stock.move"].search(
            [("od19_bf_id", "=", self.id), ("account_move_id", "!=", False)]
        )
        for move in moves:
            if move.account_move_id.state == "posted":
                self._add_amounts(move.account_move_id.line_ids)

    def _validate_compute(self):
        self.ensure_one()
        if self.customer_invoice_ids.filtered(lambda m: m.state not in ("posted", "cancel")):
            raise ValidationError(_("Please validate customer invoices first."))
        if self.vendor_bill_ids.filtered(lambda m: m.state not in ("posted", "cancel")):
            raise ValidationError(_("Please validate vendor bills first."))
        if self.customer_credit_note_ids.filtered(lambda m: m.state not in ("posted", "cancel")):
            raise ValidationError(_("Please validate customer credit notes first."))
        if self.customer_debit_note_ids.filtered(lambda m: m.state not in ("posted", "cancel")):
            raise ValidationError(_("Please validate customer debit notes first."))
        if self.vendor_credit_note_ids.filtered(lambda m: m.state not in ("posted", "cancel")):
            raise ValidationError(_("Please validate vendor credit notes first."))
        if self.payment_receipt_ids.filtered(lambda p: p.state == "draft"):
            raise ValidationError(_("Please post the receipt payments first."))
        if self.payment_send_ids.filtered(lambda p: p.state == "draft"):
            raise ValidationError(_("Please post the outgoing payments first."))
        moves = self.env["stock.move"].search([("od19_bf_id", "=", self.id)])
        if moves.filtered(lambda m: m.state not in ("done", "cancel")):
            raise ValidationError(_("Please validate the inventory adjustment first."))
        for asset in self.account_asset_asset_ids:
            if asset.depreciation_line_ids.filtered(
                lambda l: l.move_id and l.move_id.state != "posted"
            ):
                raise ValidationError(_("Please post the fixed asset depreciation first."))

    def action_compute(self):
        for rec in self:
            if rec.mode == "auto":
                rec.action_gather()
            rec._validate_compute()
            rec._reset_compute()
            rec._compute_invoices(rec.customer_invoice_ids)
            rec._compute_invoices(rec.vendor_bill_ids)
            rec._compute_invoices(rec.customer_credit_note_ids)
            rec._compute_invoices(rec.customer_debit_note_ids)
            rec._compute_invoices(rec.vendor_credit_note_ids)
            rec._compute_payments(rec.payment_receipt_ids)
            rec._compute_payments(rec.payment_send_ids)
            rec._compute_fixed_assets()
            rec._compute_inventory_adjust()
            rec.state = "computed"
        return True

    # ------------------------------------------------------------------
    # Post
    # ------------------------------------------------------------------
    def _validate_post(self):
        self.ensure_one()
        precision = self.env["decimal.precision"].precision_get("Bring Forward")
        if self.line_ids.filtered(lambda l: l.difference_debit < 0 or l.difference_credit < 0):
            raise ValidationError(
                _("Please check the target total debit or credit: the target cannot be lower than the computed amount.")
            )
        total_debit = round(sum(self.line_ids.mapped("difference_debit")), precision)
        total_credit = round(sum(self.line_ids.mapped("difference_credit")), precision)
        if total_debit != total_credit:
            raise ValidationError(_("Total difference debit and credit are not balanced."))
        if not self.line_ids.filtered(lambda l: l.difference_debit > 0) or not self.line_ids.filtered(
            lambda l: l.difference_credit > 0
        ):
            raise ValidationError(_("There is no data to create the journal entry."))

    def _prepare_move_line(self, line, debit, credit):
        return {
            "date_maturity": self.date,
            "debit": debit,
            "credit": credit,
            "account_id": line.account_id.id,
        }

    def action_post(self):
        for rec in self:
            rec.action_compute()
            rec._validate_post()
            debit_lines = [
                (0, 0, rec._prepare_move_line(line, line.difference_debit, 0))
                for line in rec.line_ids
                if line.difference_debit > 0
            ]
            credit_lines = [
                (0, 0, rec._prepare_move_line(line, 0, line.difference_credit))
                for line in rec.line_ids
                if line.difference_credit > 0
            ]
            move = self.env["account.move"].create(
                {
                    "ref": rec.doc_no,
                    "line_ids": debit_lines + credit_lines,
                    "journal_id": rec.journal_id.id,
                    "date": rec.date,
                    "narration": rec.remark,
                }
            )
            move.action_post()
            rec.write({"state": "posted", "move_id": move.id})
        return True

    # ------------------------------------------------------------------
    # Computes (counters)
    # ------------------------------------------------------------------
    @api.depends("stock_inventory_ids")
    def _compute_inven_adjust_count(self):
        for rec in self:
            rec.inven_adjust_count = len(rec.stock_inventory_ids)

    @api.depends("customer_invoice_ids")
    def _compute_customer_invoice_count(self):
        for rec in self:
            rec.customer_invoice_count = len(rec.customer_invoice_ids)

    @api.depends("vendor_bill_ids")
    def _compute_vendor_bill_count(self):
        for rec in self:
            rec.vendor_bill_count = len(rec.vendor_bill_ids)

    @api.depends("payment_receipt_ids")
    def _compute_payment_receipt_count(self):
        for rec in self:
            rec.payment_receipt_count = len(rec.payment_receipt_ids)

    @api.depends("payment_send_ids")
    def _compute_payment_send_count(self):
        for rec in self:
            rec.payment_send_count = len(rec.payment_send_ids)

    @api.depends("account_asset_asset_ids")
    def _compute_account_asset_asset_count(self):
        for rec in self:
            rec.account_asset_asset_count = len(rec.account_asset_asset_ids)

    @api.depends("customer_credit_note_ids")
    def _compute_customer_credit_note_count(self):
        for rec in self:
            rec.customer_credit_note_count = len(rec.customer_credit_note_ids)

    @api.depends("customer_debit_note_ids")
    def _compute_customer_debit_note_count(self):
        for rec in self:
            rec.customer_debit_note_count = len(rec.customer_debit_note_ids)

    @api.depends("vendor_credit_note_ids")
    def _compute_vendor_credit_note_count(self):
        for rec in self:
            rec.vendor_credit_note_count = len(rec.vendor_credit_note_ids)

    # ------------------------------------------------------------------
    # Smart button actions
    # ------------------------------------------------------------------
    def _action_open(self, name, res_model, domain, context=None, views=None):
        self.ensure_one()
        return {
            "name": name,
            "type": "ir.actions.act_window",
            "res_model": res_model,
            "view_mode": "list,form",
            "views": views or [(False, "list"), (False, "form")],
            "domain": domain,
            "context": dict(context or {}, default_company_id=self.company_id.id),
        }

    def view_inventory_adjustment(self):
        return self._action_open(
            _("Inventory Adjustments"),
            "stock.quant",
            [("od19_bf_id", "=", self.id)],
            {"default_od19_bf_id": self.id},
        )

    def view_customer_invoices(self):
        return self._action_open(
            _("Customer Invoices"),
            "account.move",
            [("od19_customer_bf_id", "=", self.id)],
            {"default_move_type": "out_invoice", "default_od19_customer_bf_id": self.id},
            [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
        )

    def view_vendor_bills(self):
        return self._action_open(
            _("Vendor Bills"),
            "account.move",
            [("od19_vendor_bf_id", "=", self.id)],
            {"default_move_type": "in_invoice", "default_od19_vendor_bf_id": self.id},
            [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
        )

    def view_payment_receipt(self):
        return self._action_open(
            _("Payments"),
            "account.payment",
            [("od19_receipt_bf_id", "=", self.id)],
            {"default_payment_type": "inbound", "default_od19_receipt_bf_id": self.id},
            [
                (self.env.ref("account.view_account_payment_tree").id, "list"),
                (self.env.ref("account.view_account_payment_form").id, "form"),
            ],
        )

    def view_payment_send(self):
        return self._action_open(
            _("Payments"),
            "account.payment",
            [("od19_bf_id", "=", self.id)],
            {
                "default_payment_type": "outbound",
                "default_od19_bf_id": self.id,
                "default_partner_type": "supplier",
            },
            [
                (self.env.ref("account.view_account_supplier_payment_tree").id, "list"),
                (self.env.ref("account.view_account_payment_form").id, "form"),
            ],
        )

    def view_fixed_assets(self):
        return self._action_open(
            _("Assets"),
            "account.asset",
            [("od19_bf_id", "=", self.id)],
            {"default_od19_bf_id": self.id},
        )

    def view_customer_credit_note(self):
        return self._action_open(
            _("Customer Credit Notes"),
            "account.move",
            [("od19_customer_cn_bf_id", "=", self.id)],
            {
                "default_move_type": "out_refund",
                "default_dncn": "cn",
                "default_od19_customer_cn_bf_id": self.id,
            },
            [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
        )

    def view_customer_debit_note(self):
        return self._action_open(
            _("Debit Notes"),
            "account.move",
            [("od19_customer_dn_bf_id", "=", self.id)],
            {
                "default_move_type": "out_invoice",
                "default_dncn": "dn",
                "default_od19_customer_dn_bf_id": self.id,
            },
            [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
        )

    def view_vendor_credit_note(self):
        return self._action_open(
            _("Vendor Credit Notes"),
            "account.move",
            [("od19_vendor_cn_bf_id", "=", self.id)],
            {"default_move_type": "in_refund", "default_od19_vendor_cn_bf_id": self.id},
            [
                (self.env.ref("account.view_move_tree").id, "list"),
                (self.env.ref("account.view_move_form").id, "form"),
            ],
        )


class Od19BringForwardLine(models.Model):
    _name = "od19.bring.forward.line"
    _description = "Bring Forward Line"

    bring_forward_id = fields.Many2one(
        "od19.bring.forward", string="Bring Forward", ondelete="cascade"
    )
    account_id = fields.Many2one("account.account", string="Account")
    account_id_show = fields.Many2one(
        "account.account", related="account_id", readonly=False, store=True
    )
    target_total_debit = fields.Float(string="Target Total Debit", digits="Bring Forward")
    compute_debit = fields.Float(
        string="Compute Debit", readonly=True, store=True, digits="Bring Forward"
    )
    difference_debit = fields.Float(
        string="Difference Debit",
        compute="_compute_difference_debit",
        store=True,
        digits="Bring Forward",
    )
    target_total_credit = fields.Float(string="Target Total Credit", digits="Bring Forward")
    compute_credit = fields.Float(
        string="Compute Credit", readonly=True, store=True, digits="Bring Forward"
    )
    difference_credit = fields.Float(
        string="Difference Credit",
        compute="_compute_difference_credit",
        store=True,
        digits="Bring Forward",
    )
    is_create_manual = fields.Boolean(string="Is Manual Create?", copy=False, default=True)
    company_id = fields.Many2one(
        "res.company", string="Company", related="bring_forward_id.company_id", store=True
    )

    @api.depends("compute_debit", "target_total_debit")
    def _compute_difference_debit(self):
        for rec in self:
            rec.difference_debit = rec.target_total_debit - rec.compute_debit

    @api.depends("compute_credit", "target_total_credit")
    def _compute_difference_credit(self):
        for rec in self:
            rec.difference_credit = rec.target_total_credit - rec.compute_credit
