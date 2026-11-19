# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from markupsafe import Markup

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _od19_get_merge_lines(self, only_targets=False):
        """Return purchase bill lines that target an existing asset.

        When ``only_targets`` is True only lines that are not yet linked to
        their target asset are returned (used before posting). Otherwise the
        lines already linked to their target asset are returned.
        """
        self.ensure_one()
        if not self.is_purchase_document():
            return self.env["account.move.line"]
        lines = self.line_ids.filtered(
            lambda line: line.od19_target_asset_id and not line.tax_line_id
        )
        if only_targets:
            return lines.filtered(lambda line: not line.asset_id)
        return lines.filtered(
            lambda line: line.asset_id == line.od19_target_asset_id
        )

    def action_post(self):
        # Pre-link the merge lines to their target asset so the standard OCA
        # logic skips creating a brand-new asset for them.
        for move in self:
            for line in move._od19_get_merge_lines(only_targets=True):
                target = line.od19_target_asset_id
                if move not in target.od19_additional_bill_ids:
                    target._od19_check_can_merge(line)
                line.with_context(allow_asset=True).asset_id = target.id

        ret_val = super().action_post()

        # Then add the bill value into the existing asset.
        for move in self:
            for line in move._od19_get_merge_lines():
                target = line.od19_target_asset_id
                if move in target.od19_additional_bill_ids:
                    continue
                target._od19_merge_purchase_value(line.balance, move)
                move.message_post(
                    body=self.env._(
                        "The amount %(amount)s was merged into the asset %(asset)s.",
                        amount=line.balance,
                        asset=Markup(
                            """<a href=# data-oe-model=account.asset"""
                            f""" data-oe-id={target.id}"""
                            f""">{target.display_name}</a>"""
                        ),
                    )
                )
        return ret_val

    def button_draft(self):
        # Reverse the merge before the standard draft reset tries to unlink
        # the (not yet draft) target asset.
        for move in self:
            for line in move._od19_get_merge_lines():
                line.od19_target_asset_id._od19_unmerge_purchase_value(
                    line.balance, move
                )
                line.with_context(
                    allow_asset=True, allow_asset_removal=True
                ).asset_id = False
        return super().button_draft()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    od19_target_asset_id = fields.Many2one(
        comodel_name="account.asset",
        string="Merge into Asset",
        check_company=True,
        copy=False,
        help="Select an existing asset to merge this bill line's value into "
        "instead of creating a new asset.",
    )
