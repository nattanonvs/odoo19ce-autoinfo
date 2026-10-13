from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class StockCountSession(models.Model):
    _name = "od19.stock.count.session"
    _description = "OD19 Stock Count Session"

    name = fields.Char(required=True)
    location_id = fields.Many2one("stock.location", required=True)
    state = fields.Selection(
        selection=[
            ("scheduled", "Scheduled"),
            ("counted", "Counted"),
            ("pending_approval", "Pending Approval"),
            ("adjusted", "Adjusted"),
            ("reviewed", "Reviewed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="scheduled",
        tracking=True,
    )
    line_ids = fields.One2many("od19.stock.count.line", "session_id")
    variance_count = fields.Integer(
        string="Variances",
        compute="_compute_variance_count",
        help="Number of count lines with a non-zero variance.",
    )
    approved_by = fields.Many2one(
        "res.users", string="Approved By", readonly=True, copy=False
    )

    @api.depends("line_ids.variance_qty")
    def _compute_variance_count(self):
        for session in self:
            session.variance_count = len(
                session.line_ids.filtered(lambda l: l.variance_qty)
            )

    def action_mark_counted(self):
        for session in self:
            if session.state != "scheduled":
                raise UserError(
                    _("Only scheduled count sessions can be marked as counted.")
                )
            if not session.line_ids:
                raise UserError(
                    _("Please add at least one count line before marking as counted.")
                )
            session.state = "counted"

    def action_submit_for_approval(self):
        for session in self:
            if session.state != "counted":
                raise UserError(
                    _("Only counted sessions can be submitted for approval.")
                )
            session.state = "pending_approval"

    def action_create_adjustment(self):
        """Create stock.quant adjustments for every counted variance.

        For each count line, the system quantity is set to the counted
        quantity. This updates the quant and (for real-time valuation
        categories) posts the corresponding valuation and accounting
        entries through Odoo's standard inventory adjustment mechanism.
        """
        self.ensure_one()
        if self.state != "pending_approval":
            raise UserError(
                _("Adjustments can only be created for sessions pending approval.")
            )
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(
                _("Only inventory managers can approve count adjustments.")
            )
        for line in self.line_ids:
            if line.variance_qty:
                line.quant_id.inventory_quantity = line.counted_qty
                line.quant_id.action_apply_inventory()
        self.approved_by = self.env.user
        self.state = "adjusted"

    def action_mark_reviewed(self):
        for session in self:
            if session.state != "adjusted":
                raise UserError(
                    _("Only adjusted sessions can be marked as reviewed.")
                )
            session.state = "reviewed"

    def action_cancel(self):
        for session in self:
            if session.state in ("adjusted", "reviewed"):
                raise UserError(
                    _("Adjusted or reviewed sessions cannot be cancelled.")
                )
            session.state = "cancelled"

    def action_reset_to_scheduled(self):
        for session in self:
            if session.state != "cancelled":
                raise UserError(
                    _("Only cancelled sessions can be reset to scheduled.")
                )
            session.state = "scheduled"


class StockCountLine(models.Model):
    _name = "od19.stock.count.line"
    _description = "OD19 Stock Count Line"

    session_id = fields.Many2one(
        "od19.stock.count.session",
        required=True,
        ondelete="cascade",
    )
    quant_id = fields.Many2one("stock.quant", required=True)
    product_id = fields.Many2one(
        "product.product",
        related="quant_id.product_id",
        store=True,
    )
    system_qty = fields.Float(required=True, readonly=True)
    counted_qty = fields.Float(required=True)
    variance_qty = fields.Float(
        compute="_compute_variance_qty",
        store=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "system_qty" not in vals and vals.get("quant_id"):
                quant = self.env["stock.quant"].browse(vals["quant_id"])
                vals["system_qty"] = quant.quantity
        return super().create(vals_list)

    def write(self, vals):
        if "quant_id" in vals and "system_qty" not in vals:
            quant = self.env["stock.quant"].browse(vals["quant_id"])
            vals = dict(vals, system_qty=quant.quantity)
        return super().write(vals)

    @api.depends("counted_qty", "system_qty")
    def _compute_variance_qty(self):
        for line in self:
            line.variance_qty = line.counted_qty - line.system_qty

    @api.constrains("session_id", "quant_id")
    def _check_quant_matches_session_location(self):
        for line in self:
            if line.session_id and line.quant_id:
                if line.quant_id.location_id != line.session_id.location_id:
                    raise ValidationError(
                        _(
                            "Count line quant must belong to the same location as the session."
                        )
                    )

    @api.constrains("session_id", "quant_id")
    def _check_quant_is_unique_per_session(self):
        for line in self:
            if not line.session_id or not line.quant_id:
                continue
            duplicate_count = self.search_count(
                [
                    ("session_id", "=", line.session_id.id),
                    ("quant_id", "=", line.quant_id.id),
                    ("id", "!=", line.id),
                ]
            )
            if duplicate_count:
                raise ValidationError(
                    _("A quant can only be counted once within the same session.")
                )
