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

    @api.depends("invoice_ids", "invoice_ids.move_type", "invoice_ids.state")
    def _compute_od19_customer_invoice_count(self):
        for order in self:
            order.od19_customer_invoice_count = len(
                order.invoice_ids.filtered(
                    lambda move: move.move_type in ("out_invoice", "out_refund")
                    and move.state != "cancel"
                )
            )

    @api.depends(
        "od19_billing_readiness_state",
        "invoice_ids",
        "invoice_ids.move_type",
        "invoice_ids.state",
        "invoice_ids.payment_state",
    )
    def _compute_od19_invoice_closure_state(self):
        for order in self:
            invoices = order.invoice_ids.filtered(
                lambda move: move.move_type in ("out_invoice", "out_refund")
                and move.state != "cancel"
            )
            if order.od19_billing_readiness_state != "ready":
                order.od19_invoice_closure_state = "waiting_readiness"
            elif not invoices:
                order.od19_invoice_closure_state = "ready_to_invoice"
            elif all(move.payment_state == "paid" for move in invoices):
                order.od19_invoice_closure_state = "paid"
            elif any(
                move.payment_state in ("partial", "in_payment", "paid")
                for move in invoices
            ):
                order.od19_invoice_closure_state = "partially_paid"
            else:
                order.od19_invoice_closure_state = "invoiced"
