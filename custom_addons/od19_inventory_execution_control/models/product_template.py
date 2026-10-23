from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    od19_tracking_required = fields.Boolean(
        string="Tracking Required",
        compute="_compute_od19_tracking_required",
        store=True,
        readonly=True,
    )
    od19_tracking_required_reason = fields.Char(
        string="Tracking Requirement Reason",
    )

    @api.depends("tracking", "cost_method", "categ_id")
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

    # ``cost_method`` is a non-stored computed field (it mirrors the product
    # category's costing method), so it cannot be used in ``@api.constrains``.
    # Constrain on its source field ``categ_id`` instead, which triggers the
    # check whenever the costing method changes.
    @api.constrains("tracking", "categ_id")
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
