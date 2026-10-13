# -*- coding: utf-8 -*-
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    qc_inspection_count = fields.Integer(
        string='QC Count',
        compute='_compute_qc_inspection_count',
    )
    qc_inspection_ids = fields.One2many(
        'od19.qc.inspection', 'picking_id',
        string='QC Inspections',
    )

    def _compute_qc_inspection_count(self):
        for picking in self:
            picking.qc_inspection_count = len(picking.qc_inspection_ids)

    def action_view_qc_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'QC Inspections',
            'res_model': 'od19.qc.inspection',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {
                'default_picking_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_inspection_type': 'incoming' if self.picking_type_id.code == 'incoming' else 'outgoing',
            },
        }
