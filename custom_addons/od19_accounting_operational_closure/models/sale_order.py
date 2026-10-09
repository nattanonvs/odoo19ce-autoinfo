from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    od19_invoice_closure_state = fields.Selection(
        [
            ("waiting_readiness", "Waiting Readiness"),
            ("ready_to_invoice", "Ready to Invoice"),
            ("invoiced", "Invoiced"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Invoice Closure State",
        compute="_compute_od19_invoice_closure_state",
        store=True,
        readonly=True,
    )
    od19_customer_invoice_count = fields.Integer(
        string="Customer Invoice Count",
        compute="_compute_od19_customer_invoice_count",
    )

    @api.depends(
        "order_line.invoice_lines.move_id.move_type",
        "order_line.invoice_lines.move_id.state",
    )
    def _compute_od19_customer_invoice_count(self):
        for order in self:
            order.od19_customer_invoice_count = len(order._od19_customer_invoice_moves())

    @api.depends(
        "od19_billing_readiness_state",
        "invoice_status",
        "order_line.invoice_lines.move_id.move_type",
        "order_line.invoice_lines.move_id.state",
        "order_line.invoice_lines.move_id.od19_operational_closure_state",
    )
    def _compute_od19_invoice_closure_state(self):
        for order in self:
            invoices = order._od19_customer_invoice_moves()
            posted_invoices = invoices.filtered(lambda move: move.state == "posted")
            if order.od19_billing_readiness_state != "ready":
                order.od19_invoice_closure_state = "waiting_readiness"
            elif not posted_invoices:
                order.od19_invoice_closure_state = "ready_to_invoice"
            elif all(
                move.od19_operational_closure_state == "paid"
                for move in posted_invoices
            ) and order.invoice_status == "invoiced":
                order.od19_invoice_closure_state = "paid"
            elif any(
                move.od19_operational_closure_state in ("partially_paid", "paid")
                for move in posted_invoices
            ):
                order.od19_invoice_closure_state = "partially_paid"
            else:
                order.od19_invoice_closure_state = "invoiced"

    def _od19_customer_invoice_moves(self):
        self.ensure_one()
        return self.order_line.invoice_lines.move_id.filtered(
            lambda move: move.move_type in ("out_invoice", "out_refund")
            and move.state != "cancel"
        )
