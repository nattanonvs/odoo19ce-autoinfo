from odoo import api, fields, models


class NotificationPreference(models.Model):
    _name = "notification.preference"
    _description = "Notification Preference"
    _order = "user_id, event"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
    )
    event = fields.Selection(
        selection=[
            ("default", "Default"),
            ("asset_loan_due", "Asset Loan Due Reminder"),
            ("asset_loan_overdue", "Asset Loan Overdue"),
            ("asset_calibration_due", "Asset Calibration Due"),
            ("issue_assigned", "Issue Assigned"),
            ("issue_updated", "Issue Updated"),
            ("announcement", "Announcement"),
            ("custom", "Custom"),
        ],
        string="Event",
        required=True,
        default="default",
    )
    channel_ids = fields.Many2many(
        comodel_name="notification.channel",
        relation="notification_preference_channel_rel",
        column1="preference_id",
        column2="channel_id",
        string="Channels",
        required=True,
    )

    _sql_constraints = [
        (
            "user_event_uniq",
            "unique(user_id, event)",
            "Only one preference per event per user.",
        ),
    ]

    @api.model
    def get_channels(self, user_id, event="default"):
        """Return channel types for a user on a given event, falling back to default."""
        pref = self.search(
            [("user_id", "=", user_id), ("event", "=", event)],
            limit=1,
        )
        if not pref:
            pref = self.search(
                [("user_id", "=", user_id), ("event", "=", "default")],
                limit=1,
            )
        if not pref:
            default_odoo = self.env["notification.channel"].search(
                [("channel_type", "=", "odoo")],
                limit=1,
            )
            return [default_odoo.channel_type] if default_odoo else ["odoo"]
        return pref.channel_ids.mapped("channel_type")
