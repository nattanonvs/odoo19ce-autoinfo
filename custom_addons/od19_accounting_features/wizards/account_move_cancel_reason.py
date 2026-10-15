# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMoveCancelReason(models.TransientModel):
    _name = "od19.account.move.cancel.reason"
    _description = "Cancel Reason Wizard"

    reason = fields.Text(
        string="Cancel Reason",
        required=True,
        help="Reason for cancelling this journal entry.",
    )
    move_ids = fields.Many2many(
        comodel_name="account.move",
        string="Journal Entries",
        help="The journal entries that will be cancelled.",
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids") or []
        active_model = self.env.context.get("active_model")
        if active_model == "account.move" and active_ids:
            defaults["move_ids"] = [(6, 0, active_ids)]
        return defaults

    def action_confirm(self):
        self.ensure_one()
        if not self.move_ids:
            raise UserError(self.env._("No journal entries selected."))
        if not self.reason or not self.reason.strip():
            raise UserError(self.env._("Please provide a cancel reason."))

        moves = self.move_ids.filtered(lambda m: m.state in ("draft", "posted"))
        if not moves:
            raise UserError(
                self.env._("None of the selected entries can be cancelled.")
            )

        # Store the reason on every move before cancelling.
        moves.write({"od19_cancel_reason": self.reason.strip()})

        # Call the real cancellation, skipping the wizard loop.
        moves.with_context(od19_skip_reason=True).button_cancel()

        return {"type": "ir.actions.act_window_close"}
