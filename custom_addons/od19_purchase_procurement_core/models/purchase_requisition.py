from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    od19_entry_mode = fields.Selection(
        [
            ("requisition", "Purchase Requisition"),
            ("direct", "Direct Purchase Order"),
        ],
        string="Entry Mode",
        default="requisition",
        required=True,
        tracking=True,
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

    def action_confirm(self):
        self.ensure_one()
        if self.od19_approval_state != "approved":
            raise UserError(
                _("Every purchase requisition must be approved before confirmation.")
            )
        return super().action_confirm()
