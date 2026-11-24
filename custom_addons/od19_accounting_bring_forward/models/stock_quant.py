from odoo import api, fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    od19_bf_id = fields.Many2one("od19.bring.forward", string="Bring Forward")

    @api.model
    def _get_inventory_fields_create(self):
        res = super()._get_inventory_fields_create()
        return res + ["od19_bf_id"]

    def _get_inventory_move_values(
        self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False
    ):
        res = super()._get_inventory_move_values(
            qty,
            location_id,
            location_dest_id,
            package_id=package_id,
            package_dest_id=package_dest_id,
        )
        res.update({"od19_bf_id": self.od19_bf_id.id})
        return res
