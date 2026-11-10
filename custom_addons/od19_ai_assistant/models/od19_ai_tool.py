# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Read-only Odoo data tools exposed to the AI assistant.

The assistant never writes to the database: every tool performs a bounded
``search_read`` or ``_read_group`` and returns a compact text summary that is
fed back to the model. Results are read with the *current user's* rights, so
model ACLs and record rules apply exactly as they do on a regular Odoo screen.
Tools whose backing model is not installed are hidden automatically, so the
module keeps working on any Odoo 19 database.
"""

import logging
from datetime import date, datetime

from odoo import api, fields, models
from odoo.fields import Domain

_logger = logging.getLogger(__name__)

MAX_LIMIT = 20
DEFAULT_LIMIT = 5
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y")


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
                "name": "search_purchase_orders",
                "model": "purchase.order",
                "description": "ค้นหาใบสั่งซื้อ (Purchase Order) จากชื่อผู้ขายหรือเลขที่เอกสาร",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "search_invoices",
                "model": "account.move",
                "description": "ค้นหาใบแจ้งหนี้/ใบกำกับภาษี จากชื่อคู่ค้าหรือเลขที่เอกสาร",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "search_journal_items",
                "model": "account.move.line",
                "description": (
                    "ค้นหารายการบัญชีแยกประเภท (GL) ที่บันทึกแล้ว "
                    "จากเลขที่เอกสาร ชื่อ/รหัสบัญชี ชื่อคู่ค้า และช่วงวันที่"
                ),
                "arguments": {
                    "keyword": "คำค้นหา",
                    "date_from": "วันที่เริ่ม (YYYY-MM-DD)",
                    "date_to": "วันที่สิ้นสุด (YYYY-MM-DD)",
                    "limit": "จำนวนผลสูงสุด",
                },
            },
            {
                "name": "search_stock_quants",
                "model": "stock.quant",
                "description": "ค้นหายอดคงเหลือสินค้าคงคลัง (Stock on hand) จากชื่อหรือรหัสสินค้า",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "search_employees",
                "model": "hr.employee",
                "description": "ค้นหาข้อมูลพนักงาน จากชื่อ ตำแหน่ง หรือแผนก",
                "arguments": {"keyword": "คำค้นหา", "limit": "จำนวนผลสูงสุด"},
            },
            {
                "name": "sales_summary",
                "model": "sale.order",
                "description": (
                    "สรุปยอดขายรวมตามเดือน (เฉพาะใบสั่งขายที่ยืนยันแล้ว) "
                    "ระบุช่วงวันที่ได้"
                ),
                "arguments": {
                    "date_from": "วันที่เริ่ม (YYYY-MM-DD)",
                    "date_to": "วันที่สิ้นสุด (YYYY-MM-DD)",
                },
            },
            {
                "name": "tax_summary",
                "model": "account.move",
                "description": (
                    "สรุปภาษีซื้อ/ภาษีขาย (ยอดก่อนภาษี ภาษี ยอดรวม) "
                    "แยกตามประเภทเอกสาร ในช่วงวันที่ที่ระบุ"
                ),
                "arguments": {
                    "date_from": "วันที่เริ่ม (YYYY-MM-DD)",
                    "date_to": "วันที่สิ้นสุด (YYYY-MM-DD)",
                },
            },
            {
                "name": "overdue_receivables",
                "model": "account.move",
                "description": "สรุปยอดลูกหนี้ค้างชำระที่เกินกำหนดชำระ ตามคู่ค้า ณ วันนี้",
                "arguments": {"limit": "จำนวนผลสูงสุด"},
            },
        ]

    @api.model
    def all_tools(self):
        """Every declared tool: curated + generic + meta + draft.

        Each specialised layer contributes through its own ``_*_definitions``
        method (defined in its own file). ``getattr`` keeps the layers optional
        so the module still loads while they are being built.
        """
        definitions = list(self._tool_definitions())
        for method_name in (
            "_generic_definitions",
            "_index_definitions",
            "_draft_definitions",
        ):
            method = getattr(self, method_name, None)
            if method:
                definitions.extend(method())
        return definitions

    @api.model
    def available_tools(self):
        """Definitions whose backing model is installed (model-less = always)."""
        result = []
        for tool in self.all_tools():
            model_name = tool.get("model")
            if model_name is None or model_name in self.env:
                result.append(tool)
        return result

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
        model_name = tool.get("model")
        if model_name and not self._check_read_access(model_name):
            return "คุณไม่มีสิทธิ์อ่านข้อมูล %s" % self.env[
                model_name
            ]._description
        arguments = arguments if isinstance(arguments, dict) else {}
        try:
            return method(arguments)
        except Exception as exc:  # noqa: BLE001 - never break the chat loop
            _logger.warning("AI tool %s failed: %s", name, exc)
            return "เรียกเครื่องมือ %s ไม่สำเร็จ: %s" % (name, exc)

    # ------------------------------------------------------------------
    # Access rights (A3) - read with the current user's real rights
    # ------------------------------------------------------------------
    @api.model
    def _check_read_access(self, model_name):
        """Return whether the current user may read ``model_name``.

        Mirrors Odoo's own ``has_access('read')`` check (model ACL + record
        rules) so the assistant never leaks data the user cannot see.
        """
        if model_name not in self.env:
            return False
        return self.env[model_name].has_access("read")

    # ------------------------------------------------------------------
    # Data access helpers (no sudo: obey the current user's rights)
    # ------------------------------------------------------------------
    @api.model
    def _read_model(self, model_name, domain, fields_, limit):
        return self.env[model_name].search_read(domain, fields_, limit=limit)

    @api.model
    def _group_model(
        self, model_name, domain, groupby, aggregates, limit=None, order=None
    ):
        return self.env[model_name]._read_group(
            domain,
            groupby=groupby,
            aggregates=aggregates,
            limit=limit,
            order=order,
        )

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
        records = self._read_model(
            "res.partner",
            domain,
            ["name", "ref", "vat", "email", "phone"],
            self._safe_limit(arguments.get("limit")),
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
        records = self._read_model(
            "product.product",
            domain,
            ["name", "default_code", "list_price"],
            self._safe_limit(arguments.get("limit")),
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
        records = self._read_model(
            "sale.order",
            domain,
            ["name", "partner_id", "date_order", "amount_total", "state"],
            self._safe_limit(arguments.get("limit")),
        )
        return self._format_records(
            records, ["name", "partner_id", "date_order", "amount_total", "state"]
        )

    @api.model
    def _run_search_purchase_orders(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain.TRUE
        if keyword:
            domain = Domain.OR(
                [
                    Domain("name", "ilike", keyword),
                    Domain("partner_id.name", "ilike", keyword),
                ]
            )
        records = self._read_model(
            "purchase.order",
            domain,
            ["name", "partner_id", "date_order", "amount_total", "state"],
            self._safe_limit(arguments.get("limit")),
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
        records = self._read_model(
            "account.move",
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
            self._safe_limit(arguments.get("limit")),
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

    @api.model
    def _run_search_journal_items(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain("parent_state", "=", "posted")
        if keyword:
            domain = domain & Domain.OR(
                [
                    Domain("move_id.name", "ilike", keyword),
                    Domain("account_id.name", "ilike", keyword),
                    Domain("account_id.code", "ilike", keyword),
                    Domain("partner_id.name", "ilike", keyword),
                ]
            )
        date_from = self._parse_date(arguments.get("date_from"))
        date_to = self._parse_date(arguments.get("date_to"))
        if date_from:
            domain = domain & Domain("date", ">=", date_from)
        if date_to:
            domain = domain & Domain("date", "<=", date_to)
        records = self._read_model(
            "account.move.line",
            domain,
            [
                "date",
                "move_id",
                "account_id",
                "partner_id",
                "debit",
                "credit",
                "balance",
            ],
            self._safe_limit(arguments.get("limit")),
        )
        return self._format_records(
            records,
            [
                "date",
                "move_id",
                "account_id",
                "partner_id",
                "debit",
                "credit",
                "balance",
            ],
        )

    @api.model
    def _run_search_stock_quants(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain("location_id.usage", "=", "internal")
        if keyword:
            domain = domain & Domain.OR(
                [
                    Domain("product_id.name", "ilike", keyword),
                    Domain("product_id.default_code", "ilike", keyword),
                ]
            )
        records = self._read_model(
            "stock.quant",
            domain,
            ["product_id", "location_id", "quantity", "available_quantity"],
            self._safe_limit(arguments.get("limit")),
        )
        return self._format_records(
            records, ["product_id", "location_id", "quantity", "available_quantity"]
        )

    @api.model
    def _run_search_employees(self, arguments):
        keyword = (arguments.get("keyword") or "").strip()
        domain = Domain.TRUE
        if keyword:
            domain = Domain.OR(
                [
                    Domain("name", "ilike", keyword),
                    Domain("job_title", "ilike", keyword),
                    Domain("department_id.name", "ilike", keyword),
                ]
            )
        records = self._read_model(
            "hr.employee",
            domain,
            ["name", "job_title", "department_id", "work_email", "work_phone"],
            self._safe_limit(arguments.get("limit")),
        )
        return self._format_records(
            records, ["name", "job_title", "department_id", "work_email", "work_phone"]
        )

    # ------------------------------------------------------------------
    # Aggregate tools (A2)
    # ------------------------------------------------------------------
    @api.model
    def _run_sales_summary(self, arguments):
        domain = Domain("state", "in", ["sale", "done"])
        date_from = self._parse_date(arguments.get("date_from"))
        date_to = self._parse_date(arguments.get("date_to"))
        if date_from:
            domain = domain & Domain("date_order", ">=", date_from)
        if date_to:
            domain = domain & Domain(
                "date_order", "<=", datetime.combine(date_to, datetime.max.time())
            )
        rows = self._group_model(
            "sale.order",
            domain,
            ["date_order:month"],
            ["amount_total:sum", "__count"],
            order="date_order:month",
        )
        return self._format_groups(
            rows, ["เดือน"], ["ยอดขายรวม", "จำนวนใบสั่งขาย"]
        )

    @api.model
    def _run_tax_summary(self, arguments):
        domain = Domain(
            "move_type",
            "in",
            ["out_invoice", "out_refund", "in_invoice", "in_refund"],
        ) & Domain("state", "=", "posted")
        date_from = self._parse_date(arguments.get("date_from"))
        date_to = self._parse_date(arguments.get("date_to"))
        if date_from:
            domain = domain & Domain("date", ">=", date_from)
        if date_to:
            domain = domain & Domain("date", "<=", date_to)
        rows = self._group_model(
            "account.move",
            domain,
            ["move_type"],
            [
                "amount_untaxed:sum",
                "amount_tax:sum",
                "amount_total:sum",
                "__count",
            ],
            order="move_type",
        )
        return self._format_groups(
            rows,
            ["ประเภทเอกสาร"],
            ["ยอดก่อนภาษี", "ภาษี", "ยอดรวม", "จำนวนเอกสาร"],
        )

    @api.model
    def _run_overdue_receivables(self, arguments):
        today = fields.Date.context_today(self)
        domain = (
            Domain("move_type", "=", "out_invoice")
            & Domain("state", "=", "posted")
            & Domain("payment_state", "in", ["not_paid", "partial"])
            & Domain("invoice_date_due", "<", today)
            & Domain("amount_residual_signed", ">", 0)
        )
        rows = self._group_model(
            "account.move",
            domain,
            ["partner_id"],
            ["amount_residual_signed:sum", "__count"],
            limit=self._safe_limit(arguments.get("limit")),
            order="amount_residual_signed:sum desc",
        )
        return self._format_groups(
            rows, ["คู่ค้า"], ["ยอดค้างชำระ", "จำนวนใบแจ้งหนี้"]
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
    def _parse_date(self, value):
        """Parse a user supplied date into a ``datetime.date`` (or ``None``)."""
        if isinstance(value, date):
            return value
        text = (value or "").strip() if isinstance(value, str) else ""
        if not text:
            return None
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    @api.model
    def _plain_value(self, value):
        """Normalise an ORM value (recordset/date/float) for text output."""
        if isinstance(value, models.BaseModel):
            return value.display_name or ""
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, float):
            return round(value, 2)
        if isinstance(value, (list, tuple)) and value:
            return value[1]  # many2one -> display name
        if value in (None, False, ""):
            return ""
        return value

    @api.model
    def _format_records(self, records, fields_):
        if not records:
            return "ไม่พบข้อมูล"
        lines = []
        for record in records:
            parts = []
            for fname in fields_:
                value = self._plain_value(record.get(fname))
                if value == "":
                    continue
                parts.append("%s=%s" % (fname, value))
            lines.append("- " + ", ".join(parts))
        return "\n".join(lines)

    @api.model
    def _format_groups(self, rows, group_labels, aggregate_labels):
        if not rows:
            return "ไม่พบข้อมูล"
        labels = list(group_labels) + list(aggregate_labels)
        lines = []
        for row in rows:
            values = [self._plain_value(value) for value in row]
            parts = [
                "%s=%s" % (label, value)
                for label, value in zip(labels, values)
                if value != ""
            ]
            lines.append("- " + ", ".join(parts))
        return "\n".join(lines)
