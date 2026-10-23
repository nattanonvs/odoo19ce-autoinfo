# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    od19_source_move_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Source Bill Line / บรรทัดใบวางบิลต้นทาง",
        ondelete="set null",
        copy=False,
        index="btree_not_null",
        help="Previous vendor bill line this line was pulled from (flow 2).",
    )
    od19_source_picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Source Picking / ใบรับ-ส่งต้นทาง",
        ondelete="set null",
        copy=False,
        index="btree_not_null",
        help="Receipt / delivery the quantity of this line was pulled from "
        "(style B: bill by receipt / delivery).",
    )
