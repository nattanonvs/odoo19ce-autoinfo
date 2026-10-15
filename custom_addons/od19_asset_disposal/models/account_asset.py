# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountAsset(models.Model):
    _inherit = "account.asset"

    state = fields.Selection(
        selection_add=[("disposed", "Disposed")],
        ondelete={"disposed": "set open"},
        help="When an asset is disposed, the status goes in 'Disposed' "
        "and a disposal journal entry is generated.",
    )

    od19_additional_bill_ids = fields.Many2many(
        comodel_name="account.move",
        relation="od19_asset_additional_bill_rel",
        column1="asset_id",
        column2="move_id",
        string="Additional Documents",
        help="เอกสารเพิ่มเติม",
        check_company=True,
    )
    od19_supporting_move_ids = fields.Many2many(
        comodel_name="account.move",
        relation="od19_asset_supporting_move_rel",
        column1="asset_id",
        column2="move_id",
        string="Supporting Documents",
        help="เอกสารสนับสนุน",
        check_company=True,
    )
    od19_disposal_date = fields.Date(
        string="Disposal Date",
        help="วันที่จำหน่าย",
        readonly=True,
        copy=False,
    )
    od19_disposal_reason = fields.Text(
        string="Disposal Reason",
        help="เหตุผลการจำหน่าย",
        copy=False,
    )
    od19_disposal_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Disposal Journal Entry",
        readonly=True,
        copy=False,
        check_company=True,
        help="Journal entry generated when the asset was disposed.",
    )

    # ------------------------------------------------------------------
    # Disposal workflow
    # ------------------------------------------------------------------
    def action_dispose(self):
        """Dispose the asset.

        Step 1: cancel all draft depreciation moves for this asset.
        Step 2: create a disposal journal entry
                (debit accumulated depreciation, credit asset cost,
                debit asset disposal / residual value account).
        Step 3: set asset state to 'disposed'.
        Step 4: set disposal_date.
        """
        self.ensure_one()
        if self.state not in ("open", "close"):
            raise UserError(
                self.env._(
                    "You can only dispose assets that are in "
                    "'Running' or 'Close' state."
                )
            )

        # Step 1: cancel draft depreciation moves
        draft_moves = self._od19_get_draft_depreciation_moves()
        if draft_moves:
            draft_moves.button_cancel()

        # Step 2: create disposal journal entry
        disposal_move = self._od19_create_disposal_move()

        # Step 3 & 4: set state and disposal date
        self.write(
            {
                "state": "disposed",
                "od19_disposal_date": fields.Date.today(),
                "od19_disposal_move_id": disposal_move.id,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Disposal Journal Entry"),
            "res_model": "account.move",
            "res_id": disposal_move.id,
            "view_mode": "form",
            "target": "current",
        }

    def _od19_get_draft_depreciation_moves(self):
        """Return all draft depreciation moves linked to this asset."""
        self.ensure_one()
        dep_lines = self.depreciation_line_ids.filtered(
            lambda l: l.type == "depreciate" and l.move_id
        )
        moves = dep_lines.mapped("move_id").filtered(
            lambda m: m.state == "draft"
        )
        return moves

    def _od19_create_disposal_move(self):
        """Create and post the disposal journal entry.

        The entry is balanced as follows:

        * Debit  accumulated depreciation account = value_depreciated
        * Credit asset cost account                = depreciation_base
        * Debit  asset disposal / residual account = value_residual

        value_residual = depreciation_base - value_depreciated, so the
        total debit equals the total credit.
        """
        self.ensure_one()
        profile = self.profile_id
        company = self.company_id
        currency = company.currency_id

        if not profile.account_residual_value_id:
            raise UserError(
                self.env._(
                    "Please configure the Residual Value Account on the "
                    "asset profile '%s' before disposing the asset."
                )
                % profile.name
            )

        depreciated = self.value_depreciated
        residual = self.value_residual
        asset_cost = self.depreciation_base

        ctx = dict(
            self.env.context,
            allow_asset=True,
            check_move_validity=False,
        )
        move_vals = {
            "date": fields.Date.today(),
            "ref": self.env._("Disposal of %s", self.display_name),
            "journal_id": profile.journal_id.id,
            "company_id": company.id,
        }
        move = self.env["account.move"].with_context(**ctx).create(move_vals)

        move_lines = []
        # Debit accumulated depreciation
        if not currency.is_zero(depreciated):
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": self.env._(
                            "Accumulated Depreciation - %s", self.name
                        ),
                        "account_id": profile.account_depreciation_id.id,
                        "debit": depreciated,
                        "credit": 0.0,
                        "asset_id": self.id,
                        "asset_profile_id": False,
                        "partner_id": self.partner_id.id or False,
                    },
                )
            )
        # Credit asset cost
        if not currency.is_zero(asset_cost):
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": self.env._("Asset Cost - %s", self.name),
                        "account_id": profile.account_asset_id.id,
                        "debit": 0.0,
                        "credit": asset_cost,
                        "asset_id": self.id,
                        "asset_profile_id": False,
                        "partner_id": self.partner_id.id or False,
                    },
                )
            )
        # Debit disposal / residual value account (balancing amount)
        if not currency.is_zero(residual):
            move_lines.append(
                (
                    0,
                    0,
                    {
                        "name": self.env._("Asset Disposal - %s", self.name),
                        "account_id": profile.account_residual_value_id.id,
                        "debit": residual,
                        "credit": 0.0,
                        "asset_id": self.id,
                        "asset_profile_id": False,
                        "partner_id": self.partner_id.id or False,
                    },
                )
            )

        move.with_context(**ctx).write({"line_ids": move_lines})
        move.action_post()
        return move

    # ------------------------------------------------------------------
    # Disposal revert
    # ------------------------------------------------------------------
    def action_revert_disposal(self):
        """Revert the disposal of the asset.

        Only available when state = 'disposed'. Reverses the disposal
        journal entry, sets the asset state back to 'open' and clears
        the disposal date.
        """
        self.ensure_one()
        if self.state != "disposed":
            raise UserError(
                self.env._("You can only revert assets that are disposed.")
            )
        if not self.od19_disposal_move_id:
            raise UserError(
                self.env._("No disposal journal entry found to reverse.")
            )

        # Reverse the disposal move (this also cancels the original move).
        # allow_asset=True is required so that the reverse move lines can
        # keep the asset_id set without raising the OCA protection error.
        reversal_move = self.od19_disposal_move_id.with_context(
            allow_asset=True
        )._reverse_moves(
            default_values_list=[
                {
                    "date": fields.Date.today(),
                    "ref": self.env._(
                        "Reversal of %s", self.od19_disposal_move_id.ref
                    ),
                }
            ],
            cancel=True,
        )

        # Clear disposal info and reopen the asset
        self.write(
            {
                "state": "open",
                "od19_disposal_date": False,
                "od19_disposal_move_id": False,
            }
        )

        res_id = reversal_move.id if reversal_move else False
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Disposal Reversal Journal Entry"),
            "res_model": "account.move",
            "res_id": res_id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------
    # Safe depreciation cron
    # ------------------------------------------------------------------
    @api.model
    def od19_safe_depreciation(self):
        """Monthly cron: compute depreciation for every open asset.

        Each asset is processed inside its own savepoint so that a
        failure on one asset does not prevent the others from being
        computed. Errors are logged and the cron continues.
        """
        assets = self.search(
            [("state", "=", "open"), ("active", "=", True)]
        )
        today = fields.Date.today()
        for asset in assets:
            try:
                with self.env.cr.savepoint():
                    asset.compute_depreciation_board()
                    asset._compute_entries(today)
            except Exception:
                _logger.exception(
                    "Safe depreciation failed for asset '%s' (id=%s).",
                    asset.display_name,
                    asset.id,
                )
        return True
