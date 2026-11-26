# -*- coding: utf-8 -*-
"""Designer RPC backend — thin, permission-checked bridge between the OWL UI
and the ``od19.sc.*`` config engine models.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

# Fields the designer UI is allowed to read/write per model.
_DIMENSIONS = {
    "od19.sc.menu.node": {
        "read": ["id", "name", "parent_id", "sequence", "menu_type", "target_model",
                 "view_mode", "target_url", "client_tag", "group_ids", "active"],
        "write": ["name", "parent_id", "sequence", "menu_type", "target_model",
                  "view_mode", "target_url", "client_tag", "active"],
    },
    "od19.sc.field.def": {
        "read": ["id", "target_model", "mode", "name", "field_description", "ttype",
                 "required", "readonly", "invisible", "help", "selection_values",
                 "relation", "sequence", "active"],
        "write": ["target_model", "mode", "name", "field_description", "ttype",
                  "required", "readonly", "invisible", "help", "selection_values",
                  "relation", "sequence", "active"],
    },
    "od19.sc.design.token": {
        "read": ["id", "key", "value", "sequence", "active"],
        "write": ["key", "value", "sequence", "active"],
    },
    "od19.sc.formula": {
        "read": ["id", "name", "target_model", "target_field", "expression", "trigger",
                 "cron_interval_number", "cron_interval_type", "sequence", "active",
                 "last_result"],
        "write": ["name", "target_model", "target_field", "expression", "trigger",
                  "cron_interval_number", "cron_interval_type", "sequence", "active"],
    },
    "od19.sc.integration.endpoint": {
        "read": ["id", "name", "direction", "url", "method", "headers", "payload_template",
                 "auth_token_param", "mapping_model", "schedule", "cron_interval_number",
                 "cron_interval_type", "sequence", "active", "last_status", "last_run"],
        "write": ["name", "direction", "url", "method", "headers", "payload_template",
                  "auth_token_param", "mapping_model", "schedule", "cron_interval_number",
                  "cron_interval_type", "sequence", "active"],
    },
}

_TEMPLATE_FIELDS = ["id", "name", "code", "department", "header_title",
                    "header_subtitle", "sequence", "active", "note"]


class Od19ScDesigner(models.TransientModel):
    _name = "od19.sc.designer"
    _description = "Service Center Designer (RPC bridge)"

    name = fields.Char(default="Service Designer")

    # ------------------------------------------------------------------
    # Bootstrap / read
    # ------------------------------------------------------------------
    @api.model
    def _selection(self, model_name, field_name):
        field = self.env[model_name]._fields[field_name]
        return [{"value": value, "label": label} for value, label in field.selection]

    @api.model
    def get_bootstrap(self):
        self.check_access("read")
        templates = self.env["od19.sc.template"].search_read(
            [], _TEMPLATE_FIELDS, order="sequence, id")
        return {
            "templates": templates,
            "meta": {
                "menu_types": self._selection("od19.sc.menu.node", "menu_type"),
                "field_modes": self._selection("od19.sc.field.def", "mode"),
                "field_types": self._selection("od19.sc.field.def", "ttype"),
                "formula_triggers": self._selection("od19.sc.formula", "trigger"),
                "interval_types": self._selection("od19.sc.formula", "cron_interval_type"),
                "directions": self._selection("od19.sc.integration.endpoint", "direction"),
                "http_methods": self._selection("od19.sc.integration.endpoint", "method"),
            },
        }

    @api.model
    def get_template(self, template_id):
        template = self.env["od19.sc.template"].browse(int(template_id)).exists()
        if not template:
            raise UserError(_("Template not found."))
        template.check_access("read")
        data = {"template": template.read(_TEMPLATE_FIELDS)[0]}
        for model_name, spec in _DIMENSIONS.items():
            records = self.env[model_name].search_read(
                [("template_id", "=", template.id)], spec["read"])
            data[model_name] = records
        return data

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    @api.model
    def save_record(self, model_name, template_id, vals, rec_id=None):
        spec = _DIMENSIONS.get(model_name)
        if not spec:
            raise UserError(_("Model '%s' cannot be edited from the designer.") % model_name)
        model = self.env[model_name]
        clean = {key: value for key, value in (vals or {}).items() if key in spec["write"]}
        if rec_id:
            record = model.browse(int(rec_id))
            record.check_access("write")
            record.write(clean)
        else:
            clean["template_id"] = int(template_id)
            record = model.create(clean)
        return record.read(spec["read"])[0]

    @api.model
    def delete_record(self, model_name, rec_id):
        if model_name not in _DIMENSIONS:
            raise UserError(_("Model '%s' cannot be edited from the designer.") % model_name)
        record = self.env[model_name].browse(int(rec_id))
        record.check_access("unlink")
        record.unlink()
        return True

    # ------------------------------------------------------------------
    # Apply / preview / rollback
    # ------------------------------------------------------------------
    @api.model
    def save_template(self, template_id, vals):
        template = self.env["od19.sc.template"].browse(int(template_id))
        template.check_access("write")
        clean = {key: value for key, value in (vals or {}).items()
                 if key in ("name", "code", "department", "header_title",
                            "header_subtitle", "sequence", "note")}
        template.write(clean)
        return template.read(_TEMPLATE_FIELDS)[0]

    @api.model
    def apply_template(self, template_id):
        template = self.env["od19.sc.template"].browse(int(template_id))
        template.check_access("write")
        template.action_apply()
        return True

    @api.model
    def preview_template(self, template_id):
        template = self.env["od19.sc.template"].browse(int(template_id))
        template.check_access("read")
        return {
            "name": template.name,
            "menu_nodes": len(template.menu_node_ids),
            "field_defs": len(template.field_def_ids),
            "design_tokens": len(template.design_token_ids),
            "formulas": len(template.formula_ids),
            "integrations": len(template.integration_ids),
            "revisions": len(template.revision_ids),
        }

    @api.model
    def rollback_template(self, template_id):
        template = self.env["od19.sc.template"].browse(int(template_id))
        template.check_access("write")
        template.action_rollback_last()
        return True

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    @api.model
    def test_formula(self, formula_id):
        formula = self.env["od19.sc.formula"].browse(int(formula_id))
        formula.check_access("write")
        formula.action_test()
        return formula.last_result or ""

    @api.model
    def test_integration(self, endpoint_id):
        endpoint = self.env["od19.sc.integration.endpoint"].browse(int(endpoint_id))
        endpoint.check_access("write")
        endpoint.action_test_connection()
        return endpoint.last_status or ""
