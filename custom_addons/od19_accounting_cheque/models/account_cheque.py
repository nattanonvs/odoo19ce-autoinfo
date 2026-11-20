# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountCheque(models.Model):
    _name = "account.cheque"
    _description = "Cheque"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "due_date desc, id desc"

    name = fields.Char(
        string="Cheque Number",
        required=True,
        tracking=True,
    )
    cheque_type = fields.Selection(
        [
            ("customer", "Customer Cheque (Received)"),
            ("supplier", "Supplier Cheque (Issued)"),
        ],
        string="Type",
        required=True,
        default="customer",
        tracking=True,
    )
    cheque_book_id = fields.Many2one(
        "account.cheque.book",
        string="Cheque Book",
        ondelete="cascade",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Bank Account",
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        tracking=True,
    )
    bank_id = fields.Many2one(
        "res.bank",
        string="Bank",
        tracking=True,
    )
    bank_branch = fields.Char(string="Bank Branch")
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    cheque_date = fields.Date(
        string="Cheque Date",
        required=True,
        tracking=True,
    )
    due_date = fields.Date(
        string="Due Date",
        required=True,
        tracking=True,
    )
    clear_date = fields.Date(string="Clearing Date")
    pay_to = fields.Char(string="Pay To")
    memo = fields.Char(string="Memo")
    ac_payee = fields.Boolean("A/C Payee", default=False)
    state = fields.Selection(
        [
            ("available", "Available"),
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("to_pay", "To Pay"),
            ("deposited", "Deposited"),
            ("cleared", "Cleared"),
            ("paid", "Paid"),
            ("bounced", "Bounced"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Payment",
        readonly=True,
        copy=False,
        help="Receipt payment created for this customer cheque.",
    )
    deposit_payment_id = fields.Many2one(
        "account.payment",
        string="Deposit Payment",
        readonly=True,
        copy=False,
        help="Deposit payment created when the cheque was deposited into the bank.",
    )
    received_move_id = fields.Many2one(
        "account.move",
        string="Received Journal Entry",
        readonly=True,
        ondelete="cascade",
        copy=False,
        help="Customer cheque received entry (Dr Cheque Received / Cr AR).",
    )
    deposited_move_id = fields.Many2one(
        "account.move",
        string="Deposit Journal Entry",
        readonly=True,
        ondelete="cascade",
        copy=False,
        help="Customer cheque deposit entry (Dr Bank / Cr Cheque Received).",
    )
    issue_move_id = fields.Many2one(
        "account.move",
        string="Issue Journal Entry",
        readonly=True,
        ondelete="cascade",
        copy=False,
        help="Supplier cheque issued entry (Dr AP / Cr Cheque Issued).",
    )
    paid_move_id = fields.Many2one(
        "account.move",
        string="Paid Journal Entry",
        readonly=True,
        ondelete="cascade",
        copy=False,
        help="Supplier cheque paid entry (Dr Cheque Issued / Cr Bank).",
    )
    paid_date = fields.Date(string="Paid Date", readonly=True)
    note = fields.Text(string="Notes")

    def _get_cheque_received_account_id(self):
        self.ensure_one()
        acc = self.company_id.cheque_received_account_id
        if not acc:
            raise UserError(_("Please set the Cheque Received Account in company settings."))
        return acc.id

    def _get_cheque_paid_account_id(self):
        self.ensure_one()
        acc = self.company_id.cheque_paid_account_id
        if not acc:
            raise UserError(_("Please set the Cheque Paid Account in company settings."))
        return acc.id

    def _get_bank_account_id(self):
        self.ensure_one()
        if not self.journal_id or not self.journal_id.default_account_id:
            raise UserError(_("Please set a default account on the bank journal %s.") % self.journal_id.name)
        return self.journal_id.default_account_id.id

    def _create_cheque_move(self, debit_account_id, credit_account_id, ref, date=None):
        """Create and post a journal entry for the cheque.

        :param debit_account_id: account to debit
        :param credit_account_id: account to credit
        :param ref: journal entry reference
        :param date: entry date (defaults to cheque date)
        :return: created account.move
        """
        self.ensure_one()
        move_date = date or self.cheque_date
        company_currency = self.company_id.currency_id
        amount_balance = self.currency_id._convert(
            self.amount, company_currency, self.company_id, move_date
        )
        move_vals = {
            "date": move_date,
            "ref": ref,
            "company_id": self.company_id.id,
            "journal_id": self.journal_id.id,
            "line_ids": [
                (0, 0, {
                    "name": _("Cheque #%s") % self.name,
                    "account_id": debit_account_id,
                    "partner_id": self.partner_id.id,
                    "currency_id": self.currency_id.id,
                    "amount_currency": self.amount,
                    "debit": amount_balance if amount_balance > 0 else 0.0,
                    "credit": -amount_balance if amount_balance < 0 else 0.0,
                    "date_maturity": move_date,
                }),
                (0, 0, {
                    "name": _("Cheque #%s") % self.name,
                    "account_id": credit_account_id,
                    "partner_id": self.partner_id.id,
                    "currency_id": self.currency_id.id,
                    "amount_currency": -self.amount,
                    "debit": -amount_balance if amount_balance < 0 else 0.0,
                    "credit": amount_balance if amount_balance > 0 else 0.0,
                    "date_maturity": move_date,
                }),
            ],
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()
        return move

    def _reverse_cheque_move(self, move_id_field, date=None):
        """Reverse a previously created cheque journal entry and clear the link."""
        self.ensure_one()
        move = getattr(self, move_id_field)
        if move:
            move._reverse_moves(default_values_list=[{
                "date": date or fields.Date.context_today(self),
                "ref": _("Reversal: %s") % (move.ref or ""),
            }])
            self.write({move_id_field: False})

    def _reverse_cheque_moves(self, *move_id_fields, date=None):
        """Reverse several cheque journal entries in one call.

        Used by the bounce / cancel / reset flows so every GL entry that was
        created during the cheque lifecycle is reversed, leaving no orphan
        balance on the Cheque Received / Cheque Issued accounts.
        """
        self.ensure_one()
        for move_id_field in move_id_fields:
            self._reverse_cheque_move(move_id_field, date=date)

    @api.constrains("amount")
    def _check_amount(self):
        for cheque in self:
            if cheque.amount < 0:
                raise ValidationError(_("Cheque amount cannot be negative."))
            # A blank cheque recycled back into the book (state 'available')
            # legitimately has a zero amount; any other state must be > 0.
            if cheque.amount == 0 and cheque.state != "available":
                raise ValidationError(
                    _("Cheque amount must be greater than zero.")
                )

    @api.constrains("cheque_date", "due_date")
    def _check_dates(self):
        for cheque in self:
            if cheque.cheque_date and cheque.due_date:
                if cheque.due_date < cheque.cheque_date:
                    raise ValidationError(
                        _("Due date must be after or equal to cheque date.")
                    )

    @api.constrains("name", "cheque_book_id")
    def _check_unique_cheque_no(self):
        for cheque in self:
            if cheque.cheque_book_id:
                duplicate = self.search(
                    [
                        ("name", "=", cheque.name),
                        ("cheque_book_id", "=", cheque.cheque_book_id.id),
                        ("id", "!=", cheque.id),
                    ],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _("Cheque number %s already exists in this book.") % cheque.name
                    )

    def action_confirm(self):
        for cheque in self:
            if cheque.state in ("available", "draft"):
                if cheque.cheque_type == "customer":
                    # Customer cheque received:
                    # Debit  Cheque Received
                    # Credit Accounts Receivable (partner)
                    move = cheque._create_cheque_move(
                        cheque._get_cheque_received_account_id(),
                        cheque.partner_id.property_account_receivable_id.id
                        or cheque._get_bank_account_id(),
                        _("Customer Cheque Received: %s") % cheque.name,
                    )
                    cheque.write({"state": "confirmed", "received_move_id": move.id})
                else:
                    cheque.state = "confirmed"

    def action_to_pay(self):
        for cheque in self:
            if cheque.state == "confirmed" and cheque.cheque_type == "supplier":
                # Supplier cheque issued:
                # Debit  Accounts Payable (partner)
                # Credit Cheque Issued
                move = cheque._create_cheque_move(
                    cheque.partner_id.property_account_payable_id.id
                    or cheque._get_cheque_paid_account_id(),
                    cheque._get_cheque_paid_account_id(),
                    _("Supplier Cheque Issued: %s") % cheque.name,
                )
                cheque.write({"state": "to_pay", "issue_move_id": move.id})
            elif cheque.state == "confirmed":
                cheque.state = "to_pay"

    def action_register_payment(self):
        """Receive a customer cheque through an ``account.payment`` receipt.

        This is the entry point from the cheque form. The same result can be
        achieved from an invoice with the "Register Payment" wizard by picking
        the "Cheque (Received)" payment method.
        """
        self.ensure_one()
        if self.cheque_type != "customer":
            raise UserError(_("Only customer cheques can be registered as a receipt payment."))
        journal = self.journal_id
        if not journal:
            raise UserError(_("Please select a bank journal on the cheque first."))
        method_line = self._get_cheque_payment_method_line(journal)
        payment = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.partner_id.id,
            "journal_id": journal.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "date": self.cheque_date,
            "memo": _("Cheque #%s") % self.name,
            "cheque_id": self.id,
            "payment_method_line_id": method_line.id,
        })
        # action_post keeps the cheque in sync (payment_id / received_move_id /
        # state) through the account.payment override.
        payment.action_post()
        return True

    def _get_cheque_payment_method_line(self, journal):
        """Return the "Cheque (Received)" method line of ``journal``.

        The method line is created on the fly for journals created after the
        module was installed (only pre-existing journals get it automatically).
        """
        self.ensure_one()
        method = self.env.ref(
            "od19_accounting_cheque.payment_method_od19_cheque",
            raise_if_not_found=False,
        )
        if not method:
            raise UserError(_("The 'Cheque (Received)' payment method is missing."))
        method_line = journal.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id == method
        )[:1]
        if not method_line:
            method_line = self.env["account.payment.method.line"].create({
                "name": method.name,
                "payment_method_id": method.id,
                "journal_id": journal.id,
            })
        return method_line

    def _deposit_through_payment(self):
        """Deposit a received customer cheque through an ``account.payment``.

        Creates an inbound payment that debits the bank account and credits the
        "Cheque Received" account (Dr Bank / Cr Cheque Received) and reconciles
        the two "Cheque Received" lines so the temporary account is cleared.
        """
        self.ensure_one()
        company = self.company_id
        cheque_received_account = company.cheque_received_account_id
        if not cheque_received_account:
            raise UserError(_("Please set the Cheque Received Account in company settings."))
        journal = self.journal_id or self.payment_id.journal_id
        if not journal or not journal.default_account_id:
            raise UserError(_("Please set a bank journal with a default account on the cheque."))
        deposit_date = self.due_date or self.cheque_date or fields.Date.context_today(self)
        payment = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.partner_id.id,
            "journal_id": journal.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "date": deposit_date,
            "memo": _("Cheque Deposit #%s") % self.name,
            "od19_is_cheque_deposit": True,
        })
        payment.action_post()
        payment.move_id._od19_reconcile_account_lines(
            cheque_received_account.id, self.partner_id.id
        )
        self.write({
            "state": "deposited",
            "deposited_move_id": payment.move_id.id,
            "deposit_payment_id": payment.id,
            "clear_date": deposit_date,
        })

    def action_deposit(self):
        for cheque in self:
            if cheque.cheque_type != "customer" or cheque.state not in ("confirmed", "to_pay"):
                continue
            if cheque.payment_id:
                # Cheque received through a payment: deposit it through a
                # second payment so the whole lifecycle stays in account.payment.
                cheque._deposit_through_payment()
            else:
                # Legacy flow: manual journal entry, kept for cheques that were
                # not received through a payment.
                move = cheque._create_cheque_move(
                    cheque._get_bank_account_id(),
                    cheque._get_cheque_received_account_id(),
                    _("Customer Cheque Deposited: %s") % cheque.name,
                    date=cheque.due_date or cheque.cheque_date,
                )
                cheque.write({"state": "deposited", "deposited_move_id": move.id})

    def action_clear(self):
        for cheque in self:
            if cheque.state == "deposited":
                cheque.state = "cleared"

    def action_paid(self):
        for cheque in self:
            if cheque.state in ("to_pay", "deposited", "cleared"):
                if cheque.cheque_type == "supplier" and cheque.state in ("to_pay", "deposited"):
                    # Supplier cheque paid:
                    # Debit  Cheque Issued
                    # Credit Bank
                    move = cheque._create_cheque_move(
                        cheque._get_cheque_paid_account_id(),
                        cheque._get_bank_account_id(),
                        _("Supplier Cheque Paid: %s") % cheque.name,
                        date=cheque.due_date or cheque.cheque_date,
                    )
                    cheque.write({
                        "state": "paid",
                        "paid_date": fields.Date.context_today(self),
                        "paid_move_id": move.id,
                    })
                else:
                    cheque.write({
                        "state": "paid",
                        "paid_date": fields.Date.context_today(self),
                    })

    def action_bounce(self):
        for cheque in self:
            if cheque.state in ("confirmed", "deposited", "cleared"):
                # Reverse every entry created so far (receive + deposit) so the
                # customer is debited again and the Cheque Received account is
                # fully cleared.
                cheque._reverse_cheque_moves(
                    "deposited_move_id", "received_move_id"
                )
                cheque.state = "bounced"

    def action_cancel(self):
        for cheque in self:
            if cheque.state in ("cleared", "paid", "cancelled"):
                continue
            # Reverse any created entries (received, deposited, issued, paid).
            cheque._reverse_cheque_moves(
                "deposited_move_id",
                "received_move_id",
                "issue_move_id",
                "paid_move_id",
            )
            cheque.state = "cancelled"

    def action_draft(self):
        for cheque in self:
            if cheque.state == "cancelled":
                cheque.state = "draft"

    def action_reconcile(self):
        """ตัดบัญชีลูกหนี้/เจ้าหนี้ของเช็คกับใบแจ้งหนี้เดิม (reconcile)."""
        for cheque in self:
            if cheque.cheque_type == "customer":
                move = cheque.received_move_id
                account = cheque.partner_id.property_account_receivable_id
            else:
                move = cheque.issue_move_id
                account = cheque.partner_id.property_account_payable_id
            if not move or not account:
                continue
            move._od19_reconcile_account_lines(account.id, cheque.partner_id.id)
        return True

    def action_back_to_available(self):
        for cheque in self:
            if cheque.state in ("confirmed", "cancelled") and cheque.cheque_book_id:
                # A confirmed cheque already created GL entries; reverse them
                # before clearing the cheque so no orphan balance is left.
                cheque._reverse_cheque_moves(
                    "deposited_move_id",
                    "received_move_id",
                    "issue_move_id",
                    "paid_move_id",
                )
                cheque.write({
                    "state": "available",
                    "cheque_date": False,
                    "due_date": False,
                    "pay_to": False,
                    "amount": 0.0,
                    "partner_id": self.company_id.partner_id.id,
                })

    def action_print_cheque(self):
        self.ensure_one()
        return self.env.ref(
            "od19_accounting_cheque.action_report_cheque_print"
        ).report_action(self.ids)
