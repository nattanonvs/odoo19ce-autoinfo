# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    od19_prepare_payment = fields.Boolean(
        string="เตรียมจ่าย (ไม่ Post ทันที) / Prepare payment",
        help="Create the payment as a draft so it can be prepared and "
        "approved before posting and settling the invoice.",
    )

    def _post_payments(self, to_process, edit_mode=False):
        if self.od19_prepare_payment:
            self._od19_stage_prepared_payments(to_process)
            return
        return super()._post_payments(to_process, edit_mode=edit_mode)

    def _reconcile_payments(self, to_process, edit_mode=False):
        if self.od19_prepare_payment:
            return
        return super()._reconcile_payments(to_process, edit_mode=edit_mode)

    def _od19_stage_prepared_payments(self, to_process):
        """Keep the created payments in draft and remember what to settle.

        The standard flow posts and reconciles immediately. When the payment is
        staged instead, the source document lines are stored on the payment so
        that ``action_post()`` can reconcile them once the payment is posted.
        """
        for vals in to_process:
            payment = vals.get("payment")
            if not payment:
                continue
            lines = vals.get("to_reconcile")
            if lines:
                payment.od19_pending_reconcile_line_ids = [Command.set(lines.ids)]
            # ``account.payment.create()`` already builds the journal entry and
            # flags the payment as ``in_process``, even though that entry is
            # still unposted. The prepare step is materialised by the plain
            # ``draft`` state, so put it back: nothing hits the ledger before the
            # payment is posted.
            if payment.state != "draft":
                payment.state = "draft"
