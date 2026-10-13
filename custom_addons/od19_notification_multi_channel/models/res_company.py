import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    line_enabled = fields.Boolean(
        string="Enable LINE Notifications",
        default=False,
    )
    line_channel_access_token = fields.Char(
        string="LINE Channel Access Token",
        help="Channel access token from LINE Developers Console (Messaging API).",
        copy=False,
    )
    line_channel_secret = fields.Char(
        string="LINE Channel Secret",
        help="Channel secret from LINE Developers Console (for webhook verification).",
        copy=False,
    )
    line_default_channel_id = fields.Many2one(
        comodel_name="notification.channel",
        string="Default LINE Channel",
        domain=[("channel_type", "=", "line")],
    )
