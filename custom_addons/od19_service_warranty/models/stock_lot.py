# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    warranty_start_date = fields.Date(
        string='Warranty Start Date',
        help='Date when warranty coverage begins (usually sale date).',
    )
    warranty_end_date = fields.Date(
        string='Warranty End Date',
        compute='_compute_warranty_end_date',
        store=True,
        help='Date when warranty coverage expires.',
    )
    warranty_status = fields.Selection([
        ('none', 'No Warranty'),
        ('active', 'Active'),
        ('expired', 'Expired'),
    ], string='Warranty Status', compute='_compute_warranty_status', store=True)

    @api.depends('warranty_start_date', 'product_id.product_tmpl_id.warranty_duration', 'product_id.product_tmpl_id.warranty_type')
    def _compute_warranty_end_date(self):
        for lot in self:
            if lot.warranty_start_date and lot.product_id:
                days = lot.product_id.product_tmpl_id._get_warranty_days()
                if days > 0:
                    lot.warranty_end_date = lot.warranty_start_date + timedelta(days=days)
                    continue
            lot.warranty_end_date = False

    @api.depends('warranty_end_date')
    def _compute_warranty_status(self):
        today = fields.Date.context_today(self)
        for lot in self:
            if not lot.warranty_end_date:
                lot.warranty_status = 'none'
            elif lot.warranty_end_date >= today:
                lot.warranty_status = 'active'
            else:
                lot.warranty_status = 'expired'
