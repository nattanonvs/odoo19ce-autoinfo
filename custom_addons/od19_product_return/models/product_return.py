from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductReturn(models.Model):
    _name = "od19.product.return"
    _description = "Product Return / RMA"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Return Number",
        default="/",
        readonly=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        required=True,
        tracking=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        required=True,
        tracking=True,
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Serial/Lot",
        domain="[('product_id', '=', product_id)]",
    )
    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit of Measure",
        related="product_id.uom_id",
        readonly=True,
    )
    reason = fields.Selection(
        selection=[
            ("defective", "Defective / สินค้าชำรุด"),
            ("wrong_product", "Wrong Product / สินค้าผิด"),
            ("damaged", "Damaged in Transit / สินค้าชำรุดระหว่างขนส่ง"),
            ("not_as_described", "Not as Described / ไม่ตรงตามรายละเอียด"),
            ("warranty", "Warranty Claim / เคลมประกัน"),
            ("other", "Other / อื่นๆ"),
        ],
        string="Reason",
        required=True,
        tracking=True,
    )
    description = fields.Text(string="Description")
    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        domain="[('partner_id', '=', partner_id)]",
    )
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        domain="[('partner_id', '=', partner_id), ('move_type', '=', 'out_invoice')]",
    )
    warranty_claim_id = fields.Many2one(
        comodel_name="od19.warranty.claim",
        string="Warranty Claim",
    )
    return_date = fields.Date(
        string="Return Date",
        default=fields.Date.context_today,
        required=True,
    )
    refund_amount = fields.Monetary(
        string="Refund Amount",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("approved", "Approved"),
            ("returned", "Returned"),
            ("refunded", "Refunded"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        copy=False,
    )
    rejection_reason = fields.Text(string="Rejection Reason")
    return_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Return Picking",
        readonly=True,
    )
    refund_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Refund Invoice",
        readonly=True,
    )
    responsible_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.user,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "od19.product.return"
                ) or "/"
        return super().create(vals_list)

    @api.constrains("quantity")
    def _check_quantity(self):
        for rec in self:
            if rec.quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")

    def action_confirm(self):
        self.write({"state": "confirmed"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Reject Return",
            "res_model": "od19.product.return.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_return_id": self.id},
        }

    def action_return(self):
        """Create a stock picking to receive returned goods."""
        self.ensure_one()
        if self.state != "approved":
            return
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming")], limit=1
        )
        picking_vals = {
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "origin": self.name,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
            "move_ids": [
                (
                    0,
                    0,
                    {
                        "description_picking": self.product_id.display_name,
                        "product_id": self.product_id.id,
                        "product_uom_qty": self.quantity,
                        "product_uom": self.uom_id.id,
                        "location_id": picking_type.default_location_src_id.id,
                        "location_dest_id": picking_type.default_location_dest_id.id,
                    },
                )
            ],
        }
        picking = self.env["stock.picking"].create(picking_vals)
        self.return_picking_id = picking.id
        self.write({"state": "returned"})
        return {
            "type": "ir.actions.act_window",
            "name": "Return Picking",
            "res_model": "stock.picking",
            "res_id": picking.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_refund(self):
        """Create a customer refund (credit note)."""
        self.ensure_one()
        if self.state not in ("returned", "approved"):
            return
        refund_vals = {
            "move_type": "out_refund",
            "partner_id": self.partner_id.id,
            "invoice_origin": self.name,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": f"Return: {self.product_id.display_name}",
                        "product_id": self.product_id.id,
                        "quantity": self.quantity,
                        "price_unit": self.refund_amount or 0.0,
                    },
                )
            ],
        }
        refund = self.env["account.move"].create(refund_vals)
        self.refund_move_id = refund.id
        self.write({"state": "refunded"})
        return {
            "type": "ir.actions.act_window",
            "name": "Customer Refund",
            "res_model": "account.move",
            "res_id": refund.id,
            "view_mode": "form",
            "target": "current",
        }
