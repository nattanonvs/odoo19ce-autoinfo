# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""Layer 3 — external provider registry (structure only, disabled by default).

Phase 2 (internet: web search/fetch) and phase 3 (company systems: ZKTeco,
e-Tax, currency bot, external DB) plug in here. Nothing is enabled now; the
registry merely exists so those phases are additive.
"""

from odoo import api, models


class Od19AiProvider(models.AbstractModel):
    _name = "od19.ai.provider"
    _description = "ทะเบียนผู้ให้บริการภายนอกของผู้ช่วย AI (OD19)"

    @api.model
    def _provider_definitions(self):
        """External tools; populated in phase 2/3. Empty for now."""
        return []

    @api.model
    def enabled(self):
        return bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("od19_ai.external_enabled")
        )

    @api.model
    def list_tools(self):
        if not self.enabled():
            return []
        return list(self._provider_definitions())

    @api.model
    def execute(self, name, arguments):
        if not self.enabled():
            return "ยังไม่เปิดใช้งานเครื่องมือภายนอก: %s" % name
        return "ยังไม่รองรับเครื่องมือภายนอก: %s" % name
