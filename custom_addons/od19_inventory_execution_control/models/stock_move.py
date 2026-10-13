from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class StockMove(models.Model):
    _inherit = "stock.move"

    od19_reference_document = fields.Char(
        compute="_compute_od19_reference_document",
        store=True,
        readonly=True,
    )
    backdate_date = fields.Date(
        string="Backdate",
        copy=False,
        help="If set, the valuation layer and accounting entries for this "
        "move will use this date instead of the move date.",
    )

    @api.depends("origin", "picking_id.origin")
    def _compute_od19_reference_document(self):
        for move in self:
            move.od19_reference_document = move.origin or move.picking_id.origin or False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("backdate_date"):
                self._check_backdate_access()
        return super().create(vals_list)

    def write(self, vals):
        if "backdate_date" in vals and vals["backdate_date"]:
            self._check_backdate_access()
        return super().write(vals)

    def _check_backdate_access(self):
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(
                _(
                    "Only inventory managers are allowed to backdate stock "
                    "moves."
                )
            )

    def _action_done(self, cancel_backorder=False):
        """Apply the backdate to the move date before validation.

        By setting ``date`` on the move before the super call, the generated
        stock.valuation.layer rows and (for real-time valuation) the
        account.move entries inherit the backdated date.
        """
        backdated_moves = self.filtered("backdate_date")
        original_dates = {}
        for move in backdated_moves:
            original_dates[move.id] = move.date
            move.date = move.backdate_date
        try:
            res = super()._action_done(cancel_backorder=cancel_backorder)
        finally:
            # Restore the original date on the move record; the SVL /
            # account.move already carry the backdated date.
            for move in backdated_moves:
                move.write({"date": original_dates[move.id]})
        return res
