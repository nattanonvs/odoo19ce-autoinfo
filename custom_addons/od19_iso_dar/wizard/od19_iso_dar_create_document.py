# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class Od19IsoDarCreateDocument(models.TransientModel):
    _name = "od19.iso.dar.create.document"
    _description = "สร้างเอกสาร ISO ใหม่จากใบ DAR"

    dar_id = fields.Many2one(
        "od19.iso.dar",
        default=lambda self: self.env.context.get("active_id"),
        required=True,
    )
    document_title = fields.Char(string="ชื่อเอกสาร", required=True)
    category_id = fields.Many2one("od19.iso.document.category", string="ประเภทเอกสาร")
    department_id = fields.Many2one("hr.department", string="แผนก")
    revision = fields.Char(string="Revision", default="00")

    def action_create_document(self):
        self.ensure_one()
        if not self.env.user.has_group("od19_iso_dar.group_iso_dar_controller") \
                and not self.env.user.has_group("base.group_system"):
            raise UserError(_("เฉพาะ Document Controller เท่านั้นที่ยืนยันสร้างเอกสารได้"))
        doc = self.env["od19.iso.document"].create({
            "document_title": self.document_title,
            "category_id": self.category_id.id or self.dar_id.category_id.id,
            "department_id": self.department_id.id or self.dar_id.department_id.id,
            "revision": self.revision or "00",
            "standard_ids": [(6, 0, self.dar_id.standard_ids.ids)],
            "iso_clause": self.dar_id.iso_clause,
        })
        self.dar_id.document_id = doc.id
        self.dar_id.message_post(body=_("สร้างเอกสารใหม่ %s จากใบ DAR") % doc.code)
        return {
            "type": "ir.actions.act_window",
            "res_model": "od19.iso.document",
            "res_id": doc.id,
            "view_mode": "form",
            "target": "current",
        }
