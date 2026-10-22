# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    od19_zkteco_enabled = fields.Boolean(
        string="Enable ZKTeco Devices",
        default=True,
    )
    od19_zkteco_comm_key = fields.Char(
        string="ZKTeco Communication Key",
        help="Shared key configured on the device as 'Comm Key'. The device "
             "must send this key to be accepted. Requests without a matching "
             "key are refused.",
    )
    od19_zkteco_allow_auto_register = fields.Boolean(
        string="Allow Auto-registration of Devices",
        default=False,
        help="When enabled, a terminal that sends a valid communication key "
             "but is not yet registered is created automatically. Leave "
             "disabled to accept only devices registered in advance.",
    )
    od19_zkteco_match_field = fields.Selection(
        selection=[
            ('barcode', 'Badge ID (Barcode)'),
            ('pin', 'PIN'),
        ],
        string="Employee Match Field",
        default='barcode',
        help="Field on the employee record used to match a punch coming "
             "from the device.",
    )
    od19_zkteco_auto_process = fields.Boolean(
        string="Process Punches Automatically",
        default=True,
        help="When enabled, punches are paired into attendances right away. "
             "When disabled, use the scheduled action to process them.",
    )
    od19_zkteco_grace_minutes = fields.Integer(
        string="Check-out Grace (minutes)",
        default=0,
        help="Minimum delay before a new punch of the same employee is "
             "treated as a check-out instead of an ignored duplicate.",
    )
