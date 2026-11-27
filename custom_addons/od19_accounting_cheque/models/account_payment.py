# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    cheque_id = fields.Many2one(
        "account.cheque",
        string="Received Cheque",
        copy=False,
        help="Customer cheque this receipt was created for.",
    )
    cheque_paid_id = fields.Many2one(
        "account.cheque",
        string="Paid Cheque",
        copy=False,
    )
    pay_to = fields.Char(string="Pay To")
    # Set on the internal payment created when a received cheque is deposited,
    # so the outstanding/destination accounts are computed below.
    od19_is_cheque_deposit = fields.Boolean(
        string="Cheque Deposit",
        copy=False,
    )

    @api.depends(
        "payment_method_line_id",
        "journal_id",
        "company_id",
        "od19_is_cheque_deposit",
    )
    def _compute_outstanding_account_id(self):
        # EXTENDS 'account'
        super()._compute_outstanding_account_id()
        for payment in self:
            if payment.payment_method_code == "od19_cheque":
                # Receiving a customer cheque parks the money on the dedicated
                # "Cheque Received" account until the cheque is deposited.
                cheque_account = payment.company_id.cheque_received_account_id
                if cheque_account:
                    payment.outstanding_account_id = cheque_account
            elif payment.od19_is_cheque_deposit:
                # Depositing the cheque debits the bank account directly so the
                # payment is immediately considered paid and no statement line
                # is needed to move the amount out of the outstanding account.
                if payment.journal_id.default_account_id:
                    payment.outstanding_account_id = payment.journal_id.default_account_id

    @api.depends("journal_id", "partner_id", "partner_type", "od19_is_cheque_deposit")
    def _compute_destination_account_id(self):
        # EXTENDS 'account'
        super()._compute_destination_account_id()
        for payment in self:
            if payment.od19_is_cheque_deposit:
                # Counterpart of the deposit is the "Cheque Received" account:
                # Dr Bank / Cr Cheque Received.
                payment.destination_account_id = payment.company_id.cheque_received_account_id

    def action_post(self):
        res = super().action_post()
        for rec in self:
            if rec.cheque_paid_id:
                rec.cheque_paid_id.write({
                    "pay_to": rec.pay_to or rec.partner_id.name,
                    "cheque_date": rec.date,
                    "due_date": rec.date,
                    "amount": rec.amount,
                    "state": "confirmed",
                    "partner_id": rec.partner_id.id,
                    "journal_id": rec.journal_id.id,
                    "currency_id": rec.currency_id.id,
                })
            if rec.cheque_id and not rec.od19_is_cheque_deposit:
                # A customer cheque received through a payment: keep the cheque
                # in sync with the posted receipt entry.
                rec.cheque_id.write({
                    "payment_id": rec.id,
                    "received_move_id": rec.move_id.id,
                    "state": "confirmed",
                })
        return res
