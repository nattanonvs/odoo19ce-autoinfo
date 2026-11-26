# -*- coding: utf-8 -*-
"""Designed Template — หัวเทมเพลต + ตัวสั่ง apply/rollback ของเอนจิน 5 มิติ."""
import base64
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

THEME_ASSET_NAME = "od19_sc_theme"
THEME_ATTACHMENT_NAME = "od19_sc_theme.css"


class Od19ScTemplate(models.Model):
    _name = "od19.sc.template"
    _description = "Service Center — Designed Template"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="รหัสเทมเพลต เช่น TA-01")
    department = fields.Char(help="แผนก/กลุ่มธุรกิจ เช่น TA, Service")
    header_title = fields.Char(string="Design Header Name")
    header_subtitle = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    note = fields.Text()

    menu_node_ids = fields.One2many("od19.sc.menu.node", "template_id")
    field_def_ids = fields.One2many("od19.sc.field.def", "template_id")
    design_token_ids = fields.One2many("od19.sc.design.token", "template_id")
    formula_ids = fields.One2many("od19.sc.formula", "template_id")
    integration_ids = fields.One2many("od19.sc.integration.endpoint", "template_id")
    revision_ids = fields.One2many("od19.sc.revision", "template_id")

    menu_node_count = fields.Integer(compute="_compute_counts")
    field_def_count = fields.Integer(compute="_compute_counts")
    design_token_count = fields.Integer(compute="_compute_counts")
    formula_count = fields.Integer(compute="_compute_counts")
    integration_count = fields.Integer(compute="_compute_counts")

    @api.depends("menu_node_ids", "field_def_ids", "design_token_ids", "formula_ids", "integration_ids")
    def _compute_counts(self):
        for tpl in self:
            tpl.menu_node_count = len(tpl.menu_node_ids)
            tpl.field_def_count = len(tpl.field_def_ids)
            tpl.design_token_count = len(tpl.design_token_ids)
            tpl.formula_count = len(tpl.formula_ids)
            tpl.integration_count = len(tpl.integration_ids)

    # ------------------------------------------------------------------
    # Snapshot / restore (revision)
    # ------------------------------------------------------------------
    _SNAPSHOT_FIELDS = {
        "od19.sc.menu.node": ["name", "sequence", "menu_type", "target_model", "view_mode",
                              "target_url", "client_tag", "active"],
        "od19.sc.field.def": ["mode", "target_model", "name", "field_description", "ttype",
                              "required", "readonly", "invisible", "help", "selection_values",
                              "relation", "sequence", "active"],
        "od19.sc.design.token": ["key", "value", "sequence", "active"],
        "od19.sc.formula": ["name", "target_model", "target_field", "expression", "trigger",
                            "cron_interval_number", "cron_interval_type", "sequence", "active"],
        "od19.sc.integration.endpoint": ["name", "direction", "url", "method", "headers",
                                         "payload_template", "auth_token_param", "schedule",
                                         "cron_interval_number", "cron_interval_type",
                                         "sequence", "active"],
    }

    @api.model
    def _rec_vals(self, record, field_names):
        vals = {}
        for fname in field_names:
            field = record._fields[fname]
            value = record[fname]
            if field.type == "many2one":
                vals[fname] = value.id if value else False
            elif field.type in ("one2many", "many2many"):
                vals[fname] = value.ids
            elif field.type in ("date", "datetime"):
                vals[fname] = str(value) if value else False
            else:
                vals[fname] = value
        return vals

    def _snapshot(self):
        self.ensure_one()
        data = {"meta": self.read(["name", "code", "department", "header_title", "header_subtitle", "note"])[0]}
        # menu nodes: keep hierarchy via index of parent in the (id-sorted) list
        nodes = self.menu_node_ids.sorted(lambda n: n.id)
        node_ids = nodes.ids
        menu_dump = []
        for node in nodes:
            vals = self._rec_vals(node, self._SNAPSHOT_FIELDS["od19.sc.menu.node"])
            vals["group_ids"] = node.group_ids.ids
            pid = node.parent_id.id
            vals["_parent_index"] = node_ids.index(pid) if pid in node_ids else False
            menu_dump.append(vals)
        data["od19.sc.menu.node"] = menu_dump
        for model_name in ("od19.sc.field.def", "od19.sc.design.token", "od19.sc.formula",
                           "od19.sc.integration.endpoint"):
            recs = self.env[model_name].search([("template_id", "=", self.id)])
            data[model_name] = [self._rec_vals(r, self._SNAPSHOT_FIELDS[model_name]) for r in recs]
        return data

    def _restore_snapshot(self, data):
        self.ensure_one()
        for model_name in ("od19.sc.menu.node", "od19.sc.field.def", "od19.sc.design.token",
                           "od19.sc.formula", "od19.sc.integration.endpoint"):
            self.env[model_name].search([("template_id", "=", self.id)]).unlink()
        meta = data.get("meta") or {}
        self.write({
            "header_title": meta.get("header_title"),
            "header_subtitle": meta.get("header_subtitle"),
            "note": meta.get("note"),
        })
        node_recs = []
        for vals in data.get("od19.sc.menu.node", []):
            vals = dict(vals)
            parent_index = vals.pop("_parent_index", False)
            group_ids = vals.pop("group_ids", [])
            if parent_index is not False and parent_index is not None and parent_index < len(node_recs):
                vals["parent_id"] = node_recs[parent_index].id
            node = self.env["od19.sc.menu.node"].create(dict(vals, template_id=self.id))
            if group_ids:
                node.group_ids = [(6, 0, group_ids)]
            node_recs.append(node)
        for model_name in ("od19.sc.field.def", "od19.sc.design.token", "od19.sc.formula",
                           "od19.sc.integration.endpoint"):
            for vals in data.get(model_name, []):
                self.env[model_name].create(dict(vals, template_id=self.id))
        self._materialize_all()

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------
    def action_apply(self):
        """เก็บ revision แล้ว materialize ของจริงทุกมิติ."""
        for tpl in self:
            self.env["od19.sc.revision"].create({
                "template_id": tpl.id,
                "name": _("Snapshot before apply"),
                "snapshot": json.dumps(tpl._snapshot(), default=str),
            })
            tpl._materialize_all()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Service Center"),
                "message": _("Applied the designed template."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_preview(self):
        """คืนคำอธิบายสิ่งที่จะถูกสร้าง/แก้ (ไม่ลงมือจริง)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Preview — %s") % (self.name or ""),
                "message": self._preview_message(),
                "type": "info",
                "sticky": True,
            },
        }

    def _preview_message(self):
        self.ensure_one()
        lines = [
            _("Menus: %s") % len(self.menu_node_ids),
            _("Fields: %s") % len(self.field_def_ids),
            _("Design tokens: %s") % len(self.design_token_ids),
            _("Formulas: %s") % len(self.formula_ids),
            _("Integrations: %s") % len(self.integration_ids),
        ]
        return "\n".join(lines)

    def _materialize_all(self):
        self.ensure_one()
        self._materialize_menu()
        self._materialize_field()
        self._materialize_theme()
        self._materialize_formula()
        self._materialize_integration()
        return True

    def action_rollback_last(self):
        self.ensure_one()
        rev = self.env["od19.sc.revision"].search([("template_id", "=", self.id)], order="id desc", limit=1)
        if not rev:
            raise UserError(_("No revision available to roll back."))
        return rev.action_restore()

    # ------------------------------------------------------------------
    # Materializers
    # ------------------------------------------------------------------
    def _materialize_menu(self):
        self.ensure_one()
        nodes = self.menu_node_ids.filtered(lambda n: n.active)
        ordered, seen = [], set()

        def visit(node):
            if node.id in seen:
                return
            if node.parent_id and node.parent_id.id not in seen:
                visit(node.parent_id)
            seen.add(node.id)
            ordered.append(node)

        for node in nodes.sorted(lambda r: (r.sequence, r.id)):
            visit(node)
        for node in ordered:
            node._materialize()

    def _materialize_field(self):
        self.ensure_one()
        for fd in self.field_def_ids.filtered("active"):
            fd._materialize()

    def _materialize_theme(self):
        self.ensure_one()
        css = self._build_theme_css()
        Attachment = self.env["ir.attachment"]
        att = Attachment.search([("name", "=", THEME_ATTACHMENT_NAME)], limit=1)
        vals = {
            "name": THEME_ATTACHMENT_NAME,
            "mimetype": "text/css",
            "public": True,
            "datas": base64.b64encode(css.encode("utf-8")),
        }
        if att:
            att.write(vals)
        else:
            att = Attachment.create(vals)
        path = "/web/content/%s/%s" % (att.id, THEME_ATTACHMENT_NAME)
        asset = self.env["ir.asset"].search([("name", "=", THEME_ASSET_NAME)], limit=1)
        asset_vals = {
            "name": THEME_ASSET_NAME,
            "bundle": "web.assets_backend",
            "directive": "append",
            "path": path,
            "active": True,
        }
        if asset:
            asset.write(asset_vals)
        else:
            self.env["ir.asset"].create(asset_vals)
        self.env.registry.clear_cache("assets")

    def _build_theme_css(self):
        tokens = self.env["od19.sc.design.token"].search([("template_id.active", "=", True)])
        lines = []
        for token in tokens.sorted(lambda t: (t.template_id.sequence, t.sequence, t.id)):
            key = token.key if token.key.startswith("--") else "--%s" % token.key
            lines.append("  %s: %s;" % (key, token.value))
        css = ":root {\n%s\n}\n" % "\n".join(lines)
        for tpl in self.search([("active", "=", True)], order="sequence, id"):
            if tpl.header_title:
                css += "\n.o_main_navbar .od19-sc-brand::after { content: \"%s\"; }\n" % tpl.header_title
        return css

    def _materialize_formula(self):
        self.ensure_one()
        for formula in self.formula_ids.filtered("active"):
            formula._materialize()

    def _materialize_integration(self):
        self.ensure_one()
        for endpoint in self.integration_ids.filtered("active"):
            endpoint._materialize()
