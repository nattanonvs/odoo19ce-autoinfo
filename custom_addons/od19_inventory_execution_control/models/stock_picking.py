from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    od19_flow_class = fields.Selection(
        selection=[
            ("receipt", "Receipt"),
            ("delivery", "Delivery"),
            ("transfer", "Transfer"),
            ("return", "Return"),
        ],
        compute="_compute_od19_flow_class",
        store=True,
        readonly=True,
    )
    od19_execution_state = fields.Selection(
        selection=[
            ("waiting", "Waiting"),
            ("ready", "Ready"),
            ("done", "Done"),
            ("exception", "Exception"),
        ],
        compute="_compute_od19_execution_state",
        store=True,
        readonly=True,
    )

    @api.depends("picking_type_code", "return_id")
    def _compute_od19_flow_class(self):
        for picking in self:
            if picking.return_id:
                picking.od19_flow_class = "return"
            elif picking.picking_type_code == "incoming":
                picking.od19_flow_class = "receipt"
            elif picking.picking_type_code == "outgoing":
                picking.od19_flow_class = "delivery"
            elif picking.picking_type_code == "internal":
                picking.od19_flow_class = "transfer"
            else:
                picking.od19_flow_class = False

    @api.depends("state")
    def _compute_od19_execution_state(self):
        for picking in self:
            if picking.state == "assigned":
                picking.od19_execution_state = "ready"
            elif picking.state == "done":
                picking.od19_execution_state = "done"
            elif picking.state == "cancel":
                picking.od19_execution_state = "exception"
            else:
                picking.od19_execution_state = "waiting"
