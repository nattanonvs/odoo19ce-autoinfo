# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ServiceCard(models.Model):
    _name = 'od19.service.card'
    _description = 'Service Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'service_date desc'

    name = fields.Char(
        string='Service Card No.',
        default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        required=True, tracking=True,
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True, tracking=True,
    )
    lot_id = fields.Many2one(
        'stock.lot', string='Lot/Serial',
        domain="[('product_id', '=', product_id)]",
    )
    service_date = fields.Date(
        string='Service Date',
        default=fields.Date.context_today,
        required=True, tracking=True,
    )
    next_service_date = fields.Date(
        string='Next Service Date',
        compute='_compute_next_service_date', store=True,
        help='Automatically computed from service date + service interval.',
    )
    service_interval = fields.Integer(
        string='Service Interval (days)',
        default=0,
        help='Number of days until next service.',
    )
    service_type = fields.Selection([
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Corrective Repair'),
        ('inspection', 'Inspection'),
        ('installation', 'Installation'),
        ('other', 'Other'),
    ], string='Service Type', default='preventive', required=True, tracking=True)
    technician_id = fields.Many2one(
        'res.partner', string='Technician',
        domain="[('is_company', '=', False)]",
    )
    description = fields.Text(string='Service Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        default=lambda self: self.env.user,
    )
    active = fields.Boolean(default=True)

    @api.depends('service_date', 'service_interval')
    def _compute_next_service_date(self):
        for card in self:
            if card.service_date and card.service_interval > 0:
                card.next_service_date = card.service_date + timedelta(days=card.service_interval)
            else:
                card.next_service_date = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('od19.service.card') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for card in self:
            if card.state != 'draft':
                raise UserError(_('Only draft service cards can be confirmed.'))
            card.state = 'confirmed'

    def action_done(self):
        for card in self:
            if card.state != 'confirmed':
                raise UserError(_('Only confirmed service cards can be marked done.'))
            card.state = 'done'

    def action_cancel(self):
        for card in self:
            if card.state == 'done':
                raise UserError(_('Cannot cancel a done service card.'))
            card.state = 'cancelled'

    def action_reset_to_draft(self):
        for card in self:
            card.state = 'draft'
