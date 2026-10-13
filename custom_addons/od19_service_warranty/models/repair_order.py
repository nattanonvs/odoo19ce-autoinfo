# -*- coding: utf-8 -*-
from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    warranty_claim_id = fields.Many2one(
        'od19.warranty.claim', string='Warranty Claim',
        help='Warranty claim that originated this repair order.',
    )
