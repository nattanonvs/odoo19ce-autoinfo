# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    od19_scan_count = fields.Integer(
        "จำนวนการสแกน", compute="_compute_od19_scan_count"
    )

    def _compute_od19_scan_count(self):
        Log = self.env["od19.barcode.scan.log"]
        for picking in self:
            picking.od19_scan_count = Log.search_count(
                [("picking_id", "=", picking.id)]
            )

    def action_od19_open_barcode_scanner(self):
        """Open the mobile camera scanner focused on this transfer."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "od19_barcode_camera.scan",
            "name": _("สแกนบาร์โค้ด · %s") % self.name,
            "params": {
                "picking_id": self.id,
                "picking_name": self.name,
            },
        }

    def action_od19_view_scan_history(self):
        """Open the scan history filtered on this transfer."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("ประวัติการสแกน"),
            "res_model": "od19.barcode.scan.log",
            "view_mode": "list,form",
            "domain": [("picking_id", "=", self.id)],
            "context": {"search_default_picking_id": self.id},
        }
