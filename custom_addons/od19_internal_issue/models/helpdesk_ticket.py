from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    visibility = fields.Selection(
        selection=[
            ("public", "Public"),
            ("department", "Department"),
            ("private", "Private"),
        ],
        string="Visibility",
        default="public",
        required=True,
        tracking=True,
        index=True,
        help="Who can see this issue: everyone, same department, or only reporter/assignee.",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        string="Department",
        tracking=True,
        index=True,
    )
    reported_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Reported By",
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    is_emergency = fields.Boolean(
        string="Emergency",
        default=False,
        tracking=True,
        index=True,
    )
    resolution = fields.Html(
        string="Resolution",
        sanitize_style=True,
        help="Root cause and solution — can be converted to a knowledge article.",
    )
    has_tier_validation = fields.Boolean(
        string="Requires Validation",
        default=False,
        tracking=True,
    )

    @api.onchange("category_id")
    def _onchange_category_id(self):
        if self.category_id and self.category_id.default_user_id:
            self.user_id = self.category_id.default_user_id
        if self.category_id and self.category_id.default_team_id:
            self.team_id = self.category_id.default_team_id

    def write(self, vals):
        res = super().write(vals)
        if "user_id" in vals and vals["user_id"]:
            for record in self:
                record._notify_assigned()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.user_id:
                record._notify_assigned()
        return records

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def _notify_assigned(self):
        self.ensure_one()
        assignee = self.user_id
        if not assignee:
            return
        partners = assignee.partner_id
        message = _(
            "You have been assigned to issue %(number)s: %(title)s.",
            number=self.number,
            title=self.name,
        )
        self.env["notification.service"].notify(
            partners,
            message,
            event="issue_assigned",
            subject=_("New Issue Assigned"),
        )

    def _notify_updated(self, message_text):
        self.ensure_one()
        partners = self._get_notification_partners()
        if not partners:
            return
        self.env["notification.service"].notify(
            partners,
            message_text,
            event="issue_updated",
            subject=_("Issue Updated: %s") % self.name,
        )

    def _get_notification_partners(self):
        self.ensure_one()
        partners = self.env["res.partner"]
        if self.user_id:
            partners |= self.user_id.partner_id
        if self.reported_by_id:
            partners |= self.reported_by_id.partner_id
        if self.partner_id:
            partners |= self.partner_id
        return partners
