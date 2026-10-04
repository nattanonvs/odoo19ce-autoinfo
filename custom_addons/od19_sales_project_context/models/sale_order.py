from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_sale_mode = fields.Selection(
        [("one_time", "One-time"), ("contract", "Contract-based")],
        default="one_time",
        required=True,
        tracking=True,
    )
    od19_project_id = fields.Many2one("od19.sales.project", tracking=True)
    od19_project_owner_id = fields.Many2one("res.partner", tracking=True)

    @api.constrains("od19_project_id", "od19_project_owner_id")
    def _check_project_owner_consistency(self):
        for order in self:
            if (
                order.od19_project_id
                and order.od19_project_owner_id
                and order.od19_project_id.project_owner_id != order.od19_project_owner_id
            ):
                raise ValidationError(
                    "Project owner on sale order must match project owner on selected project."
                )
