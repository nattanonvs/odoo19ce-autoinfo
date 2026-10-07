from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    od19_tracking_required = fields.Boolean(
        compute="_compute_od19_tracking_required",
        store=True,
        readonly=True,
    )
    od19_tracking_required_reason = fields.Char()

    @api.depends("tracking")
    def _compute_od19_tracking_required(self):
        for template in self:
            template.od19_tracking_required = template.tracking != "none"
