# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def _od19_draft_session_info(self):
        return self.env["od19.draft"]._get_client_config()

    def session_info(self):
        result = super().session_info()
        result["od19_draft"] = self._od19_draft_session_info()
        return result

    @api.model
    def get_frontend_session_info(self):
        result = super().get_frontend_session_info()
        result["od19_draft"] = self._od19_draft_session_info()
        return result
