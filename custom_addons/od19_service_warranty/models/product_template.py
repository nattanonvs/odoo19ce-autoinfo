# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_duration = fields.Integer(
        string='Warranty Duration (days)',
        default=0,
        help='Number of days of warranty coverage from the date of sale.',
    )
    warranty_type = fields.Selection([
        ('none', 'No Warranty'),
        ('days', 'Days'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string='Warranty Type', default='none')

    def _get_warranty_days(self):
        """Return warranty duration in days based on warranty_type."""
        self.ensure_one()
        if self.warranty_type == 'none' or self.warranty_duration <= 0:
            return 0
        multiplier = {
            'days': 1,
            'months': 30,
            'years': 365,
        }.get(self.warranty_type, 0)
        return self.warranty_duration * multiplier
