# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    od19_pull_source_label = fields.Char(
        string="Source Document / เอกสารต้นทาง",
        compute="_compute_od19_pull_source_label",
    )

    @api.model
    def _od19_grni_domain(self):
        """Lines received (receipt done) but not yet fully billed."""
        return [
            ("order_id.state", "in", ("purchase", "done")),
            ("qty_received", ">", 0),
            ("qty_to_invoice", ">", 0),
            ("display_type", "=", False),
        ]

    @api.depends("purchase_request_lines.request_id")
    def _compute_od19_pull_source_label(self):
        for line in self:
            requests = line.purchase_request_lines.mapped("request_id")
            line.od19_pull_source_label = (
                ", ".join(sorted(set(requests.mapped("name")))) if requests else "-"
            )
