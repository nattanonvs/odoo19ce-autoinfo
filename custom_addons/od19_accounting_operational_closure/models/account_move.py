from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    od19_operational_flow = fields.Selection(
        [
            ("customer", "Customer"),
            ("vendor", "Vendor"),
            ("other", "Other"),
        ],
        string="Operational Flow",
        compute="_compute_od19_operational_flow",
        store=True,
        readonly=True,
    )
    od19_operational_closure_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("partially_paid", "Partially Paid"),
            ("paid", "Paid"),
        ],
        string="Operational Closure State",
        compute="_compute_od19_operational_closure_state",
        store=True,
        readonly=True,
    )
    od19_source_document = fields.Char(
        string="Source Document",
        compute="_compute_od19_source_document",
        store=True,
        readonly=True,
    )

    @api.depends("move_type")
    def _compute_od19_operational_flow(self):
        customer_types = {"out_invoice", "out_refund", "out_receipt"}
        vendor_types = {"in_invoice", "in_refund", "in_receipt"}
        for move in self:
            if move.move_type in customer_types:
                move.od19_operational_flow = "customer"
            elif move.move_type in vendor_types:
                move.od19_operational_flow = "vendor"
            else:
                move.od19_operational_flow = "other"

    @api.depends("invoice_origin", "ref", "name")
    def _compute_od19_source_document(self):
        for move in self:
            move.od19_source_document = move._od19_get_source_document()

    @api.depends("state", "payment_state", "amount_total", "amount_residual", "currency_id")
    def _compute_od19_operational_closure_state(self):
        for move in self:
            currency = move.currency_id or move.company_id.currency_id
            residual_is_zero = currency.is_zero(move.amount_residual)
            total_is_zero = currency.is_zero(move.amount_total)
            has_partial_residual = (
                not residual_is_zero
                and not total_is_zero
                and abs(move.amount_residual) < abs(move.amount_total)
            )
            if move.state != "posted":
                move.od19_operational_closure_state = "draft"
            elif move.payment_state == "paid":
                # "reversed" is intentionally excluded: a reversed payment
                # means the invoice is no longer settled.
                move.od19_operational_closure_state = "paid"
            elif move.payment_state in ("partial", "in_payment") or (
                move.payment_state == "blocked" and has_partial_residual
            ):
                move.od19_operational_closure_state = "partially_paid"
            else:
                move.od19_operational_closure_state = "posted"

    def _od19_get_source_document(self):
        self.ensure_one()
        return self.invoice_origin or self.ref or self.name
