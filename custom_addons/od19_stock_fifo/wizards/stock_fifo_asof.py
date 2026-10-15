# -*- coding: utf-8 -*-
"""FIFO As-Of Wizard.

Allows the user to compute FIFO stock valuation for selected products
(or all products) as of a specific date, and review the results in a
tree view.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockFifoAsof(models.TransientModel):
    _name = 'od19.stock.fifo.asof'
    _description = 'FIFO Valuation As-Of Wizard'

    od19_as_of_date = fields.Date(
        string='As Of Date / ณ วันที่',
        required=True,
        default=fields.Date.today,
        help='Compute FIFO valuation up to and including this date.',
    )
    od19_product_ids = fields.Many2many(
        'product.product',
        string='Products / สินค้า',
        help='Leave empty to compute for all products.',
    )

    # ------------------------------------------------------------------
    # Action
    # ------------------------------------------------------------------
    def action_compute_fifo(self):
        """Compute FIFO valuation and display results in a tree view."""
        self.ensure_one()
        if not self.od19_as_of_date:
            raise UserError(_("Please select an as-of date."))

        # Determine products to compute
        if self.od19_product_ids:
            products = self.od19_product_ids
        else:
            products = self.env['product.product'].search([
                ('type', '=', 'consu'),
                ('is_storable', '=', True),
            ])

        if not products:
            raise UserError(_("No products found to compute FIFO valuation for."))

        # Get the FIFO service
        fifo_service = self.env['od19.stock.fifo.service']

        lines_vals = []
        for product in products:
            valuation = fifo_service.compute_fifo_valuation(
                product.id, self.od19_as_of_date,
            )
            lines_vals.append({
                'od19_product_id': product.id,
                'od19_quantity': valuation['quantity_on_hand'],
                'od19_total_value': valuation['total_value'],
                'od19_unit_cost': valuation['unit_cost'],
            })

        # Create transient line records
        lines = self.env['od19.stock.fifo.asof.line'].create(lines_vals)

        # Return action to display the list view
        return {
            'name': _('FIFO Valuation As Of %s') % (self.od19_as_of_date.strftime('%Y-%m-%d'),),
            'type': 'ir.actions.act_window',
            'res_model': 'od19.stock.fifo.asof.line',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('od19_stock_fifo.view_od19_stock_fifo_asof_line_tree').id, 'list'),
                (False, 'form'),
            ],
            'domain': [('id', 'in', lines.ids)],
            'target': 'current',
            'context': dict(self.env.context),
        }


class StockFifoAsofLine(models.TransientModel):
    _name = 'od19.stock.fifo.asof.line'
    _description = 'FIFO Valuation As-Of Line'

    od19_product_id = fields.Many2one(
        'product.product',
        string='Product / สินค้า',
        readonly=True,
    )
    od19_quantity = fields.Float(
        string='Quantity / จำนวน',
        digits='Product Unit of Measure',
        readonly=True,
    )
    od19_total_value = fields.Float(
        string='Total Value / มูลค่ารวม',
        digits='Account',
        readonly=True,
    )
    od19_unit_cost = fields.Float(
        string='Unit Cost / ต้นทุนต่อหน่วย',
        digits='Account',
        readonly=True,
    )
    od19_asof_id = fields.Many2one(
        'od19.stock.fifo.asof',
        string='Wizard',
        ondelete='cascade',
    )
