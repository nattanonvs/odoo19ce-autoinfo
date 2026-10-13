from odoo import _, api, fields, models
from odoo.exceptions import AccessError


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
    backdate_date = fields.Date(
        string="Backdate",
        copy=False,
        help="If set, the stock moves, valuation layers and accounting "
        "entries of this picking will be posted on this date instead of "
        "today. Only inventory managers are allowed to backdate.",
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("backdate_date"):
                self._check_backdate_access()
        return super().create(vals_list)

    def write(self, vals):
        if "backdate_date" in vals and vals["backdate_date"]:
            self._check_backdate_access()
        return super().write(vals)

    def _check_backdate_access(self):
        """Only inventory managers may set a backdate."""
        if not self.env.user.has_group("stock.group_stock_manager"):
            raise AccessError(
                _(
                    "Only inventory managers are allowed to backdate stock "
                    "operations."
                )
            )

    def _action_done(self):
        """Propagate the backdate to the moves before validating."""
        for picking in self:
            if picking.backdate_date:
                picking.move_ids.write({"backdate_date": picking.backdate_date})
        return super()._action_done()
