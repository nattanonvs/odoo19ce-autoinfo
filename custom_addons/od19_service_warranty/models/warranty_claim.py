# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WarrantyClaim(models.Model):
    _name = 'od19.warranty.claim'
    _description = 'Warranty Claim / RMA'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Claim Reference',
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
    claim_date = fields.Date(
        string='Claim Date', default=fields.Date.context_today,
        required=True, tracking=True,
    )
    claim_type = fields.Selection([
        ('warranty', 'Warranty'),
        ('rma', 'RMA (Return Merchandise)'),
        ('repair', 'Repair'),
    ], string='Claim Type', default='warranty', required=True, tracking=True)
    description = fields.Text(string='Problem Description', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)
    under_warranty = fields.Boolean(
        string='Under Warranty', compute='_compute_under_warranty', store=True,
        help='Whether the product is still under warranty at claim date.',
    )
    repair_order_id = fields.Many2one(
        'repair.order', string='Repair Order',
        help='Linked repair order for this claim.',
    )
    resolution = fields.Text(string='Resolution Notes')
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        default=lambda self: self.env.user,
    )

    @api.depends('lot_id.warranty_status', 'lot_id.warranty_end_date', 'claim_date')
    def _compute_under_warranty(self):
        for claim in self:
            if claim.lot_id and claim.lot_id.warranty_status == 'active':
                claim.under_warranty = True
            else:
                claim.under_warranty = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('od19.warranty.claim') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for claim in self:
            if claim.state != 'draft':
                raise UserError(_('Only draft claims can be confirmed.'))
            claim.state = 'confirmed'

    def action_start(self):
        for claim in self:
            if claim.state != 'confirmed':
                raise UserError(_('Only confirmed claims can be started.'))
            claim.state = 'in_progress'

    def action_done(self):
        for claim in self:
            if claim.state != 'in_progress':
                raise UserError(_('Only in-progress claims can be completed.'))
            claim.state = 'done'

    def action_reject(self):
        for claim in self:
            claim.state = 'rejected'

    def action_cancel(self):
        for claim in self:
            if claim.state in ('done', 'rejected'):
                raise UserError(_('Cannot cancel a %s claim.') % claim.state)
            claim.state = 'cancelled'

    def action_create_repair_order(self):
        """Create a repair.order from the warranty claim."""
        self.ensure_one()
        if self.repair_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'repair.order',
                'view_mode': 'form',
                'res_id': self.repair_order_id.id,
            }
        repair_vals = {
            'partner_id': self.partner_id.id,
            'product_id': self.product_id.id,
            'lot_id': self.lot_id.id if self.lot_id else False,
            'under_warranty': self.under_warranty,
            'internal_notes': self.description,
        }
        repair = self.env['repair.order'].create(repair_vals)
        self.repair_order_id = repair.id
        self.state = 'in_progress'
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': repair.id,
        }
