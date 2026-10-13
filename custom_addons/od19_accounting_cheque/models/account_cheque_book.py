# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class AccountChequeBook(models.Model):
    _name = "account.cheque.book"
    _description = "Cheque Book"
    _order = "name desc"

    name = fields.Char(
        string="Book No",
        readonly=True,
        copy=False,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirm", "Confirmed"),
            ("done", "Done"),
        ],
        string="Status",
        default="draft",
        required=True,
        readonly=True,
        index=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Bank Account",
        required=True,
        index=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company",
        related="journal_id.company_id",
        store=True,
    )
    first_cheque_no = fields.Char(
        string="First Cheque No",
        required=True,
        default="1",
    )
    quantity = fields.Integer(
        string="Quantity",
        required=True,
        default=20,
    )
    last_cheque_no = fields.Char(
        string="Last Cheque No",
        index=True,
    )
    cheque_ids = fields.One2many(
        "account.cheque",
        "cheque_book_id",
        string="Cheque Leaves",
    )
    date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
    )

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        last = self.env["account.cheque.book"].search(
            [("journal_id", "=", self.journal_id.id)],
            order="last_cheque_no desc",
            limit=1,
        )
        if last and last.last_cheque_no:
            digits = re.findall(r"\d+", last.last_cheque_no)
            if digits:
                self.first_cheque_no = str(int(digits[-1]) + 1)

    def clear_cheques(self):
        self.ensure_one()
        self.cheque_ids.unlink()

    def list_cheques(self):
        self.ensure_one()
        self.cheque_ids.unlink()
        caught = re.findall(r"\d+", self.first_cheque_no)
        if not caught:
            raise ValidationError(_("The cheque number must contain at least one digit."))
        initial_number = caught[-1]
        padding = len(initial_number)
        splitted = re.split(initial_number, self.first_cheque_no)
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial = int(initial_number)

        last_cheque_no = ""
        for i in range(self.quantity):
            cheque_name = "%s%s%s" % (prefix, str(initial + i).zfill(padding), suffix)
            self.env["account.cheque"].create({
                "cheque_book_id": self.id,
                "name": cheque_name,
                "cheque_type": "supplier",
                "partner_id": self.company_id.partner_id.id,
                "amount": 0.0,
                "cheque_date": self.date,
                "due_date": self.date,
                "state": "available",
                "journal_id": self.journal_id.id,
            })
            if i == self.quantity - 1:
                last_cheque_no = cheque_name
        self.last_cheque_no = last_cheque_no
        return True

    def action_confirm(self):
        self.ensure_one()
        if not self.cheque_ids:
            raise ValidationError(_("Please generate cheque leaves first."))
        seq = self.env["ir.sequence"]
        name = seq.next_by_code("cheque.book") or "/"
        self.write({"name": name, "state": "confirm"})
        return True

    def action_done(self):
        self.write({"state": "done"})
        return True
