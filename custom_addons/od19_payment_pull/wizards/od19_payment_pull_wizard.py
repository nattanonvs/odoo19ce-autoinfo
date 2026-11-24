# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

# Document types considered per voucher direction.
OD19_MOVE_TYPES_BY_PAYMENT_TYPE = {
    "outbound": ["in_invoice", "in_refund"],
    "inbound": ["out_invoice", "out_refund"],
}


class Od19PaymentPullWizard(models.TransientModel):
    _name = "od19.payment.pull.wizard"
    _description = "OD19 Payment Pull Wizard"

    payment_type = fields.Selection(
        selection=[
            ("outbound", "จ่าย (เจ้าหนี้) / Outbound (Vendor)"),
            ("inbound", "รับ (ลูกหนี้) / Inbound (Customer)"),
        ],
        string="ประเภทใบสำคัญ / Voucher Type",
        required=True,
        default="outbound",
    )
    company_id = fields.Many2one(
        "res.company",
        string="บริษัท / Company",
        required=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="คู่ค้า (ตัวกรอง) / Partner filter",
    )
    date_from = fields.Date(string="ตั้งแต่วันที่ / Date from")
    date_to = fields.Date(string="ถึงวันที่ / Date to")
    only_overdue = fields.Boolean(string="เฉพาะเกินกำหนด / Only overdue")
    include_refunds = fields.Boolean(string="รวมใบลดหนี้/คืนเงิน / Include refunds")
    journal_id = fields.Many2one(
        "account.journal",
        string="สมุดบัญชี / Journal",
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
    )
    payment_date = fields.Date(
        string="วันที่จ่าย/รับ / Payment date",
        required=True,
        default=fields.Date.context_today,
    )
    group_by_partner = fields.Boolean(
        string="รวมเป็นใบสำคัญเดียวต่อคู่ค้า / One voucher per partner",
        default=True,
    )
    line_ids = fields.One2many(
        "od19.payment.pull.wizard.line",
        "wizard_id",
        string="รายการเอกสาร / Documents",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="สกุลเงิน / Currency",
        compute="_compute_currency_id",
    )
    selected_count = fields.Integer(
        string="จำนวนที่เลือก / Selected count",
        compute="_compute_selected_totals",
    )
    selected_amount = fields.Monetary(
        string="ยอดรวมที่เลือก / Selected amount",
        currency_field="currency_id",
        compute="_compute_selected_totals",
    )
    planned_voucher_count = fields.Integer(
        string="จำนวนใบสำคัญที่จะสร้าง / Planned vouchers",
        compute="_compute_selected_totals",
    )

    # -------------------------------------------------------------------------
    # DEFAULTS / LOADING
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        payment_type = res.get("payment_type") or "outbound"
        res["payment_type"] = payment_type
        if "line_ids" in fields_list and "line_ids" not in res:
            res["line_ids"] = self._od19_prepare_line_commands(
                payment_type=payment_type,
                company_id=res.get("company_id") or self.env.company.id,
                partner_id=res.get("partner_id"),
                date_from=res.get("date_from"),
                date_to=res.get("date_to"),
                only_overdue=res.get("only_overdue"),
                include_refunds=res.get("include_refunds"),
            )
        if not res.get("journal_id"):
            journal = self._od19_default_journal(
                res.get("company_id") or self.env.company.id
            )
            if journal:
                res["journal_id"] = journal.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        # ``default_get`` is also triggered by the ORM while creating a record,
        # but it only sees the defaults, not the filters passed to ``create``
        # (partner/date/...). Rebuild the lines from the final field values so
        # the filters are always honoured, unless the caller supplied them.
        for wizard, vals in zip(wizards, vals_list):
            if "line_ids" in vals:
                continue
            wizard.line_ids = wizard._od19_prepare_line_commands(
                payment_type=wizard.payment_type,
                company_id=wizard.company_id.id,
                partner_id=wizard.partner_id.id,
                date_from=wizard.date_from,
                date_to=wizard.date_to,
                only_overdue=wizard.only_overdue,
                include_refunds=wizard.include_refunds,
            )
        return wizards

    @api.onchange(
        "payment_type",
        "company_id",
        "partner_id",
        "date_from",
        "date_to",
        "only_overdue",
        "include_refunds",
    )
    def _onchange_reload_lines(self):
        for wizard in self:
            wizard.line_ids = wizard._od19_prepare_line_commands(
                payment_type=wizard.payment_type,
                company_id=wizard.company_id.id,
                partner_id=wizard.partner_id.id,
                date_from=wizard.date_from,
                date_to=wizard.date_to,
                only_overdue=wizard.only_overdue,
                include_refunds=wizard.include_refunds,
            )

    @api.model
    def _od19_default_journal(self, company_id):
        return self.env["account.journal"].search(
            [
                ("type", "in", ("bank", "cash")),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )

    def _od19_search_moves(
        self,
        payment_type,
        company_id,
        partner_id=False,
        date_from=False,
        date_to=False,
        only_overdue=False,
        include_refunds=False,
    ):
        """Return the open documents matching the wizard filters."""
        move_types = list(OD19_MOVE_TYPES_BY_PAYMENT_TYPE.get(payment_type, []))
        if not include_refunds:
            move_types = [move_type for move_type in move_types if not move_type.endswith("_refund")]
        domain = [
            ("move_type", "in", move_types),
            ("state", "=", "posted"),
            ("company_id", "=", company_id),
        ]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        if date_from:
            domain.append(("invoice_date", ">=", date_from))
        if date_to:
            domain.append(("invoice_date", "<=", date_to))
        if only_overdue:
            domain.append(
                ("invoice_date_due", "<", fields.Date.context_today(self))
            )
        moves = self.env["account.move"].search(domain)
        # Keep only documents that still have something to pay and can be paid.
        return moves.filtered(
            lambda move: move.payment_state != "blocked"
            and not move.currency_id.is_zero(move.amount_residual)
        )

    def _od19_prepare_line_commands(
        self,
        payment_type,
        company_id,
        partner_id=False,
        date_from=False,
        date_to=False,
        only_overdue=False,
        include_refunds=False,
    ):
        moves = self._od19_search_moves(
            payment_type=payment_type,
            company_id=company_id,
            partner_id=partner_id,
            date_from=date_from,
            date_to=date_to,
            only_overdue=only_overdue,
            include_refunds=include_refunds,
        )
        commands = [Command.clear()]
        for move in moves:
            commands.append(
                Command.create(
                    {
                        "move_id": move.id,
                        "selected": True,
                        "amount_to_pay": move.amount_residual,
                    }
                )
            )
        return commands

    # -------------------------------------------------------------------------
    # COMPUTED
    # -------------------------------------------------------------------------

    @api.depends("line_ids.selected", "line_ids.currency_id", "company_id")
    def _compute_currency_id(self):
        for wizard in self:
            currencies = wizard.line_ids.filtered("selected").currency_id
            wizard.currency_id = (
                currencies[:1] if len(currencies) == 1 else wizard.company_id.currency_id
            )

    @api.depends(
        "line_ids.selected",
        "line_ids.amount_to_pay",
        "line_ids.amount_residual",
        "line_ids.partner_id",
        "line_ids.currency_id",
        "group_by_partner",
        "currency_id",
    )
    def _compute_selected_totals(self):
        for wizard in self:
            selected = wizard.line_ids.filtered("selected")
            wizard.selected_count = len(selected)
            wizard.selected_amount = sum(selected.mapped("amount_to_pay"))
            if not wizard.group_by_partner:
                wizard.planned_voucher_count = len(selected)
            else:
                partial = selected.filtered("is_partial")
                full = selected - partial
                partners = {
                    (line.partner_id.id, line.currency_id.id) for line in full
                }
                wizard.planned_voucher_count = len(partners) + len(partial)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_pull(self):
        self.ensure_one()
        lines = self.line_ids.filtered("selected")
        if not lines:
            raise UserError(
                _(
                    "กรุณาเลือกรายการเอกสารอย่างน้อย 1 รายการ / "
                    "Please select at least one document."
                )
            )
        for line in lines:
            if line.currency_id.compare_amounts(line.amount_to_pay, 0.0) <= 0:
                raise UserError(
                    _(
                        "ยอดจ่ายของเอกสาร %(doc)s ต้องมากกว่า 0 / "
                        "The amount to pay for %(doc)s must be greater than 0.",
                        doc=line.ref or line.move_id.display_name,
                    )
                )
            if line.currency_id.compare_amounts(line.amount_to_pay, line.amount_residual) > 0:
                raise UserError(
                    _(
                        "ยอดจ่ายของเอกสาร %(doc)s เกินยอดค้างชำระ / "
                        "The amount to pay for %(doc)s exceeds the residual amount.",
                        doc=line.ref or line.move_id.display_name,
                    )
                )
        payments = self.env["account.payment"]
        for group_lines, amount in self._od19_build_groups(lines):
            payments |= self._od19_create_payment(group_lines, amount)
        return self._od19_open_created_payments(payments)

    def _od19_build_groups(self, lines):
        """Split the selected lines into voucher groups.

        Full lines are grouped per (partner, currency) when 'group_by_partner'
        is on, otherwise one group per document. Partial lines always get their
        own group so the edited amount can be honoured.
        """
        partial_lines = lines.filtered("is_partial")
        full_lines = lines - partial_lines
        groups = []
        if self.group_by_partner:
            buckets = {}
            for line in full_lines:
                key = (line.partner_id.id, line.currency_id.id)
                buckets.setdefault(key, self.env["od19.payment.pull.wizard.line"])
                buckets[key] |= line
            groups += [(bucket, None) for bucket in buckets.values()]
        else:
            groups += [(line, None) for line in full_lines]
        groups += [(line, line.amount_to_pay) for line in partial_lines]
        return groups

    def _od19_create_payment(self, lines, amount):
        moves = lines.move_id
        if amount is None:
            # Settle the whole residual by default. Without an explicit amount
            # the register wizard falls back to the *next installment* of the
            # payment term (e.g. a 30% advance), which would not pay the
            # documents shown in the wizard.
            amount = sum(lines.mapped("amount_residual"))
        vals = {
            "journal_id": self.journal_id.id,
            "payment_date": self.payment_date,
            "group_payment": True,
            # Keep the payment in draft so the prepare/approve gate applies.
            "od19_prepare_payment": True,
            # Force the amount so the register wizard does not replace it with
            # the next installment computed from the payment terms.
            "amount": amount,
            "custom_user_amount": amount,
            "custom_user_currency_id": lines[0].currency_id.id,
        }
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=moves.ids)
            .create(vals)
        )
        return wizard._create_payments()

    def _od19_open_created_payments(self, payments):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("สร้างใบสำคัญเรียบร้อย / Vouchers created"),
                "message": _(
                    "สร้างใบสำคัญจำนวน %(count)s ใบ ในสถานะร่าง / "
                    "%(count)s voucher(s) created in draft state.",
                    count=len(payments),
                ),
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window",
                    "name": _("ใบสำคัญที่สร้าง / Created Vouchers"),
                    "res_model": "account.payment",
                    "view_mode": "list,form",
                    "views": [
                        [
                            self.env.ref(
                                "od19_accounting_payment_voucher_reports."
                                "view_od19_payment_voucher_tree"
                            ).id,
                            "list",
                        ],
                        [False, "form"],
                    ],
                    "domain": [("id", "in", payments.ids)],
                    "context": {"create": False},
                },
            },
        }
