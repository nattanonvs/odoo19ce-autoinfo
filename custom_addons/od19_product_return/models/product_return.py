from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Only draft returns can be confirmed.")
                )
            rec.write({"state": "confirmed"})

    def action_approve(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(
                    _("Only confirmed returns can be approved.")
                )
            rec.write({"state": "approved"})

    def action_reject(self):
        self.ensure_one()
        if self.state in ("returned", "refunded", "rejected"):
            raise UserError(
                _("A %s return cannot be rejected.") % self.state
            )
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
            raise UserError(
                _("Only approved returns can be received.")
            )
        picking_type = self.env["stock.picking.type"].search(
            [("code", "=", "incoming"), ("company_id", "=", self.company_id.id)],
            limit=1,
        )
        if not picking_type:
            raise UserError(
                _(
                    "No incoming operation type is configured for company %s, "
                    "so the returned goods cannot be received."
                )
                % self.company_id.display_name
            )
        source_location = picking_type.default_location_src_id
        dest_location = picking_type.default_location_dest_id
        if not source_location or not dest_location:
            raise UserError(
                _(
                    "The incoming operation type %s is missing its default "
                    "source or destination location."
                )
                % picking_type.display_name
            )
        picking_vals = {
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "origin": self.name,
            "location_id": source_location.id,
            "location_dest_id": dest_location.id,
            "move_ids": [
                (
                    0,
                    0,
                    {
                        "description_picking": self.product_id.display_name,
                        "product_id": self.product_id.id,
                        "product_uom_qty": self.quantity,
                        "product_uom": self.uom_id.id,
                        "location_id": source_location.id,
                        "location_dest_id": dest_location.id,
                    },
                )
            ],
        }
        picking = self.env["stock.picking"].create(picking_vals)
        picking.action_confirm()
        picking.action_assign()
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

    def _get_refund_unit_price(self):
        """Resolve the unit price to refund for this product.

        Priority: the explicit refund amount (a total, converted to a unit
        price), then the price on the linked invoice line for the same
        product, and finally zero.
        """
        self.ensure_one()
        if self.refund_amount and self.quantity:
            return self.refund_amount / self.quantity
        if self.invoice_id:
            line = self.invoice_id.invoice_line_ids.filtered(
                lambda inv_line: inv_line.product_id == self.product_id
            )[:1]
            if line:
                return line.price_unit
        return 0.0

    def action_refund(self):
        """Create a customer refund (credit note)."""
        self.ensure_one()
        # An already created refund is re-opened on every call: the action stays
        # idempotent, even once the record reached the ``refunded`` state.
        if self.refund_move_id:
            return self._open_refund_action(self.refund_move_id)
        if self.state not in ("returned", "approved"):
            raise UserError(
                _("Only returned or approved returns can be refunded.")
            )
        refund_vals = {
            "move_type": "out_refund",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "invoice_origin": self.name,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": f"Return: {self.product_id.display_name}",
                        "product_id": self.product_id.id,
                        "quantity": self.quantity,
                        "price_unit": self._get_refund_unit_price(),
                    },
                )
            ],
        }
        refund = self.env["account.move"].create(refund_vals)
        self.refund_move_id = refund.id
        self.write({"state": "refunded"})
        return self._open_refund_action(refund)

    def _open_refund_action(self, refund):
        return {
            "type": "ir.actions.act_window",
            "name": "Customer Refund",
            "res_model": "account.move",
            "res_id": refund.id,
            "view_mode": "form",
            "target": "current",
        }
