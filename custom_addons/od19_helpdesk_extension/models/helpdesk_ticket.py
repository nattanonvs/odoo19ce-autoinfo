from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _name = "helpdesk.ticket"
    _inherit = "helpdesk.ticket"

    team_type = fields.Selection(
        related="team_id.team_type",
        string="Team Type",
        store=True,
        readonly=True,
    )
    is_customer_service = fields.Boolean(
        compute="_compute_is_customer_service",
        store=True,
    )

    # --- Sales Services fields (shown only for customer_service teams) ---
    service_type = fields.Selection(
        selection=[
            ("repair", "Repair / ซ่อมแซม"),
            ("installation", "Installation / ติดตั้ง"),
            ("maintenance", "Maintenance / บำรุงรักษา"),
            ("warranty", "Warranty / การรับประกัน"),
            ("inspection", "Inspection / ตรวจสอบ"),
            ("other", "Other / อื่นๆ"),
        ],
        string="Service Type",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        domain="[('sale_ok', '=', True)]",
    )
    lot_id = fields.Many2one(
        comodel_name="stock.lot",
        string="Serial/Lot",
        domain="[('product_id', '=', product_id)]",
    )
    technician_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Technician",
        domain="[('department_id.name', 'ilike', 'service')]",
    )
    planned_date = fields.Date(string="Planned Date")
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
    total_cost = fields.Monetary(
        string="Service Cost",
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    resolution = fields.Html(string="Resolution")

    @api.depends("team_type")
    def _compute_is_customer_service(self):
        for rec in self:
            rec.is_customer_service = rec.team_type == "customer_service"

    def action_create_invoice(self):
        """Create a customer invoice from a sales service ticket."""
        self.ensure_one()
        if not self.partner_id:
            return
        if self.invoice_id:
            return self._open_invoice_action(self.invoice_id)
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "company_id": self.company_id.id,
            "invoice_origin": self.number,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": f"Service: {self.name}",
                        "quantity": 1,
                        "price_unit": self.total_cost or 0.0,
                        "product_id": self.product_id.id if self.product_id else False,
                    },
                )
            ],
        }
        invoice = self.env["account.move"].create(invoice_vals)
        self.invoice_id = invoice.id
        return self._open_invoice_action(invoice)

    def _open_invoice_action(self, invoice):
        return {
            "type": "ir.actions.act_window",
            "name": "Invoice",
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }
