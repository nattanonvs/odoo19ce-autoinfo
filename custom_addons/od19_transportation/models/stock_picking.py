# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transport_order_id = fields.Many2one(
        'od19.transport.order', string='Transport Order',
        help='Transport order assigned to this transfer.',
    )
    transport_order_count = fields.Integer(string='Transport Orders', default=0)

    def action_view_transport_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transport Orders',
            'res_model': 'od19.transport.order',
            'view_mode': 'list,form',
            'domain': [('picking_ids', 'in', self.ids)],
        }
