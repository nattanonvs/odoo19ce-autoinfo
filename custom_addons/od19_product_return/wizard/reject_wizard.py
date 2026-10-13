from odoo import fields, models


class ProductReturnRejectWizard(models.TransientModel):
    _name = "od19.product.return.reject.wizard"
    _description = "Reject Product Return Wizard"

    return_id = fields.Many2one(
        comodel_name="od19.product.return",
        string="Product Return",
        required=True,
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        required=True,
    )

    def action_reject(self):
        self.ensure_one()
        self.return_id.write(
            {
                "state": "rejected",
                "rejection_reason": self.rejection_reason,
            }
        )
        return {"type": "ir.actions.act_window_close"}
