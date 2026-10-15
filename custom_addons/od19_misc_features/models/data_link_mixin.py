# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Abstract mixin helping to preserve sale/purchase line references.

When new invoice lines are created from source documents (for example from a
down payment or from a sale/purchase order), the link to the originating
``sale.order.line`` / ``purchase.order.line`` must be carried over so that
analytic entries, delivered quantities and invoice reporting stay consistent.

This mixin provides two small helpers that copy those references from a set of
origin lines onto ``self``. The mapping is positional (line ``i`` of ``self``
corresponds to line ``i`` of ``origin_lines``).
"""

from odoo import models


class Od19DataLinkMixin(models.AbstractModel):
    _name = "od19.data.link.mixin"
    _description = "OD19 Data Link Mixin (preserve SO/PO line references)"

    def _preserve_sale_line_ids(self, origin_lines):
        """Copy ``sale_line_ids`` from ``origin_lines`` onto ``self``.

        :param origin_lines: recordset of source lines that carry
            ``sale_line_ids`` (e.g. ``account.move.line`` or any model
            exposing a ``sale_line_ids`` many2many).
        :returns: ``self``
        """
        for new_line, origin_line in zip(self, origin_lines):
            if (
                "sale_line_ids" in origin_line._fields
                and "sale_line_ids" in new_line._fields
            ):
                new_line.sale_line_ids = origin_line.sale_line_ids.ids
        return self

    def _preserve_purchase_line_id(self, origin_lines):
        """Copy ``purchase_line_id`` from ``origin_lines`` onto ``self``.

        :param origin_lines: recordset of source lines that carry
            ``purchase_line_id``.
        :returns: ``self``
        """
        for new_line, origin_line in zip(self, origin_lines):
            if (
                "purchase_line_id" in origin_line._fields
                and "purchase_line_id" in new_line._fields
            ):
                new_line.purchase_line_id = origin_line.purchase_line_id
        return self
