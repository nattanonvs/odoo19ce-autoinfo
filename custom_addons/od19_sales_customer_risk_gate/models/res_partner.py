from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ResPartner(models.Model):
    _inherit = "res.partner"

    od19_blacklist_status = fields.Selection(
        selection=[("normal", "Normal"), ("blacklisted", "Blacklisted")],
        string="Blacklist Status",
        default="normal",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
    )
    od19_blacklist_reason = fields.Text(
        string="Blacklist Reason",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_request_state = fields.Selection(
        selection=[
            ("not_requested", "Not Requested"),
            ("pending", "Pending Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Credit Request State",
        default="not_requested",
        tracking=True,
        copy=False,
        groups="base.group_user",
    )
    od19_credit_limit_amount = fields.Monetary(
        string="Credit Limit Amount",
        currency_field="od19_credit_currency_id",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
        help="Maximum credit amount allowed for this customer.",
    )
    od19_credit_currency_id = fields.Many2one(
        "res.currency",
        string="Credit Currency",
        default=lambda self: self.env.company.currency_id,
        copy=False,
    )
    od19_credit_used_amount = fields.Monetary(
        string="Credit Used Amount",
        currency_field="od19_credit_currency_id",
        compute="_compute_od19_credit_used_amount",
        store=False,
        copy=False,
        help="Sum of unpaid invoices and confirmed sale order amounts.",
    )
    od19_credit_available = fields.Monetary(
        string="Credit Available",
        currency_field="od19_credit_currency_id",
        compute="_compute_od19_credit_available",
        store=False,
        copy=False,
        help="Credit limit minus credit used.",
    )
    od19_credit_expiry_date = fields.Date(
        string="Credit Expiry Date",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer,base.group_partner_manager",
        help="Date when the credit approval expires.",
    )
    od19_credit_sale_allowed = fields.Boolean(
        string="Credit Sale Allowed",
        compute="_compute_od19_credit_sale_allowed",
        store=True,
        copy=False,
        help="Customer is allowed to buy on credit terms.",
    )
    od19_credit_requested_by = fields.Many2one(
        "res.users",
        string="Requested By",
        tracking=True,
        copy=False,
        readonly=True,
    )
    od19_credit_request_date = fields.Datetime(
        string="Requested On",
        tracking=True,
        copy=False,
        readonly=True,
    )
    od19_credit_review_owner_id = fields.Many2one(
        "res.users",
        string="Review Owner",
        tracking=True,
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_review_date = fields.Datetime(
        string="Reviewed On",
        tracking=True,
        copy=False,
        readonly=True,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )
    od19_credit_review_note = fields.Text(
        string="Review Note",
        copy=False,
        groups="od19_sales_customer_risk_gate.group_od19_credit_reviewer",
    )

    _OD19_PROTECTED_FIELDS = {
        "od19_blacklist_status",
        "od19_blacklist_reason",
        "od19_credit_request_state",
        "od19_credit_review_date",
        "od19_credit_limit_amount",
        "od19_credit_expiry_date",
    }

    @api.depends(
        "od19_credit_request_state",
        "od19_credit_expiry_date",
        "od19_credit_limit_amount",
    )
    def _compute_od19_credit_sale_allowed(self):
        today = fields.Date.context_today(self)
        for partner in self:
            is_approved = partner.od19_credit_request_state == "approved"
            not_expired = (
                not partner.od19_credit_expiry_date
                or partner.od19_credit_expiry_date >= today
            )
            # Compute available credit on the fly to avoid stale stored data
            commercial = partner.commercial_partner_id
            used = commercial.od19_credit_used_amount
            available = commercial.od19_credit_limit_amount - used
            has_available_credit = (
                not commercial.od19_credit_limit_amount or available > 0
            )
            partner.od19_credit_sale_allowed = (
                is_approved and not_expired and has_available_credit
            )

    def _compute_od19_credit_used_amount(self):
        for partner in self:
            commercial = partner.commercial_partner_id
            # Unpaid customer invoices (posted, not fully reconciled)
            invoice_domain = [
                ("partner_id.commercial_partner_id", "=", commercial.id),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
            ]
            invoices = self.env["account.move"].sudo().search(invoice_domain)
            unpaid = sum(invoices.mapped("amount_residual_signed"))
            # Confirmed sale orders (not yet invoiced fully)
            so_domain = [
                ("partner_id.commercial_partner_id", "=", commercial.id),
                ("state", "=", "sale"),
            ]
            orders = self.env["sale.order"].sudo().search(so_domain)
            order_amount = sum(orders.mapped("amount_total"))
            partner.od19_credit_used_amount = max(unpaid + order_amount, 0.0)

    @api.depends("od19_credit_limit_amount", "od19_credit_used_amount")
    def _compute_od19_credit_available(self):
        for partner in self:
            partner.od19_credit_available = (
                partner.od19_credit_limit_amount - partner.od19_credit_used_amount
            )

    def _od19_is_credit_reviewer(self):
        self.ensure_one()
        return self.env.user.has_group(
            "od19_sales_customer_risk_gate.group_od19_credit_reviewer"
        )

    def write(self, vals):
        if not self.env.su and not self._od19_is_credit_reviewer():
            if self._OD19_PROTECTED_FIELDS.intersection(vals):
                raise AccessError(
                    _("Only credit reviewers can modify customer risk fields.")
                )
        reval_fields = {"od19_blacklist_status", "od19_credit_request_state",
                        "od19_credit_expiry_date", "od19_credit_limit_amount"}
        needs_reval = bool(reval_fields.intersection(vals))
        res = super().write(vals)
        if needs_reval:
            self._od19_revalidate_confirmed_orders()
        return res

    def _od19_revalidate_confirmed_orders(self):
        """Revalidate all confirmed sale orders when risk fields change.

        When blacklist status, credit state, expiry date or credit limit
        changes, check every confirmed sale order of the commercial partner.
        Orders that no longer pass the customer gate are flagged with a
        warning activity so the sales team can review them.
        """
        for partner in self:
            commercial = partner.commercial_partner_id
            confirmed_orders = self.env["sale.order"].sudo().search(
                [
                    ("partner_id.commercial_partner_id", "=", commercial.id),
                    ("state", "=", "sale"),
                ]
            )
            for order in confirmed_orders:
                reason_code, message = order._od19_check_customer_gate(
                    "credit_revalidation"
                )
                if reason_code:
                    order._od19_log_gate_event(
                        commercial, reason_code, "credit_revalidation"
                    )
                    owner = (
                        commercial.od19_credit_review_owner_id
                        or order.user_id
                        or self.env.user
                    )
                    order.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=owner.id,
                        summary=_("Credit revalidation: review required"),
                        note=message,
                    )

    def action_od19_request_credit(self):
        for partner in self:
            commercial = partner.commercial_partner_id
            if commercial.od19_credit_request_state in ("pending", "approved"):
                continue
            commercial.sudo().write(
                {
                    "od19_credit_request_state": "pending",
                    "od19_credit_requested_by": self.env.user.id,
                    "od19_credit_request_date": fields.Datetime.now(),
                }
            )
            owner = commercial.sudo().od19_credit_review_owner_id
            if owner:
                commercial.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=owner.id,
                    summary=_("Review credit request"),
                    note=_("Customer %s requested credit approval.")
                    % commercial.display_name,
                )
        return True

    def action_od19_approve_credit(self):
        self._od19_review_credit("approved")

    def action_od19_reject_credit(self):
        self._od19_review_credit("rejected")

    def _od19_review_credit(self, new_state):
        if not self._od19_is_credit_reviewer():
            raise AccessError(
                _("Only credit reviewers can approve or reject credit requests.")
            )
        for partner in self:
            commercial = partner.commercial_partner_id
            if commercial.od19_credit_request_state != "pending":
                raise UserError(
                    _("Credit request must be in 'Pending Review' state.")
                )
            if not commercial.od19_credit_review_note:
                raise UserError(
                    _("Please fill in the review note before deciding.")
                )
            commercial.sudo().write(
                {
                    "od19_credit_request_state": new_state,
                    "od19_credit_review_owner_id": self.env.user.id,
                    "od19_credit_review_date": fields.Datetime.now(),
                }
            )
            commercial.activity_feedback(
                ["mail.mail_activity_data_todo"],
                feedback=_("Credit request %s.") % new_state,
            )
        return True

    def action_od19_set_blacklist(self):
        if not self._od19_is_credit_reviewer():
            raise AccessError(
                _("Only credit reviewers can manage the blacklist.")
            )
        for partner in self:
            commercial = partner.commercial_partner_id
            if not commercial.od19_blacklist_reason:
                raise UserError(
                    _("A blacklist reason is required before blacklisting.")
                )
            commercial.sudo().write({"od19_blacklist_status": "blacklisted"})
        return True

    def action_od19_clear_blacklist(self):
        if not self._od19_is_credit_reviewer():
            raise AccessError(
                _("Only credit reviewers can manage the blacklist.")
            )
        for partner in self:
            commercial = partner.commercial_partner_id
            commercial.sudo().write({"od19_blacklist_status": "normal"})
        return True

    @api.model
    def od19_credit_gate_kpis(self):
        partners = self.env["res.partner"].search([])
        pending = partners.filtered(lambda p: p.od19_credit_request_state == "pending")
        rejected = partners.filtered(
            lambda p: p.od19_credit_request_state == "rejected"
        )
        events = self.env["od19.credit.gate.event"].search([])
        now = fields.Datetime.now()
        avg_age = 0.0
        if pending and any(p.od19_credit_request_date for p in pending):
            ages = [
                (now - p.od19_credit_request_date).total_seconds() / 86400.0
                for p in pending
                if p.od19_credit_request_date
            ]
            avg_age = sum(ages) / len(ages) if ages else 0.0
        return {
            "pending_count": len(pending),
            "pending_avg_age_days": avg_age,
            "rejected_count": len(rejected),
            "blocked_blacklist_count": len(
                events.filtered(lambda e: e.reason_code == "blacklist")
            ),
            "blocked_credit_count": len(
                events.filtered(lambda e: e.reason_code == "credit")
            ),
        }
