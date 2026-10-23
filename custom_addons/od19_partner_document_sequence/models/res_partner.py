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

    def _sync_partner_ranks(self):
        """Flag the partner as customer/vendor for the standard filters.

        ``customer_rank`` / ``supplier_rank`` are provided by the ``account``
        module, which is not a dependency here: sync them only when present.
        """
        has_ranks = "customer_rank" in self._fields
        for rec in self:
            if has_ranks:
                if rec.customer and not rec.customer_rank:
                    rec.customer_rank = 1
                if rec.supplier and not rec.supplier_rank:
                    rec.supplier_rank = 1
            rec._generate_partner_ref()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Mirror ``_onchange_partner_type``: auto-numbering is turned off
            # when the partner is both a customer and a vendor.
            if "is_auto_running" not in vals:
                vals["is_auto_running"] = not (
                    vals.get("customer") and vals.get("supplier")
                )
        res = super().create(vals_list)
        res._sync_partner_ranks()
        return res

    def write(self, vals):
        # Sync customer/supplier with rank fields
        if "customer_rank" in self._fields:
            if vals.get("customer"):
                vals.setdefault("customer_rank", 1)
            if vals.get("supplier"):
                vals.setdefault("supplier_rank", 1)
        res = super().write(vals)
        if "is_auto_running" not in vals and (
            "customer" in vals or "supplier" in vals
        ):
            # Keep the ORM consistent with ``_onchange_partner_type``.
            both = self.filtered(lambda r: r.customer and r.supplier)
            others = self - both
            if both:
                super(ResPartner, both).write({"is_auto_running": False})
            if others:
                super(ResPartner, others).write({"is_auto_running": True})
        self._sync_partner_ranks()
        return res
