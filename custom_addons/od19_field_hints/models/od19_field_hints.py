# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models

from odoo.tools import str2bool


class Od19FieldHints(models.AbstractModel):
    _name = "od19.field.hints"
    _description = "OD19 Field Hints Config"

    def _get_client_config(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": str2bool(params.get_param("od19_field_hints.enabled", "True")),
        }
