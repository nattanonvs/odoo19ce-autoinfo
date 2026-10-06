from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        compute="_compute_od19_entry_mode",
        store=True,
        readonly=True,
        precompute=True,
    )

    @api.depends("requisition_id")
    def _compute_od19_entry_mode(self):
        for order in self:
            order.od19_entry_mode = (
                "requisition" if order.requisition_id else "direct"
            )

    od19_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
        ],
        string="Approval State",
        default="draft",
        required=True,
        tracking=True,
        copy=False,
    )

    def action_od19_submit_for_approval(self):
        self.write({"od19_approval_state": "submitted"})

    def action_od19_approve(self):
        self.write({"od19_approval_state": "approved"})

    def button_confirm(self):
        for order in self:
            if order.od19_approval_state != "approved":
                raise UserError(
                    _("Every purchase order must be approved before confirmation.")
                )
        return super().button_confirm()
