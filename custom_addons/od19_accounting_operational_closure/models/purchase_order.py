from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    od19_vendor_bill_closure_state = fields.Selection(
        [
            ("waiting_commitment", "Waiting Commitment"),
            ("waiting_service_acceptance", "Waiting Service Acceptance"),
            ("ready_to_bill", "Ready to Bill"),
            ("billed", "Billed"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Vendor Bill Closure State",
        compute="_compute_od19_vendor_bill_closure_state",
        store=True,
        readonly=True,
    )

    @api.depends(
        "state",
        "invoice_status",
        "invoice_ids.move_type",
        "invoice_ids.state",
        "invoice_ids.od19_operational_closure_state",
        "order_line.od19_service_acceptance_required",
        "order_line.od19_service_accepted",
    )
    def _compute_od19_vendor_bill_closure_state(self):
        for order in self:
            bills = order.invoice_ids.filtered(
                lambda move: move.move_type in ("in_invoice", "in_refund")
                and move.state != "cancel"
            )
            waiting_service = order.order_line.filtered(
                lambda line: line.od19_service_acceptance_required
                and not line.od19_service_accepted
            )
            if not order._od19_is_committed_for_service_acceptance():
                order.od19_vendor_bill_closure_state = "waiting_commitment"
            elif waiting_service:
                order.od19_vendor_bill_closure_state = "waiting_service_acceptance"
            elif not bills:
                order.od19_vendor_bill_closure_state = "ready_to_bill"
            elif all(
                move.od19_operational_closure_state == "paid"
                for move in bills
            ) and order.invoice_status == "invoiced":
                order.od19_vendor_bill_closure_state = "paid"
            elif any(
                move.od19_operational_closure_state in ("partially_paid", "paid")
                for move in bills
            ):
                order.od19_vendor_bill_closure_state = "partially_paid"
            else:
                order.od19_vendor_bill_closure_state = "billed"

    def _od19_is_committed_for_service_acceptance(self):
        self.ensure_one()
        return self.state in ("purchase", "done")
