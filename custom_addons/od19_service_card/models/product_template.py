# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_interval = fields.Integer(
        string='Default Service Interval (days)',
        default=0,
        help='Default number of days until the next service for this product.',
    )
