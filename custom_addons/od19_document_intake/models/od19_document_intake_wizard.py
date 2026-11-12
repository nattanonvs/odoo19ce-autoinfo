# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models

LINK_MODELS = [
    ("res.partner", "คู่ค้า"),
    ("account.move", "ใบกำกับ/บิล"),
    ("purchase.order", "ใบสั่งซื้อ"),
    ("sale.order", "ใบสั่งขาย"),
]


class Od19InboxLinkWizard(models.TransientModel):
    _name = "od19.document.inbox.link.wizard"
    _description = "ยืนยันและผูกเอกสารจากกล่องรับเข้า"

    inbox_id = fields.Many2one("od19.document.inbox", required=True, ondelete="cascade")
    category_id = fields.Many2one(
        "od19.document.category", "หมวดเอกสาร", required=True, ondelete="restrict",
    )
    resource_ref = fields.Reference(selection=LINK_MODELS, string="ผูกกับ")

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        inbox = self.env["od19.document.inbox"].browse(
            self.env.context.get("active_id"),
        )
        if inbox:
            values.setdefault("inbox_id", inbox.id)
            values.setdefault("category_id", inbox.suggested_category_id.id)
        return values

    def action_confirm(self):
        self.ensure_one()
        res_model = res_id = False
        if self.resource_ref:
            res_model, res_id = self.resource_ref._name, self.resource_ref.id
        attachment = self.inbox_id._od19_create_attachment(
            category=self.category_id, res_model=res_model, res_id=res_id,
        )
        attachment._od19_run_extraction(self.inbox_id.channel_id)
        self.inbox_id.write({"classify_method": "manual"})
        return {"type": "ir.actions.act_window_close"}


class Od19IntakeUploadLine(models.TransientModel):
    _name = "od19.document.intake.upload.line"
    _description = "บรรทัดอัปโหลดเอกสารยกชุด"

    wizard_id = fields.Many2one(
        "od19.document.intake.upload.wizard", required=True, ondelete="cascade",
    )
    file = fields.Binary("ไฟล์", required=True)
    filename = fields.Char("ชื่อไฟล์")


class Od19IntakeUploadWizard(models.TransientModel):
    _name = "od19.document.intake.upload.wizard"
    _description = "อัปโหลดเอกสารยกชุดเข้าช่องรับเข้า"

    channel_id = fields.Many2one(
        "od19.document.channel", "ช่องทาง", required=True, ondelete="cascade",
    )
    line_ids = fields.One2many(
        "od19.document.intake.upload.line", "wizard_id", "ไฟล์",
    )

    def action_upload(self):
        self.ensure_one()
        Inbox = self.env["od19.document.inbox"]
        created = Inbox
        for line in self.line_ids:
            created |= Inbox.create({
                "name": line.filename or "เอกสารเข้า",
                "filename": line.filename,
                "file": line.file,
                "channel_id": self.channel_id.id,
                "state": "new",
            })
        created.action_process()
        return {
            "type": "ir.actions.act_window",
            "name": "กล่องรับเข้า",
            "res_model": "od19.document.inbox",
            "view_mode": "kanban,form",
            "domain": [("id", "in", created.ids)],
        }
