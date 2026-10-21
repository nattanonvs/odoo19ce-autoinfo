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
    )
    deposited_move_id = fields.Many2one(
        "account.move",
        string="Deposit Journal Entry",
        readonly=True,
        ondelete="cascade",
        copy=False,
    )
    issue_move_id = fields.Many2one(
        "account.move",
        string="Issue Journal Entry",
        readonly=True,
        ondelete="cascade",
        copy=False,
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

    @api.constrains("amount")
    def _check_amount(self):
        for cheque in self:
            if cheque.amount < 0:
                raise ValidationError(_("Cheque amount cannot be negative."))

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
                    cheque.write({"state": "confirmed", "deposited_move_id": move.id})
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

    def action_deposit(self):
        for cheque in self:
            if cheque.state in ("confirmed", "to_pay") and cheque.cheque_type == "customer":
                # Customer cheque deposited:
                # Debit  Bank
                # Credit Cheque Received
                move = cheque._create_cheque_move(
                    cheque._get_bank_account_id(),
                    cheque._get_cheque_received_account_id(),
                    _("Customer Cheque Deposited: %s") % cheque.name,
                    date=cheque.due_date or cheque.cheque_date,
                )
                cheque.write({"state": "deposited", "deposited_move_id": move.id})
            elif cheque.state in ("confirmed", "to_pay"):
                cheque.state = "deposited"

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
                        "deposited_move_id": move.id,
                    })
                else:
                    cheque.write({
                        "state": "paid",
                        "paid_date": fields.Date.context_today(self),
                    })

    def action_bounce(self):
        for cheque in self:
            if cheque.state in ("confirmed", "deposited", "cleared"):
                # Reverse the deposit entry if any
                if cheque.deposited_move_id:
                    cheque._reverse_cheque_move("deposited_move_id")
                cheque.state = "bounced"

    def action_cancel(self):
        for cheque in self:
            if cheque.state in ("cleared", "paid", "cancelled"):
                continue
            # Reverse any created entries
            if cheque.deposited_move_id:
                cheque._reverse_cheque_move("deposited_move_id")
            if cheque.issue_move_id:
                cheque._reverse_cheque_move("issue_move_id")
            cheque.state = "cancelled"

    def action_draft(self):
        for cheque in self:
            if cheque.state == "cancelled":
                cheque.state = "draft"

    def action_back_to_available(self):
        for cheque in self:
            if cheque.state in ("confirmed", "cancelled") and cheque.cheque_book_id:
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
