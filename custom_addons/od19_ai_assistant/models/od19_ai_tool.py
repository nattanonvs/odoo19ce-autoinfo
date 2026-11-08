# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Read-only Odoo data tools exposed to the AI assistant.

The assistant never writes to the database: every tool below performs a
bounded ``search_read`` and returns a compact text summary that is fed
back to the model. Tools whose backing model is not installed are hidden
automatically, so the module keeps working on any Odoo 19 database.
"""

import logging

from odoo import api, models
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

MAX_LIMIT = 20
DEFAULT_LIMIT = 5


class Od19AiTool(models.AbstractModel):
    _name = "od19.ai.tool"
    _description = "เครื่องมืออ่านข้อมูล Odoo สำหรับผู้ช่วย AI (OD19)"

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------
    @api.model
    def _tool_definitions(self):
        """Return every declared tool with its backing Odoo model."""
        return [
            {
                "name": "search_partners",
                "model": "res.partner",
                "description": "ค้นหาคู่ค้า (ลูกค้า/ผู้ขาย) จากชื่อ รหัส หรือเลขผู้เสียภาษี",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "search_products",
                "model": "product.product",
                "description": "ค้นหาสินค้า/บริการ จากชื่อหรือรหัสสินค้า",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "search_sale_orders",
                "model": "sale.order",
                "description": "ค้นหาใบสั่งขาย (Quotation/Sales Order) จากชื่อลูกค้าหรือเลขที่เอกสาร",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "search_invoices",
                "model": "account.move",
                "description": "ค้นหาใบแจ้งหนี้/ใบกำกับภาษี จากชื่อคู่ค้าหรือเลขที่เอกสาร",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
        ]

    @api.model
    def available_tools(self):
        """Return the definitions whose backing model is installed."""
        return [
            tool
            for tool in self._tool_definitions()
            if tool["model"] in self.env
        ]

    @api.model
    def prompt_catalog(self):
        """Human/model readable catalog injected into the system prompt."""
        return "\n".join(
            "- %s (%s): %s"
            % (tool["name"], ", ".join(tool["arguments"]), tool["description"])
            for tool in self.available_tools()
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    @api.model
    def execute(self, name, arguments):
        """Run a tool by ``name`` and return a plain-text result."""
        tool = next(
            (t for t in self.available_tools() if t["name"] == name), None
        )
        if tool is None:
            return "ไม่พบเครื่องมือชื่อ %s" % name
        method = getattr(self, "_run_%s" % name, None)
        if method is None:
            return "เครื่องมือ %s ยังไม่พร้อมใช้งาน" % name
        arguments = arguments if isinstance(arguments, dict) else {}
        try:
            return method(arguments)
        except Exception as exc:  # noqa: BLE001 - never break the chat loop
            _logger.warning("AI tool %s failed: %s", name, exc)
            return "เรียกเครื่องมือ %s ไม่สำเร็จ: %s" % (name, exc)

    # ------------------------------------------------------------------
    # Tool implementations (read-only)
    # ------------------------------------------------------------------
    @api.model
    def _run_search_partners(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain.TRUE
        if keyword:
            domain = Domain.OR(
                [
                    Domain("name", "ilike", keyword),
                    Domain("ref", "ilike", keyword),
                    Domain("vat", "ilike", keyword),
                ]
            )
        records = (
            self.env["res.partner"]
            .sudo()
            .search_read(
                domain,
                ["name", "ref", "vat", "email", "phone"],
                limit=self._safe_limit(arguments.get("limit")),
            )
        )
        return self._format_records(records, ["name", "ref", "vat", "email", "phone"])

    @api.model
    def _run_search_products(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain.TRUE
        if keyword:
            domain = Domain.OR(
                [
                    Domain("name", "ilike", keyword),
                    Domain("default_code", "ilike", keyword),
                ]
            )
        records = (
            self.env["product.product"]
            .sudo()
            .search_read(
                domain,
                ["name", "default_code", "list_price"],
                limit=self._safe_limit(arguments.get("limit")),
            )
        )
        return self._format_records(records, ["name", "default_code", "list_price"])

    @api.model
    def _run_search_sale_orders(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain.TRUE
        if keyword:
            domain = Domain.OR(
                [
                    Domain("name", "ilike", keyword),
                    Domain("partner_id.name", "ilike", keyword),
                ]
            )
        records = (
            self.env["sale.order"]
            .sudo()
            .search_read(
                domain,
                ["name", "partner_id", "date_order", "amount_total", "state"],
                limit=self._safe_limit(arguments.get("limit")),
            )
        )
        return self._format_records(
            records, ["name", "partner_id", "date_order", "amount_total", "state"]
        )

    @api.model
    def _run_search_invoices(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain(
            "move_type",
            "in",
            ["out_invoice", "out_refund", "in_invoice", "in_refund"],
        )
        if keyword:
            domain = domain & Domain.OR(
                [
                    Domain("name", "ilike", keyword),
                    Domain("partner_id.name", "ilike", keyword),
                ]
            )
        records = (
            self.env["account.move"]
            .sudo()
            .search_read(
                domain,
                [
                    "name",
                    "move_type",
                    "partner_id",
                    "invoice_date",
                    "amount_total",
                    "state",
                    "payment_state",
                ],
                limit=self._safe_limit(arguments.get("limit")),
            )
        )
        return self._format_records(
            records,
            [
                "name",
                "move_type",
                "partner_id",
                "invoice_date",
                "amount_total",
                "state",
                "payment_state",
            ],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _safe_limit(self, value):
        try:
            limit = int(value)
        except (TypeError, ValueError):
            return DEFAULT_LIMIT
        return max(1, min(limit, MAX_LIMIT))

    @api.model
    def _format_records(self, records, fields):
        if not records:
            return "ไม่พบข้อมูล"
        lines = []
        for record in records:
            parts = []
            for fname in fields:
                value = record.get(fname)
                if isinstance(value, (list, tuple)) and value:
                    value = value[1]  # many2one -> display name
                if value in (None, False, ""):
                    continue
                parts.append("%s=%s" % (fname, value))
            lines.append("- " + ", ".join(parts))
        return "\n".join(lines)
