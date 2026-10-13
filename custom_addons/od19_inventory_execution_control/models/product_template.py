from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    od19_tracking_required = fields.Boolean(
        compute="_compute_od19_tracking_required",
        store=True,
        readonly=True,
    )
    od19_tracking_required_reason = fields.Char()

    @api.depends("tracking", "cost_method")
    def _compute_od19_tracking_required(self):
        for template in self:
            if template.cost_method == "fifo":
                template.od19_tracking_required = True
                template.od19_tracking_required_reason = _(
                    "FIFO costing requires lot or serial tracking."
                )
            else:
                template.od19_tracking_required = template.tracking != "none"
                template.od19_tracking_required_reason = False

    @api.constrains("tracking", "cost_method")
    def _check_fifo_requires_lot_tracking(self):
        """FIFO-costed products must be tracked by lot or serial number.

        Lot/serial tracking is required so that FIFO valuation can be matched
        to the specific lot being moved, matching the legacy dtr_stock_fifo
        behaviour.
        """
        for template in self:
            if (
                template.cost_method == "fifo"
                and template.tracking == "none"
                and template.is_storable
            ):
                raise ValidationError(
                    _(
                        "Product '%s' uses FIFO costing. FIFO valuation "
                        "requires lot or serial tracking; please set "
                        "'Track Lots' or 'Track Serial Numbers' on the "
                        "product."
                    )
                    % template.display_name
                )
