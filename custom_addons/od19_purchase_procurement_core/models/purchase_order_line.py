from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_procurement_purpose = fields.Selection(
        [
            ("internal", "Internal"),
            ("project", "Project / Sale-linked"),
        ],
        string="Procurement Purpose",
        default="internal",
        required=True,
    )
    od19_item_kind = fields.Selection(
        [
            ("product", "Product"),
            ("service", "Service"),
        ],
        string="Item Kind",
        default="product",
        required=True,
    )
    od19_project_id = fields.Many2one("od19.sales.project", string="Project")
    od19_sale_order_id = fields.Many2one("sale.order", string="Sale Order")

    @api.constrains("od19_procurement_purpose", "od19_project_id")
    def _check_project_reference(self):
        for line in self:
            if line.display_type:
                continue
            if line.od19_procurement_purpose == "project" and not line.od19_project_id:
                raise ValidationError(
                    "Project-linked procurement lines must reference a project."
                )
