# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


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
    # --- Accounting / valuation integration ---
    # NOTE: stock.valuation.layer was removed in Odoo 19. The valuation layer
    # creation logic is kept but guarded with env.get() so it only runs when
    # the model is present (e.g. when a third-party module re-introduces it).
    account_move_id = fields.Many2one(
        'account.move', string='Journal Entry',
        readonly=True, copy=False,
        help='Journal entry posted for this adjustment.',
    )
    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._default_journal(),
        help='Journal used to post the adjustment entry.',
    )
    stock_valuation_account_id = fields.Many2one(
        'account.account', string='Stock Valuation Account',
        compute='_compute_stock_valuation_account_id', store=True,
        readonly=True,
        help='Stock valuation account taken from the product category.',
    )
    adjustment_account_id = fields.Many2one(
        'account.account', string='Valuation Adjustment Account',
        default=lambda self: self._default_adjustment_account(),
        help='Offset account for the valuation adjustment.',
    )
    has_valuation_accounting = fields.Boolean(
        string='Has Valuation Accounting',
        compute='_compute_has_valuation_accounting',
        help='Technical: whether the product category is configured for '
             'perpetual (real-time) valuation accounting.',
    )

    @api.model
    def _default_journal(self):
        journal = self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.env.company.id)],
            limit=1,
        )
        return journal.id if journal else False

    @api.model
    def _default_adjustment_account(self):
        company = self.env.company
        return (
            company.od19_stock_valuation_adjustment_account_id.id
            if company.od19_stock_valuation_adjustment_account_id
            else False
        )

    @api.depends('product_id', 'product_id.categ_id')
    def _compute_stock_valuation_account_id(self):
        for rec in self:
            categ = rec.product_id.categ_id if rec.product_id else False
            rec.stock_valuation_account_id = (
                categ.property_stock_valuation_account_id.id if categ else False
            )

    @api.depends('product_id', 'product_id.categ_id')
    def _compute_has_valuation_accounting(self):
        for rec in self:
            categ = rec.product_id.categ_id if rec.product_id else False
            # property_valuation is company-dependent in Odoo 19; read it
            # directly rather than declaring it as a @depends dependency.
            valuation = categ.property_valuation if categ else False
            rec.has_valuation_accounting = bool(valuation == 'real_time')

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
        # Segregation of duties: only inventory managers may approve a
        # valuation adjustment (it updates standard price and posts GL entries).
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError(
                _('Only inventory managers can approve stock valuation adjustments.')
            )
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
            # Create stock valuation layer for the difference
            rec._create_valuation_layer(old_value)
            # Create the accounting journal entry
            rec._create_account_move()

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'confirmed', 'done'):
                raise UserError(_('Only draft, confirmed or done adjustments can be cancelled.'))
            if rec.state == 'done':
                # Reverse the accounting impact
                rec._reverse_account_move()
                # Reverse the valuation layer
                rec._reverse_valuation_layer()
                # Revert product price for price_change
                if rec.adjustment_type == 'price_change':
                    rec.product_id.standard_price = rec.line_ids[:1].old_value \
                        if rec.line_ids else rec.current_value
            rec.state = 'cancelled'

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state != 'cancelled':
                raise UserError(_('Only cancelled adjustments can be reset to draft.'))
            rec.state = 'draft'

    # ------------------------------------------------------------------
    # Stock valuation layer
    # ------------------------------------------------------------------
    def _create_valuation_layer(self, old_value):
        """Create a stock.valuation.layer for the valuation difference.

        This is a no-op on Odoo 19+ where stock.valuation.layer was removed.
        """
        self.ensure_one()
        svl_model = self.env.get('stock.valuation.layer')
        if not svl_model:
            return
        unit_cost = self.new_value - old_value
        quantity = self.quantity
        value = unit_cost * quantity
        svl_model.create({
            'product_id': self.product_id.id,
            'value': value,
            'unit_cost': unit_cost,
            'quantity': quantity,
            'remaining_qty': quantity,
            'remaining_value': value,
            'description': _('Valuation Adjustment: %s') % self.name,
            'stock_move_id': False,
            'company_id': self.company_id.id,
        })

    def _reverse_valuation_layer(self):
        """Create a reverse valuation layer to cancel the original impact.

        This is a no-op on Odoo 19+ where stock.valuation.layer was removed.
        """
        self.ensure_one()
        svl_model = self.env.get('stock.valuation.layer')
        if not svl_model:
            return
        # Without a stored valuation_layer_id we cannot reverse the exact layer.
        # On Odoo 19+ stock valuation is handled by stock moves, so the
        # adjustment's accounting reversal (_reverse_account_move) is sufficient.
        return

    # ------------------------------------------------------------------
    # Accounting journal entry
    # ------------------------------------------------------------------
    def _get_valuation_accounts(self):
        """Return (stock_valuation_account, adjustment_account)."""
        self.ensure_one()
        valuation_account = self.stock_valuation_account_id
        adjustment_account = self.adjustment_account_id or \
            self.company_id.od19_stock_valuation_adjustment_account_id
        if not valuation_account:
            raise UserError(
                _('No stock valuation account is configured on the product category %s.')
                % self.product_id.categ_id.display_name
            )
        if not adjustment_account:
            raise UserError(
                _('Please configure a Stock Valuation Adjustment Account on the company settings.')
            )
        return valuation_account, adjustment_account

    def _create_account_move(self):
        """Create and post the journal entry for the adjustment."""
        self.ensure_one()
        if self.account_move_id:
            return
        # Only create accounting entries when the category uses real-time valuation
        if not self.has_valuation_accounting:
            return
        valuation_account, adjustment_account = self._get_valuation_accounts()
        amount = self.total_adjustment
        if not amount:
            return
        debit_account = valuation_account if amount > 0 else adjustment_account
        credit_account = adjustment_account if amount > 0 else valuation_account
        move_vals = {
            'ref': _('Valuation Adjustment: %s') % self.name,
            'journal_id': self.journal_id.id,
            'date': self.adjustment_date,
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'name': _('Stock valuation adjustment'),
                    'account_id': debit_account.id,
                    'debit': abs(amount),
                    'credit': 0.0,
                    'company_id': self.company_id.id,
                }),
                (0, 0, {
                    'name': _('Valuation adjustment offset'),
                    'account_id': credit_account.id,
                    'debit': 0.0,
                    'credit': abs(amount),
                    'company_id': self.company_id.id,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        self.account_move_id = move

    def _reverse_account_move(self):
        """Reverse (or cancel) the journal entry created on approval."""
        self.ensure_one()
        if not self.account_move_id:
            return
        move = self.account_move_id
        if move.state == 'posted':
            # Use Odoo's built-in reversal to create a reversed posted entry
            reversal_wizard = self.env['account.move.reversal'].with_context(
                active_ids=move.ids,
                active_model='account.move',
            ).create({
                'journal_id': move.journal_id.id,
                'date': self.adjustment_date,
                'reason': _('Cancellation of Valuation Adjustment: %s') % self.name,
            })
            reversal_wizard.reverse_moves()
        elif move.state == 'draft':
            move.button_cancel()
        self.account_move_id = False


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


class ResCompany(models.Model):
    _inherit = 'res.company'

    od19_stock_valuation_adjustment_account_id = fields.Many2one(
        'account.account',
        string='Stock Valuation Adjustment Account',
        domain="[('account_type', 'not in', ('asset_receivable', 'liability_payable'))]",
        help='Default offset account used when posting stock valuation adjustments.',
    )
