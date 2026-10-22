# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    # Filled from the linked Goods Issue order. The dependency goes through the
    # searchable path ``move_ids.allocation_ids.stock_request_id.order_id``
    # because the OCA ``stock.picking.stock_request_ids`` is a non-stored
    # computed One2many and therefore cannot be used as a dependency trigger.
    od19_goods_issue_reason = fields.Text(
        string="เหตุผลการเบิก / Issue Reason",
        compute="_compute_od19_goods_issue_info",
        store=True,
        readonly=False,
    )
    od19_goods_issue_department_id = fields.Many2one(
        comodel_name="hr.department",
        string="แผนกที่ขอเบิก / Requesting Department",
        compute="_compute_od19_goods_issue_info",
        store=True,
        readonly=False,
    )

    @api.depends(
        "move_ids.allocation_ids.stock_request_id.order_id.od19_reason",
        "move_ids.allocation_ids.stock_request_id.order_id.department_id",
    )
    def _compute_od19_goods_issue_info(self):
        for picking in self:
            order = picking.stock_request_ids.mapped("order_id")[:1]
            picking.od19_goods_issue_reason = order.od19_reason if order else False
            picking.od19_goods_issue_department_id = (
                order.department_id if order else False
            )
