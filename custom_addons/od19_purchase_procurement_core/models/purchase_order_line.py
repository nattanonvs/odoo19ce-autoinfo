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
        compute="_compute_od19_item_kind",
        store=True,
        readonly=True,
        precompute=True,
    )
    od19_project_id = fields.Many2one("od19.sales.project", string="Project")

    @api.depends("display_type", "product_id", "product_id.type")
    def _compute_od19_item_kind(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.od19_item_kind = False
            elif line.product_id.type == "service":
                line.od19_item_kind = "service"
            else:
                line.od19_item_kind = "product"

    @api.constrains("od19_procurement_purpose", "od19_project_id")
    def _check_project_reference(self):
        for line in self:
            if line.display_type:
                continue
            if line.od19_procurement_purpose == "project" and not line.od19_project_id:
                raise ValidationError(
                    "Project-linked procurement lines must reference a project."
                )
