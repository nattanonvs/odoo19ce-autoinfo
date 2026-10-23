# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Od19TransportOrder(models.Model):
    _name = 'od19.transport.order'
    _description = 'Transport Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tier.validation']
    _order = 'date desc, id desc'

    # OCA tier validation: confirm requires approval when cost exceeds the
    # threshold defined in data/transport_tier_definition.xml.
    _state_field = 'state'
    _state_from = ['draft', 'waiting_approval']
    _state_to = ['confirmed']
    _cancel_state = 'cancelled'
    _tier_validation_manual_config = False

    name = fields.Char(string='Reference', default='/', readonly=True, copy=False)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting Approval'),
        ('confirmed', 'Confirmed'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', tracking=True)
    driver_id = fields.Many2one('hr.employee', string='Driver', tracking=True)

    route_id = fields.Many2one('od19.transport.route', string='Route', tracking=True)
    origin_location = fields.Char(string='Origin', required=True, tracking=True)
    destination_location = fields.Char(string='Destination', required=True, tracking=True)

    distance_km = fields.Float(string='Distance (km)', tracking=True)
    transport_cost = fields.Monetary(string='Transport Cost', currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)

    picking_ids = fields.Many2many('stock.picking', string='Transfers',
                                    relation='od19_transport_order_picking_rel',
                                    column1='transport_order_id', column2='picking_id')
    picking_count = fields.Integer(string='Transfer Count', compute='_compute_picking_count')

    departure_time = fields.Datetime(string='Departure Time', tracking=True)
    arrival_time = fields.Datetime(string='Arrival Time', tracking=True)

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for order in self:
            order.picking_count = len(order.picking_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('od19.transport.order') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm transport orders, routing through tier validation.

        Orders whose cost requires approval are moved to the
        ``waiting_approval`` state and a validation request is created
        instead of being confirmed directly. Once every tier is validated
        the order can be confirmed by pressing Confirm again.
        """
        awaiting = self.browse()
        for order in self:
            if not order.vehicle_id:
                raise UserError(_('Please specify a vehicle.'))
            if not order.driver_id:
                raise UserError(_('Please specify a driver.'))
            # ``need_validation`` is a non-stored computed field, so it can
            # still hold the value cached before the validation request was
            # created. Drop that stale value so the check below is accurate.
            order.invalidate_recordset(['need_validation'])
            if order.review_ids:
                if order.validation_status != 'validated':
                    raise UserError(
                        _('This transport order is waiting for tier validation '
                          'before it can be confirmed.')
                    )
            elif order.need_validation:
                awaiting |= order
        if awaiting:
            awaiting.write({'state': 'waiting_approval'})
            awaiting.request_validation()
        remaining = self - awaiting
        for order in remaining:
            order.state = 'confirmed'

    def action_start_transit(self):
        for order in self:
            if order.state != 'confirmed':
                raise UserError(_('Only confirmed orders can start transit.'))
            order.state = 'in_transit'
            order.departure_time = fields.Datetime.now()

    def action_deliver(self):
        for order in self:
            if order.state != 'in_transit':
                raise UserError(_('Only in-transit orders can be delivered.'))
            order.state = 'delivered'
            order.arrival_time = fields.Datetime.now()

    def action_cancel(self):
        for order in self:
            if order.state in ('delivered',):
                raise UserError(_('Delivered orders cannot be cancelled.'))
            order.state = 'cancelled'


class Od19TransportRoute(models.Model):
    _name = 'od19.transport.route'
    _description = 'Transport Route'

    name = fields.Char(string='Route Name', required=True)
    code = fields.Char(string='Code')
    origin = fields.Char(string='Origin', required=True)
    destination = fields.Char(string='Destination', required=True)
    distance_km = fields.Float(string='Distance (km)')
    estimated_hours = fields.Float(string='Estimated Hours')
    active = fields.Boolean(string='Active', default=True)
