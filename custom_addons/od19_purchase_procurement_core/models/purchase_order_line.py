from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    _OD19_MATERIAL_FIELDS = {
        "date_planned",
        "discount",
        "name",
        "od19_budget_reference",
        "od19_procurement_purpose",
        "od19_project_id",
        "price_unit",
        "product_id",
        "product_qty",
        "product_uom_id",
        "sale_line_id",
        "taxes_id",
    }

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
    od19_budget_reference = fields.Char(string="Budget Reference")
    od19_budget_warning = fields.Boolean(
        string="Budget Warning",
        compute="_compute_od19_budget_warning",
        store=True,
    )
    od19_budget_warning_message = fields.Char(
        string="Budget Warning Message",
        compute="_compute_od19_budget_warning",
        store=True,
    )
    od19_requires_service_acceptance = fields.Boolean(
        string="Requires Service Acceptance",
        compute="_compute_od19_requires_service_acceptance",
        store=True,
    )

    @api.depends("display_type", "product_id", "product_id.type")
    def _compute_od19_item_kind(self):
        for line in self:
            if line.display_type or not line.product_id:
                line.od19_item_kind = False
            elif line.product_id.type == "service":
                line.od19_item_kind = "service"
            else:
                line.od19_item_kind = "product"

    @api.depends("od19_item_kind", "display_type")
    def _compute_od19_requires_service_acceptance(self):
        for line in self:
            line.od19_requires_service_acceptance = (
                not line.display_type and line.od19_item_kind == "service"
            )

    @api.depends("od19_procurement_purpose", "od19_budget_reference", "display_type")
    def _compute_od19_budget_warning(self):
        for line in self:
            if line.display_type:
                line.od19_budget_warning = False
                line.od19_budget_warning_message = False
            elif (
                line.od19_procurement_purpose == "project"
                and not line.od19_budget_reference
            ):
                line.od19_budget_warning = True
                line.od19_budget_warning_message = (
                    "Project-linked procurement lines should carry a budget reference."
                )
            else:
                line.od19_budget_warning = False
                line.od19_budget_warning_message = False

    @api.constrains("od19_procurement_purpose", "od19_project_id")
    def _check_project_reference(self):
        for line in self:
            if line.display_type:
                continue
            if line.od19_procurement_purpose == "project" and not line.od19_project_id:
                raise ValidationError(
                    "Project-linked procurement lines must reference a project."
                )

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("od19_skip_approval_invalidation"):
            order_ids = [vals.get("order_id") for vals in vals_list if vals.get("order_id")]
            if order_ids:
                self.env["purchase.order"].browse(order_ids)._od19_ensure_no_post_confirm_material_edit()
        lines = super().create(vals_list)
        if not self.env.context.get("od19_skip_approval_invalidation"):
            lines.order_id._od19_reset_approval_if_needed()
        return lines

    def write(self, vals):
        reset_candidates = (
            self.order_id
            if (
                not self.env.context.get("od19_skip_approval_invalidation")
                and bool(self._OD19_MATERIAL_FIELDS.intersection(vals))
            )
            else self.env["purchase.order"]
        )
        if reset_candidates:
            reset_candidates._od19_ensure_no_post_confirm_material_edit()
        result = super().write(vals)
        if reset_candidates:
            reset_candidates._od19_reset_approval_if_needed()
        return result

    def unlink(self):
        reset_candidates = (
            self.order_id
            if not self.env.context.get("od19_skip_approval_invalidation")
            else self.env["purchase.order"]
        )
        if reset_candidates:
            reset_candidates._od19_ensure_no_post_confirm_material_edit()
        result = super().unlink()
        if reset_candidates:
            reset_candidates._od19_reset_approval_if_needed()
        return result
