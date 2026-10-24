# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class Od19PurchaseCreateVendorBill(models.TransientModel):
    _name = "od19.purchase.create.vendor.bill"
    _description = "OD19 Purchase Create Vendor Bill Wizard"

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Purchase Order / ใบสั่งซื้อ",
        required=True,
        readonly=True,
    )
    bill_date = fields.Date(
        string="Bill Date / วันที่ใบแจ้งหนี้",
        required=True,
        default=fields.Date.context_today,
    )
    bill_reference = fields.Char(
        string="Bill Reference / เลขที่ใบแจ้งหนี้",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        if active_model == "purchase.order" and active_id:
            res["purchase_order_id"] = active_id
        return res

    def action_create_bill(self):
        """Create a vendor bill (account.move) from the purchase order."""
        self.ensure_one()
        po = self.purchase_order_id
        if not po:
            raise UserError(_("No purchase order selected."))
        if po.state not in ("purchase", "done"):
            raise UserError(
                _(
                    "Vendor bill can only be created from confirmed "
                    "purchase orders."
                )
            )

        invoice_vals = po._prepare_invoice()
        invoice_vals.update(
            {
                "invoice_date": self.bill_date,
                "date": self.bill_date,
                "ref": self.bill_reference,
            }
        )

        invoice_lines = []
        sequence = 10
        pending_section = None
        for line in po.order_line:
            if line.display_type in ("line_section", "line_subsection"):
                pending_section = line
                continue
            if line.qty_to_invoice <= 0:
                # Skip lines with nothing left to bill, so a partially billed
                # order is not billed twice.
                continue
            if pending_section:
                section_vals = pending_section._prepare_account_move_line()
                section_vals.update({"sequence": sequence})
                invoice_lines.append((0, 0, section_vals))
                sequence += 10
                pending_section = None

            line_vals = line._prepare_account_move_line()
            line_vals.update({"sequence": sequence})
            invoice_lines.append((0, 0, line_vals))
            sequence += 10

        invoice_vals["invoice_line_ids"] = invoice_lines

        move = (
            self.env["account.move"]
            .with_context(default_move_type="in_invoice")
            .create(invoice_vals)
        )

        return {
            "name": _("Vendor Bill / ใบแจ้งหนี้ผู้ขาย"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": move.id,
            "target": "current",
            "context": {"default_move_type": "in_invoice"},
        }
