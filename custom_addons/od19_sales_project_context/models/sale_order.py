from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_sale_mode = fields.Selection(
        [("one_time", "One-time"), ("contract", "Contract-based")],
        string="Sale Mode",
        default="one_time",
        required=True,
        tracking=True,
    )
    od19_project_id = fields.Many2one(
        "project.project",
        string="Linked Project",
        tracking=True,
    )
    od19_project_owner_id = fields.Many2one(
        "res.partner",
        string="Project Owner",
        tracking=True,
    )

    @api.onchange("od19_project_id")
    def _onchange_od19_project_id(self):
        for order in self:
            if order.od19_project_id:
                order.od19_project_owner_id = (
                    order.od19_project_id.project_owner_id
                )
            else:
                order.od19_project_owner_id = False

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

    @api.constrains("od19_project_owner_id", "od19_sale_mode")
    def _check_project_owner_role(self):
        """A project owner must be a contact flagged as Project Owner.

        Enforced at model level so the rule holds regardless of the view
        domain (API imports, data loads, automated flows).
        """
        for order in self:
            owner = order.od19_project_owner_id
            if owner and not owner.od19_is_project_owner:
                raise ValidationError(
                    "%s is not flagged as a Project Owner contact."
                    % owner.display_name
                )

    def action_open_project_pnl_analysis(self):
        """Open the pre-quote cost & profit analysis for the linked project."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "od19_sales_project_context.action_od19_sale_order_pnl_analysis"
        )
        action["context"] = {"default_sale_order_id": self.id}
        return action
