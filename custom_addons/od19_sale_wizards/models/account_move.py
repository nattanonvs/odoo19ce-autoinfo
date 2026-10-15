# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Account.move extension: downpayment invoice linking fields.

Stores the originating Sale Order or Purchase Order name on downpayment
invoices so users can trace back where an advance payment came from.
"""
from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_downpayment_origin = fields.Char(
        string="Downpayment Origin / ต้นทางเงินมัดจำ",
        copy=False,
        help=(
            "Name of the Sale Order or Purchase Order that this "
            "downpayment invoice was created from."
        ),
    )
    od19_downpayment_source = fields.Selection(
        selection=[
            ("sale", "Sale Order / ใบสั่งขาย"),
            ("purchase", "Purchase Order / ใบสั่งซื้อ"),
        ],
        string="Downpayment Source / แหล่งเงินมัดจำ",
        copy=False,
        help="Whether this downpayment invoice came from a SO or a PO.",
    )
    od19_source_po_name = fields.Char(
        string="Source PO Name / เลขที่ใบสั่งซื้อ",
        copy=False,
        help="Purchase Order name that this downpayment invoice relates to.",
    )

    def action_open_get_sale_lines(self):
        """Open the Get Sale Order Lines wizard for the current invoice."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_(
                "You can only get sale order lines on a draft invoice."
            ))
        if self.move_type != "out_invoice":
            raise UserError(_(
                "This action is only available on customer invoices."
            ))
        return {
            "type": "ir.actions.act_window",
            "name": _("Get Sale Order Lines / ดึงรายการจากใบสั่งขาย"),
            "res_model": "od19.account.invoice.get.sale.lines",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_id": self.id,
                "active_id": self.id,
                "active_ids": self.ids,
                "active_model": "account.move",
            },
        }
