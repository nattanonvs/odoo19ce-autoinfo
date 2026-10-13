from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    stamp_date = fields.Date(
        string="Stamp Date",
        tracking=True,
        help="Date used for the CONFIRMED stamp printed on the quotation.",
    )
    stamp_code = fields.Char(
        string="Stamp Code",
        tracking=True,
        help="Code shown in the CONFIRMED stamp (e.g. project/contract code).",
    )
    confirmed_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Confirmed By",
        readonly=True,
        copy=False,
        tracking=True,
        help="User who confirmed this sale order (shown in the stamp SIGN field).",
    )

    def action_confirm(self):
        """Capture the confirming user for the CONFIRMED stamp, then confirm."""
        for order in self:
            if order.state in ("draft", "sent") and not order.confirmed_by_id:
                order.confirmed_by_id = self.env.uid
        return super().action_confirm()
