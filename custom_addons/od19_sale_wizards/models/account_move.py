# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Account.move extension: downpayment invoice linking fields.

Stores the originating Sale Order or Purchase Order name on downpayment
invoices so users can trace back where an advance payment came from.
"""
from odoo import fields, models


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
        """Open the central document pull wizard (flow 3).

        Kept for backward compatibility: the former dedicated wizard
        (``od19.account.invoice.get.sale.lines``) is replaced by the shared
        ``od19_document_pull`` mechanism, so all "source document" pulls now
        behave (and are audited) the same way.
        """
        self.ensure_one()
        return self.od19_action_open_pull_wizard()
