# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockValuationAdjustment(models.Model):
    _name = 'od19.stock.valuation.adjustment'
    _description = 'Stock Valuation Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True,
    )
    adjustment_type = fields.Selection([
        ('price_change', 'Price Change'),
        ('write_up', 'Write-Up'),
        ('write_down', 'Write-Down'),
    ], string='Adjustment Type', default='price_change', required=True, tracking=True)
    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True, tracking=True,
    )
    quantity = fields.Float(
        string='Quantity', default=1.0, required=True,
        help='Quantity affected by this adjustment.',
    )
    current_value = fields.Float(
        string='Current Value',
        compute='_compute_current_value', store=True,
        help='Current stock value per unit.',
    )
    new_value = fields.Float(
        string='New Value',
        help='New value per unit after adjustment.',
    )
    total_adjustment = fields.Float(
        string='Total Adjustment',
        compute='_compute_total_adjustment', store=True,
        help='Total value adjustment (new - current) * quantity.',
    )
    adjustment_date = fields.Date(
        string='Adjustment Date',
        default=fields.Date.context_today,
        required=True, tracking=True,
    )
    reason = fields.Text(string='Reason', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    user_id = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user,
    )
    approved_by = fields.Many2one(
        'res.users', string='Approved By',
        readonly=True, copy=False,
    )
    line_ids = fields.One2many(
        'od19.stock.valuation.adjustment.line', 'adjustment_id',
        string='Valuation Audit Trail',
    )

    @api.depends('product_id', 'quantity')
    def _compute_current_value(self):
        for rec in self:
            if rec.product_id:
                rec.current_value = rec.product_id.standard_price
            else:
                rec.current_value = 0.0

    @api.depends('current_value', 'new_value', 'quantity')
    def _compute_total_adjustment(self):
        for rec in self:
            rec.total_adjustment = (rec.new_value - rec.current_value) * rec.quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('od19.stock.valuation.adjustment') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft adjustments can be confirmed.'))
            if not rec.new_value:
                raise UserError(_('Please specify the new value.'))
            rec.state = 'confirmed'

    def action_approve(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only confirmed adjustments can be approved.'))
            old_value = rec.current_value
            rec.approved_by = self.env.user
            rec.state = 'done'
            # Update product standard price
            if rec.adjustment_type == 'price_change':
                rec.product_id.standard_price = rec.new_value
            # Create audit trail line
            rec.env['od19.stock.valuation.adjustment.line'].create({
                'adjustment_id': rec.id,
                'product_id': rec.product_id.id,
                'old_value': old_value,
                'new_value': rec.new_value,
                'quantity': rec.quantity,
                'adjustment_type': rec.adjustment_type,
                'user_id': self.env.user.id,
            })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('Cannot cancel an approved adjustment.'))
            rec.state = 'cancelled'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'


class StockValuationAdjustmentLine(models.Model):
    _name = 'od19.stock.valuation.adjustment.line'
    _description = 'Stock Valuation Adjustment Audit Line'
    _order = 'create_date desc'

    adjustment_id = fields.Many2one(
        'od19.stock.valuation.adjustment', string='Adjustment',
        required=True, ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True,
    )
    old_value = fields.Float(string='Old Value')
    new_value = fields.Float(string='New Value')
    quantity = fields.Float(string='Quantity')
    adjustment_type = fields.Selection([
        ('price_change', 'Price Change'),
        ('write_up', 'Write-Up'),
        ('write_down', 'Write-Down'),
    ], string='Adjustment Type')
    user_id = fields.Many2one('res.users', string='Done By')
    create_date = fields.Datetime(string='Date', readonly=True)
