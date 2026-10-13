from odoo import api, fields, models


class NotificationChannel(models.Model):
    _name = "notification.channel"
    _description = "Notification Channel"
    _order = "sequence, id"

    name = fields.Char(string="Channel Name", required=True, translate=True)
    channel_type = fields.Selection(
        selection=[
            ("email", "Email"),
            ("odoo", "Odoo Inbox"),
            ("line", "LINE"),
        ],
        string="Channel Type",
        required=True,
        default="odoo",
    )
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)

    _channel_type_uniq = models.Constraint(
        "unique(channel_type)",
        "Channel type must be unique.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "name" not in vals:
                type_map = dict(self._fields["channel_type"].selection)
                vals["name"] = type_map.get(vals.get("channel_type"), vals.get("channel_type"))
        return super().create(vals_list)
