# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Get Sale Order Lines wizard on customer invoices.

Allows the user to pick un-invoiced lines from a confirmed Sale Order (same
partner as the invoice) and create invoice lines from them, preserving the
``sale_line_ids`` link so delivered quantities and invoice reporting stay
consistent.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Od19AccountInvoiceGetSaleLines(models.TransientModel):
    _name = "od19.account.invoice.get.sale.lines"
    _description = "Get Sale Order Lines / ดึงรายการจากใบสั่งขาย"

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice / ใบแจ้งหนี้",
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Partner / คู่ค้า",
        related="invoice_id.partner_id",
        readonly=True,
    )
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sale Order / ใบสั่งขาย",
        domain=(
            "[('partner_id', '=', partner_id), "
            "('state', 'in', ['sale', 'done'])]"
        ),
        help="Confirmed sale orders for the same partner as this invoice.",
    )
    sale_line_ids = fields.Many2many(
        comodel_name="sale.order.line",
        string="Available Lines / รายการที่สามารถเลือกได้",
        domain=(
            "[('order_id', '=', sale_order_id), "
            "('qty_to_invoice', '>', 0), "
            "('display_type', '=', False)]"
        ),
        help="Sale order lines that have not been fully invoiced yet.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_model == "account.move" and active_id:
            res["invoice_id"] = active_id
        return res

    @api.onchange("sale_order_id")
    def _onchange_sale_order_id(self):
        """Reset the selected lines whenever the SO changes."""
        self.sale_line_ids = False

    def action_get_lines(self):
        """Create invoice lines from the selected sale order lines."""
        self.ensure_one()
        invoice = self.invoice_id
        if not invoice:
            raise UserError(_("No invoice selected."))
        if invoice.state != "draft":
            raise UserError(_(
                "You can only add sale order lines to a draft invoice."
            ))
        if invoice.move_type != "out_invoice":
            raise UserError(_(
                "This action is only available on customer invoices."
            ))
        if not self.sale_order_id:
            raise UserError(_("Please select a sale order."))
        if not self.sale_line_ids:
            raise UserError(_("Please select at least one sale order line."))

        # Only keep lines that still belong to the chosen SO and are not
        # already fully invoiced (safety net against stale selections).
        so_lines = self.sale_line_ids.filtered(
            lambda l: l.order_id == self.sale_order_id
            and l.qty_to_invoice > 0
            and not l.display_type
        )
        if not so_lines:
            raise UserError(_(
                "The selected lines are no longer available for invoicing."
            ))

        line_commands = []
        for so_line in so_lines:
            # _prepare_invoice_line already includes sale_line_ids so the
            # link back to the originating SO line is preserved.
            vals = so_line._prepare_invoice_line()
            vals["move_id"] = invoice.id
            line_commands.append((0, 0, vals))

        invoice.write({"invoice_line_ids": line_commands})

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }
