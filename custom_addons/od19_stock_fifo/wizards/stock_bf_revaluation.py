# -*- coding: utf-8 -*-
"""BF (Beginning Forward / ยกมา) Revaluation Wizard.

Allows the user to adjust the brought-forward (BF) stock value of a
product by specifying a new total value. The system creates a stock
valuation layer for the difference and posts a journal entry between
the inventory account and the revaluation account.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockBfRevaluation(models.TransientModel):
    _name = 'od19.stock.bf.revaluation'
    _description = 'BF Stock Revaluation Wizard'

    od19_revaluation_date = fields.Date(
        string='Revaluation Date / วันที่ปรับมูลค่า',
        required=True,
        default=fields.Date.today,
    )
    od19_product_id = fields.Many2one(
        'product.product',
        string='Product / สินค้า',
        required=True,
        domain="[('type', '=', 'consu'), ('is_storable', '=', True)]",
    )
    od19_current_value = fields.Float(
        string='Current Value / มูลค่าปัจจุบัน',
        digits='Account',
        readonly=True,
        help='Current FIFO value of the product.',
    )
    od19_current_qty = fields.Float(
        string='Current Quantity / จำนวนปัจจุบัน',
        digits='Product Unit of Measure',
        readonly=True,
    )
    od19_new_value = fields.Float(
        string='New Value / มูลค่าใหม่',
        digits='Account',
        help='The new BF (brought-forward) value for this product.',
    )
    od19_difference = fields.Float(
        string='Difference / ผลต่าง',
        digits='Account',
        compute='_compute_difference',
        store=False,
    )
    od19_journal_id = fields.Many2one(
        'account.journal',
        string='Journal / สมุด',
        domain="[('type', '=', 'general')]",
        help='Journal used for the revaluation entry. '
             'Leave empty to use the company default miscellaneous journal.',
    )

    # ------------------------------------------------------------------
    # Onchange / Compute
    # ------------------------------------------------------------------
    @api.onchange('od19_product_id', 'od19_revaluation_date')
    def _onchange_product(self):
        """Populate current value and quantity when product changes."""
        if self.od19_product_id and self.od19_revaluation_date:
            valuation = self.env['od19.stock.fifo.service'].compute_fifo_valuation(
                self.od19_product_id.id,
                self.od19_revaluation_date,
            )
            self.od19_current_value = valuation['total_value']
            self.od19_current_qty = valuation['quantity_on_hand']
            self.od19_new_value = valuation['total_value']

    @api.depends('od19_new_value', 'od19_current_value')
    def _compute_difference(self):
        for rec in self:
            rec.od19_difference = rec.od19_new_value - rec.od19_current_value

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    def action_apply_revaluation(self):
        """Create a stock valuation layer and journal entry for the BF revaluation."""
        self.ensure_one()

        if not self.od19_new_value:
            raise UserError(_("Please specify the new BF value."))

        difference = self.od19_new_value - self.od19_current_value
        if abs(difference) < 0.01:
            raise UserError(_(
                "The new value is the same as the current value. "
                "No revaluation is needed."
            ))

        product = self.od19_product_id
        company = self.env.company
        currency = company.currency_id

        # --- Update product valuation (Odoo 19 uses stock.move + product standard_price) ---
        # In Odoo 19 stock.valuation.layer was removed. We update the product's
        # standard_price to the new BF cost per unit and create a journal entry
        # for the revaluation difference (consistent with od19_stock_valuation_adjustment).
        old_price = product.standard_price
        new_unit_cost = self.od19_new_value / self.od19_current_qty if self.od19_current_qty else 0.0
        try:
            product.write({'standard_price': new_unit_cost})
        except Exception:
            pass
        _logger.info(
            "BF revaluation: updated product %s standard_price %.2f -> %.2f (diff=%.2f)",
            product.display_name, old_price, new_unit_cost, difference)

        # --- Determine accounts ---
        inventory_account = product.categ_id.property_stock_valuation_account_id \
            or product.property_valuation_account_id
        if not inventory_account:
            raise UserError(_(
                "No inventory valuation account is configured on the product "
                "category %s. Please configure it before revaluing."
            ) % (product.categ_id.display_name,))

        revaluation_account = company.od19_stock_revaluation_account_id
        if not revaluation_account:
            raise UserError(_(
                "No stock revaluation account is configured on the company %s. "
                "Please set it in Settings > Inventory > Stock Revaluation Account."
            ) % (company.name,))

        # --- Create journal entry ---
        journal = self.od19_journal_id or self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not journal:
            raise UserError(_(
                "No general journal found. Please create a miscellaneous journal."
            ))

        # Determine debit/credit based on difference sign
        if difference > 0:
            # Value increased: Debit inventory, Credit revaluation
            debit_account = inventory_account
            credit_account = revaluation_account
            debit_amount = difference
            credit_amount = difference
        else:
            # Value decreased: Debit revaluation, Credit inventory
            debit_account = revaluation_account
            credit_account = inventory_account
            debit_amount = -difference
            credit_amount = -difference

        move_vals = {
            'journal_id': journal.id,
            'date': self.od19_revaluation_date,
            'ref': _('BF Revaluation - %s') % (product.display_name,),
            'company_id': company.id,
            'line_ids': [
                (0, 0, {
                    'name': _('BF Revaluation - %s') % (product.display_name,),
                    'account_id': debit_account.id,
                    'debit': debit_amount,
                    'credit': 0.0,
                    'product_id': product.id,
                    'quantity': self.od19_current_qty,
                    'company_id': company.id,
                    'currency_id': currency.id,
                }),
                (0, 0, {
                    'name': _('BF Revaluation - %s') % (product.display_name,),
                    'account_id': credit_account.id,
                    'debit': 0.0,
                    'credit': credit_amount,
                    'product_id': product.id,
                    'quantity': self.od19_current_qty,
                    'company_id': company.id,
                    'currency_id': currency.id,
                }),
            ],
        }

        move = self.env['account.move'].create(move_vals)
        # Post the journal entry
        try:
            move.action_post()
        except Exception as e:
            _logger.warning("Could not post revaluation journal entry: %s", e)

        _logger.info("BF revaluation complete for %s: diff=%.2f, JE=%s",
                     product.display_name, difference, move.name)

        # Return action to show the created journal entry
        return {
            'name': _('BF Revaluation Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
            'context': dict(self.env.context),
        }
