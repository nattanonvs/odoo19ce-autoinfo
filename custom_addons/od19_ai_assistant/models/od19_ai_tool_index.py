# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Layer 0 — Capability Index and progressive disclosure.

The system prompt only ever carries a short one-line-per-tool index. When the
model needs a tool's argument schema it asks for it explicitly through
``tool_help``, which keeps the prompt small no matter how many tools exist.
"""

from odoo import api, models


class Od19AiToolIndex(models.AbstractModel):
    _inherit = "od19.ai.tool"

    #: Hard ceiling for the index injected into the system prompt.
    MAX_INDEX_CHARS = 3000
    #: One-line description length inside the index.
    INDEX_DESC_LENGTH = 70

    # ------------------------------------------------------------------
    # Registry contribution
    # ------------------------------------------------------------------
    @api.model
    def _index_definitions(self):
        return [
            {
                "name": "tool_help",
                "model": None,
                "kind": "meta",
                "description": "ดูรายละเอียดพารามิเตอร์ของเครื่องมือหนึ่งตัว",
                "arguments": {"name": "ชื่อเครื่องมือ"},
            },
        ]

    # ------------------------------------------------------------------
    # Index
    # ------------------------------------------------------------------
    @api.model
    def prompt_index(self):
        """One compact line per tool, capped by :attr:`MAX_INDEX_CHARS`."""
        lines = []
        for tool in self.available_tools():
            description = (tool.get("description") or "").strip().splitlines()
            short = description[0] if description else ""
            if len(short) > self.INDEX_DESC_LENGTH:
                short = short[: self.INDEX_DESC_LENGTH - 1] + "…"
            lines.append("- %s: %s" % (tool["name"], short))
        index = "\n".join(lines)
        if len(index) > self.MAX_INDEX_CHARS:
            index = index[: self.MAX_INDEX_CHARS - 1] + "…"
        return index

    @api.model
    def full_schema(self, name):
        """Return the full definition dict of ``name`` (or ``{}``)."""
        return next(
            (t for t in self.available_tools() if t["name"] == name), {}
        )

    # ------------------------------------------------------------------
    # tool_help implementation
    # ------------------------------------------------------------------
    @api.model
    def _run_tool_help(self, arguments):
        name = (arguments.get("name") or "").strip()
        tool = self.full_schema(name)
        if not tool:
            return "ไม่พบเครื่องมือชื่อ %s" % name
        lines = ["เครื่องมือ %s: %s" % (tool["name"], tool["description"])]
        arguments_schema = tool.get("arguments") or {}
        if arguments_schema:
            for key, description in arguments_schema.items():
                lines.append("- %s: %s" % (key, description))
        else:
            lines.append("- (ไม่มีพารามิเตอร์)")
        return "\n".join(lines)
