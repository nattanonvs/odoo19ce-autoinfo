# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
    paid_date = fields.Date(string="Paid Date", readonly=True)
    note = fields.Text(string="Notes")

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
                cheque.state = "confirmed"

    def action_to_pay(self):
        for cheque in self:
            if cheque.state == "confirmed":
                cheque.state = "to_pay"

    def action_deposit(self):
        for cheque in self:
            if cheque.state in ("confirmed", "to_pay"):
                cheque.state = "deposited"

    def action_clear(self):
        for cheque in self:
            if cheque.state == "deposited":
                cheque.state = "cleared"

    def action_paid(self):
        for cheque in self:
            if cheque.state in ("to_pay", "deposited", "cleared"):
                cheque.write({
                    "state": "paid",
                    "paid_date": fields.Date.context_today(self),
                })

    def action_bounce(self):
        for cheque in self:
            if cheque.state in ("confirmed", "deposited", "cleared"):
                cheque.state = "bounced"

    def action_cancel(self):
        for cheque in self:
            if cheque.state in ("cleared", "paid", "cancelled"):
                continue
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
