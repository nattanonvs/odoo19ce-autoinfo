# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import _, api, fields, models
from odoo.fields import Command


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "od19.document.pull.mixin"]

    od19_pull_source_label = fields.Char(
        string="Source Documents / เอกสารต้นทาง",
        compute="_compute_od19_pull_source_label",
    )

    @api.depends(
        "invoice_line_ids.purchase_line_id",
        "invoice_line_ids.sale_line_ids",
        "invoice_line_ids.od19_source_move_line_id",
    )
    def _compute_od19_pull_source_label(self):
        for move in self:
            parts = [
                "%s (%s)" % (source.display_name, count)
                for source, count in move._od19_pull_bound_sources()
            ]
            move.od19_pull_source_label = ", ".join(parts) or False

    # ------------------------------------------------------------------
    # Contract
    # ------------------------------------------------------------------

    def _od19_pull_source_specs(self):
        self.ensure_one()
        if self.move_type == "in_invoice":
            return [
                {
                    "model": "purchase.order",
                    "label": _("Purchase Order / ใบสั่งซื้อ"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("state", "in", ("purchase", "done")),
                    ],
                },
                {
                    "model": "account.move",
                    "label": _("Previous Vendor Bill / ใบวางบิลเดิม"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("move_type", "=", "in_invoice"),
                        ("state", "=", "posted"),
                        ("id", "!=", self.id),
                    ],
                },
            ]
        if self.move_type == "out_invoice":
            return [
                {
                    "model": "sale.order",
                    "label": _("Sale Order / ใบสั่งขาย"),
                    "domain": [
                        ("partner_id", "=", self.partner_id.id),
                        ("state", "in", ("sale", "done")),
                    ],
                },
            ]
        return []

    def _od19_pull_candidate_lines(self, source):
        self.ensure_one()
        if source._name == "purchase.order":
            taken = self.invoice_line_ids.purchase_line_id.ids
            return source.order_line.filtered(
                lambda l: not l.display_type
                and l.qty_to_invoice > 0
                and l.id not in taken
            )
        if source._name == "sale.order":
            taken = self.invoice_line_ids.sale_line_ids.ids
            return source.order_line.filtered(
                lambda l: not l.display_type
                and l.qty_to_invoice > 0
                and l.id not in taken
            )
        if source._name == "account.move":
            taken = self.invoice_line_ids.od19_source_move_line_id.ids
            return source.invoice_line_ids.filtered(
                lambda l: l.display_type == "product" and l.id not in taken
            )
        return self.env["account.move.line"].browse()

    def _od19_pull_line_info(self, source, line):
        self.ensure_one()
        if source._name in ("purchase.order", "sale.order"):
            return {
                "res_model": line._name,
                "res_id": line.id,
                "source_name": source.display_name,
                "product_id": line.product_id.id,
                "name": line.name,
                "qty_to_pull": line.qty_to_invoice,
                "price_unit": line.price_unit,
                "product_uom_id": line.product_uom_id.id,
            }
        return {
            "res_model": line._name,
            "res_id": line.id,
            "source_name": source.display_name,
            "product_id": line.product_id.id,
            "name": line.name,
            "qty_to_pull": line.quantity,
            "price_unit": line.price_unit,
            "product_uom_id": line.product_uom_id.id,
        }

    def _od19_pull_next_sequence(self):
        self.ensure_one()
        return (max(self.invoice_line_ids.mapped("sequence") or [0])) + 10

    def _od19_pull_apply(self, source, lines):
        self.ensure_one()
        self._od19_pull_check_editable()
        commands = []
        sequence = self._od19_pull_next_sequence()
        if source._name == "purchase.order":
            for po_line in lines.sorted("sequence"):
                vals = po_line._prepare_account_move_line(self)
                vals["sequence"] = sequence
                commands.append(Command.create(vals))
                sequence += 10
        elif source._name == "sale.order":
            for so_line in lines.sorted("sequence"):
                vals = so_line._prepare_invoice_line()
                vals["move_id"] = self.id
                vals["sequence"] = sequence
                commands.append(Command.create(vals))
                sequence += 10
        elif source._name == "account.move":
            for src_line in lines.sorted("sequence"):
                vals = src_line.copy_data(
                    {
                        "move_id": self.id,
                        "od19_source_move_line_id": src_line.id,
                        "sequence": sequence,
                    }
                )[0]
                vals.pop("move_id", None)
                commands.append(Command.create(vals))
                sequence += 10
        if not commands:
            return 0
        self.write({"invoice_line_ids": commands})
        return len(commands)

    def _od19_pull_lines_of_source(self, source):
        """Return the destination lines of self bound to ``source``.

        Shared by ``_od19_pull_remove`` and ``_od19_pull_bound_sources`` so the
        lineage lookup lives in one place.
        """
        self.ensure_one()
        if source._name == "purchase.order":
            return self.invoice_line_ids.filtered(
                lambda l: l.purchase_line_id.order_id == source
            )
        if source._name == "sale.order":
            return self.invoice_line_ids.filtered(
                lambda l: source in l.sale_line_ids.order_id
            )
        if source._name == "account.move":
            return self.invoice_line_ids.filtered(
                lambda l: l.od19_source_move_line_id.move_id == source
            )
        return self.env["account.move.line"].browse()

    def _od19_pull_remove(self, source):
        self.ensure_one()
        self._od19_pull_check_editable()
        lines = self._od19_pull_lines_of_source(source)
        count = len(lines)
        lines.unlink()
        return count

    def _od19_pull_bound_sources(self):
        self.ensure_one()
        found = []
        groups = (
            self.invoice_line_ids.purchase_line_id.order_id,
            self.invoice_line_ids.od19_source_move_line_id.move_id,
            self.invoice_line_ids.sale_line_ids.order_id,
        )
        for sources in groups:
            for source in sources:
                found.append(
                    (source, len(self._od19_pull_lines_of_source(source)))
                )
        return found
