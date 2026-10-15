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
        help="Optional shared key configured on the device as 'Comm Key'. "
             "When set, the device must send the matching key to be accepted.",
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
