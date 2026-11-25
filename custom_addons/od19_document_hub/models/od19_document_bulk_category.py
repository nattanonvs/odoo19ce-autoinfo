# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class Od19DocumentBulkCategory(models.TransientModel):
    _name = "od19.document.bulk.category.wizard"
    _description = "จัดหมวดเอกสารเป็นชุด"

    category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", required=True, ondelete="restrict",
    )

    def action_apply(self):
        self.ensure_one()
        attachments = self.env["ir.attachment"].browse(
            self.env.context.get("active_ids", []),
        )
        if attachments:
            attachments.write({"od19_category_id": self.category_id.id})
        return {"type": "ir.actions.act_window_close"}
