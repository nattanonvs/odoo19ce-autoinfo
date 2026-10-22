# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    od19_zkteco_enabled = fields.Boolean(
        related='company_id.od19_zkteco_enabled',
        readonly=False,
    )
    od19_zkteco_comm_key = fields.Char(
        related='company_id.od19_zkteco_comm_key',
        readonly=False,
    )
    od19_zkteco_allow_auto_register = fields.Boolean(
        related='company_id.od19_zkteco_allow_auto_register',
        readonly=False,
    )
    od19_zkteco_match_field = fields.Selection(
        related='company_id.od19_zkteco_match_field',
        readonly=False,
    )
    od19_zkteco_auto_process = fields.Boolean(
        related='company_id.od19_zkteco_auto_process',
        readonly=False,
    )
    od19_zkteco_grace_minutes = fields.Integer(
        related='company_id.od19_zkteco_grace_minutes',
        readonly=False,
    )
