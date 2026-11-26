# -*- coding: utf-8 -*-
"""Field & Label Engine — เพิ่ม/แก้ฟิลด์จากข้อมูล ผ่าน ir.model.fields + ir.ui.view"""
import logging
import re

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Od19ScFieldDef(models.Model):
    _name = "od19.sc.field.def"
    _description = "Service Center — Field Definition"
    _order = "template_id, target_model, sequence, id"

    template_id = fields.Many2one("od19.sc.template", required=True, ondelete="cascade")
    mode = fields.Selection(
        [("create", "Create new field"), ("existing", "Change existing field")],
        default="create", required=True)
    target_model = fields.Char(required=True, help="เช่น maintenance.equipment")
    name = fields.Char(
        required=True,
        help="ชื่อเทคนิคของฟิลด์ — ฟิลด์ใหม่จะถูกเติม prefix x_ ให้อัตโนมัติ")
    field_description = fields.Char(string="Label", required=True)
    ttype = fields.Selection(
        [
            ("char", "Text (single line)"),
            ("text", "Text (multi line)"),
            ("html", "HTML"),
            ("integer", "Integer"),
            ("float", "Decimal"),
            ("monetary", "Monetary"),
            ("boolean", "Boolean"),
            ("date", "Date"),
            ("datetime", "Date & Time"),
            ("selection", "Selection"),
            ("many2one", "Many2one"),
            ("many2many", "Many2many"),
        ],
        string="Field Type", default="char", required=True)
    required = fields.Boolean()
    readonly = fields.Boolean()
    invisible = fields.Boolean(help="ซ่อนฟิลด์บนฟอร์ม (ใช้กับฟิลด์ที่มีอยู่แล้ว)")
    help = fields.Char(string="Tooltip")
    selection_values = fields.Text(help="หนึ่งบรรทัดต่อหนึ่งค่า รูปแบบ: key|Label")
    relation = fields.Char(help="comodel สำหรับ many2one / many2many")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    ir_field_id = fields.Many2one("ir.model.fields", readonly=True, ondelete="set null")
    ir_view_id = fields.Many2one("ir.ui.view", readonly=True, ondelete="set null")

    def _selection_pairs(self):
        pairs = []
        for line in (self.selection_values or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if "|" in line:
                key, label = line.split("|", 1)
            else:
                key = label = line
            pairs.append((key.strip(), label.strip()))
        return pairs

    def _tech_name(self):
        name = (self.name or "").strip()
        name = re.sub(r"[^0-9a-zA-Z_]", "_", name)
        if not name.startswith("x_"):
            name = "x_" + name
        return name

    def _materialize(self):
        self.ensure_one()
        model = self.env["ir.model"].search([("model", "=", self.target_model)], limit=1)
        if not model:
            raise UserError(_("Model '%s' was not found.") % self.target_model)
        if self.mode == "create":
            self._materialize_new(model)
        else:
            self._materialize_existing()

    def _materialize_new(self, model):
        self.ensure_one()
        vals = {
            "name": self._tech_name(),
            "field_description": self.field_description,
            "model_id": model.id,
            "ttype": self.ttype,
            "required": self.required,
            "readonly": self.readonly,
            "help": self.help or False,
        }
        if self.ttype in ("many2one", "many2many") and self.relation:
            vals["relation"] = self.relation
        if self.ttype == "selection":
            pairs = self._selection_pairs()
            vals["selection_ids"] = [
                (0, 0, {"value": key, "name": label, "sequence": index * 10})
                for index, (key, label) in enumerate(pairs)
            ]
        field = self.ir_field_id
        if field and field.exists():
            safe = {k: v for k, v in vals.items()
                    if k in ("field_description", "required", "readonly", "help")}
            field.write(safe)
            if self.ttype == "selection":
                field.selection_ids.unlink()
                for index, (key, label) in enumerate(self._selection_pairs()):
                    self.env["ir.model.fields.selection"].create({
                        "field_id": field.id, "value": key, "name": label, "sequence": index * 10,
                    })
        else:
            field = self.env["ir.model.fields"].create(vals)
            self.ir_field_id = field.id

    def _materialize_existing(self):
        self.ensure_one()
        field = self.env["ir.model.fields"].search(
            [("model", "=", self.target_model), ("name", "=", self.name)], limit=1)
        if field and field.state == "manual":
            field.write({
                "field_description": self.field_description,
                "required": self.required,
                "readonly": self.readonly,
                "help": self.help or False,
            })
            self.ir_field_id = field.id
        else:
            self._materialize_existing_view()

    def _materialize_existing_view(self):
        """แก้ Label/required/invisible ของฟิลด์ฐาน ผ่าน inherited view (ข้อมูล ไม่ใช่ core)."""
        self.ensure_one()
        view = self.env["ir.ui.view"].search(
            [("model", "=", self.target_model), ("type", "=", "form"),
             ("mode", "=", "primary"), ("inherit_id", "=", False)], limit=1)
        if not view:
            raise UserError(
                _("No primary form view found for model '%s'; cannot override field '%s'.")
                % (self.target_model, self.name))
        attributes = []
        if self.field_description:
            attributes.append('<attribute name="string">%s</attribute>' % self.field_description)
        if self.required:
            attributes.append('<attribute name="required">1</attribute>')
        if self.invisible:
            attributes.append('<attribute name="invisible">1</attribute>')
        if self.help:
            attributes.append('<attribute name="help">%s</attribute>' % self.help)
        if not attributes:
            return
        arch = (
            '<data><field name="%s" position="attributes">%s</field></data>'
            % (self.name, "".join(attributes))
        )
        vals = {
            "name": "od19.sc: %s.%s" % (self.target_model, self.name),
            "model": self.target_model,
            "inherit_id": view.id,
            "mode": "extension",
            "priority": 99,
            "arch": arch,
        }
        if self.ir_view_id and self.ir_view_id.exists():
            self.ir_view_id.write(vals)
        else:
            self.ir_view_id = self.env["ir.ui.view"].create(vals).id
