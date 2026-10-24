# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.fields import Command


class PurchaseOrder(models.Model):
    _name = "purchase.order"
    _inherit = ["purchase.order", "od19.document.pull.mixin"]

    od19_pull_source_label = fields.Char(
        string="Source Documents / เอกสารต้นทาง",
        compute="_compute_od19_pull_source_label",
    )

    @api.depends("order_line.purchase_request_lines")
    def _compute_od19_pull_source_label(self):
        for order in self:
            parts = [
                "%s (%s)" % (source.display_name, count)
                for source, count in order._od19_pull_bound_sources()
            ]
            order.od19_pull_source_label = ", ".join(parts) or False

    # ------------------------------------------------------------------
    # Contract
    # ------------------------------------------------------------------

    def _od19_pull_editable_states(self):
        return ("draft", "sent")

    def _od19_pull_source_specs(self):
        self.ensure_one()
        return [
            {
                "model": "purchase.request",
                "label": _("Purchase Request / ใบขอซื้อ"),
                "domain": [("state", "in", ("approved", "in_progress"))],
            },
        ]

    def _od19_pull_candidate_lines(self, source):
        self.ensure_one()
        if source._name != "purchase.request":
            return self.env["purchase.request.line"].browse()
        taken = self.order_line.purchase_request_lines
        return source.line_ids.filtered(lambda line: line not in taken)

    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        return {
            "res_model": line._name,
            "res_id": line.id,
            "source_name": source.display_name,
            "product_id": line.product_id.id,
            "name": line.name or line.product_id.display_name,
            "qty_to_pull": line.product_qty,
            "price_unit": line.od19_price_unit or 0.0,
            "product_uom_id": line.product_uom_id.id,
        }

    def _od19_pull_apply(self, source, lines):
        """Delegate creation to the OCA wizard so allocations stay correct."""
        self.ensure_one()
        self._od19_pull_check_editable()
        if source._name != "purchase.request" or not lines:
            return 0
        item_commands = [
            Command.create(
                {
                    "line_id": pr_line.id,
                    "request_id": pr_line.request_id.id,
                    "product_id": pr_line.product_id.id,
                    "name": pr_line.name or pr_line.product_id.display_name,
                    "product_qty": pr_line.product_qty,
                    "product_uom_id": pr_line.product_uom_id.id,
                }
            )
            for pr_line in lines
        ]
        wizard = self.env["purchase.request.line.make.purchase.order"].create(
            {
                "purchase_order_id": self.id,
                "supplier_id": self.partner_id.id,
                "item_ids": item_commands,
            }
        )
        wizard.make_purchase_order()
        return len(item_commands)

    def _od19_pull_lines_of_source(self, source):
        """Return the order lines bound to ``source``."""
        self.ensure_one()
        return self.order_line.filtered(
            lambda line: source in line.purchase_request_lines.request_id
        )

    def _od19_pull_preview_lines(self, source):
        self.ensure_one()
        return [
            {
                "name": line.name,
                "product_id": line.product_id.id,
                "quantity": line.product_qty,
            }
            for line in self._od19_pull_lines_of_source(source)
        ]

    def _od19_pull_remove(self, source):
        """Remove the order lines of source and free the request lines."""
        self.ensure_one()
        self._od19_pull_check_editable()
        lines = self._od19_pull_lines_of_source(source)
        if not lines:
            return 0
        self.env["purchase.request.allocation"].search(
            [("purchase_line_id", "in", lines.ids)]
        ).unlink()
        count = len(lines)
        lines.unlink()
        return count

    def _od19_pull_bound_sources(self):
        self.ensure_one()
        found = []
        for source in self.order_line.purchase_request_lines.request_id:
            found.append((source, len(self._od19_pull_lines_of_source(source))))
        return found
