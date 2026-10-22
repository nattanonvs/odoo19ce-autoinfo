from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


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
                self._check_backdate_access(vals["backdate_date"])
        return super().create(vals_list)

    def write(self, vals):
        if "backdate_date" in vals and vals["backdate_date"]:
            self._check_backdate_access(vals["backdate_date"])
        return super().write(vals)

    def _check_backdate_access(self, backdate):
        """Validate a backdate value before it is stored or applied.

        Only inventory managers may backdate, the date may not be in the
        future, and it may not fall on or before the company's locked
        accounting dates (period / fiscal year / hard lock).
        """
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(
                _(
                    "Only inventory managers are allowed to backdate stock "
                    "moves."
                )
            )
        if not backdate:
            return
        backdate = fields.Date.to_date(backdate)
        today = fields.Date.context_today(self)
        if backdate > today:
            raise UserError(
                _("Backdate %(date)s cannot be in the future.", date=backdate)
            )
        company = self.env.company
        lock_dates = [
            lock_date
            for lock_date in (
                getattr(company, "hard_lock_date", None),
                getattr(company, "fiscalyear_lock_date", None),
                getattr(company, "period_lock_date", None),
            )
            if lock_date
        ]
        if lock_dates:
            latest_lock = max(lock_dates)
            if backdate <= latest_lock:
                raise UserError(
                    _(
                        "Backdate %(date)s falls on or before the locked "
                        "accounting date %(lock)s. The accounting period is "
                        "closed.",
                        date=backdate,
                        lock=latest_lock,
                    )
                )

    def _action_done(self, cancel_backorder=False):
        """Apply the backdate to the move date before validation.

        By setting ``date`` on the move before the super call, the generated
        valuation and (for real-time valuation) the account.move entries
        inherit the backdated date. The backdate is re-validated here so a
        period that was locked after the move was created cannot be bypassed.
        """
        backdated_moves = self.filtered("backdate_date")
        for move in backdated_moves:
            move._check_backdate_access(move.backdate_date)
        original_dates = {}
        for move in backdated_moves:
            original_dates[move.id] = move.date
            move.date = move.backdate_date
        try:
            res = super()._action_done(cancel_backorder=cancel_backorder)
        finally:
            # Restore the original date on the move record; the valuation /
            # account.move entries already carry the backdated date.
            for move in backdated_moves:
                move.write({"date": original_dates[move.id]})
        return res
