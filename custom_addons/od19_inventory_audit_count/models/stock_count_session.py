from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockCountSession(models.Model):
    _name = "od19.stock.count.session"
    _description = "OD19 Stock Count Session"

    name = fields.Char(required=True)
    location_id = fields.Many2one("stock.location", required=True)
    state = fields.Selection(
        selection=[
            ("scheduled", "Scheduled"),
            ("counted", "Counted"),
            ("variance", "Variance"),
            ("adjusted", "Adjusted"),
            ("reviewed", "Reviewed"),
        ],
        required=True,
        default="scheduled",
    )
    line_ids = fields.One2many("od19.stock.count.line", "session_id")


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
