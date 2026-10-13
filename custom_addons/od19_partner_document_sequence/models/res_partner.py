from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer = fields.Boolean(
        string="Is a Customer",
        default=False,
        help="Check this box if this contact is a customer.",
    )
    supplier = fields.Boolean(
        string="Is a Vendor",
        default=False,
        help="Check this box if this contact is a vendor.",
    )
    is_customer_and_supplier = fields.Boolean(
        string="Is a Customer and Vendor",
        compute="_compute_is_customer_and_supplier",
        store=True,
    )
    is_auto_running = fields.Boolean(
        string="Auto Running",
        index=True,
        default=True,
        help="Auto-generate the partner reference code.",
    )

    @api.depends("customer", "supplier")
    def _compute_is_customer_and_supplier(self):
        for rec in self:
            rec.is_customer_and_supplier = rec.customer and rec.supplier

    @api.onchange("supplier", "customer")
    def _onchange_partner_type(self):
        if self.customer and self.supplier:
            self.is_auto_running = False
        else:
            self.is_auto_running = True

    def _generate_partner_ref(self):
        """Generate the partner reference code based on customer/vendor type."""
        self.ensure_one()
        if not self.is_auto_running:
            return
        if self.ref and self.ref not in ("New", "", "/"):
            return
        if self.customer:
            self.ref = self.env["ir.sequence"].next_by_code("res.partner") or "/"
        elif self.supplier:
            self.ref = self.env["ir.sequence"].next_by_code("res.partner.vendor") or "/"

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for rec in res:
            # Sync customer_rank / supplier_rank
            if rec.customer and rec.customer_rank == 0:
                rec.customer_rank = 1
            if rec.supplier and rec.supplier_rank == 0:
                rec.supplier_rank = 1
            rec._generate_partner_ref()
        return res

    def write(self, vals):
        # Sync customer/supplier with rank fields
        if "customer" in vals and vals.get("customer"):
            vals.setdefault("customer_rank", 1)
        if "supplier" in vals and vals.get("supplier"):
            vals.setdefault("supplier_rank", 1)
        res = super().write(vals)
        for rec in self:
            rec._generate_partner_ref()
        return res
