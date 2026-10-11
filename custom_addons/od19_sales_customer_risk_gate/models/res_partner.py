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
    }

    @api.depends("od19_credit_request_state")
    def _compute_od19_credit_sale_allowed(self):
        for partner in self:
            partner.od19_credit_sale_allowed = (
                partner.od19_credit_request_state == "approved"
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
        return super().write(vals)

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
