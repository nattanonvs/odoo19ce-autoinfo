# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class IsoDocument(models.Model):
    _inherit = "od19.iso.document"

    dar_ids = fields.One2many(
        "od19.iso.dar", "document_id", string="ใบคำขอ DAR"
    )
    dar_count = fields.Integer(
        string="จำนวนใบ DAR", compute="_compute_dar_count"
    )

    @api.depends("dar_ids")
    def _compute_dar_count(self):
        for doc in self:
            doc.dar_count = len(doc.dar_ids)

    def action_new_revision_keep_approved(self):
        """เพิ่ม revision ใหม่ของเอกสารเดิม โดยคงสถานะอนุมัติไว้

        ต่างจาก ``action_new_revision`` ของ core ที่ reset เป็น draft
        ใช้กับผลหลังอนุมัติของใบ DAR ประเภท 'แก้ไข / เพิ่ม Revision'
        """
        for doc in self:
            if doc.status != "approved":
                raise UserError(
                    _("สามารถเพิ่ม revision ได้เฉพาะเอกสารที่อนุมัติแล้วเท่านั้น")
                )
            self.env["od19.iso.document.revision"].create({
                "document_id": doc.id,
                "revision": doc.revision,
                "effective_date": doc.effective_date,
                "approved_by": self.env.user.id,
                "note": _("เพิ่ม revision ใหม่ (คงสถานะอนุมัติ)"),
            })
            doc.revision = f"{int(doc.revision) + 1:02d}"
            doc.message_post(
                body=_("เพิ่ม revision ใหม่ Rev.%s (คงสถานะอนุมัติ)") % doc.revision
            )

    def action_view_dar(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "od19_iso_dar.action_od19_iso_dar"
        )
        action["domain"] = [("document_id", "=", self.id)]
        action["context"] = {"default_document_id": self.id}
        return action
