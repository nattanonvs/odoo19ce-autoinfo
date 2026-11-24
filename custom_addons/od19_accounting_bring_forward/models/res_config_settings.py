from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    bring_forward_journal_id = fields.Many2one(
        "account.journal",
        string="Bring Forward Journal",
        domain="[('type', '=', 'general')]",
        help="สมุดรายวันเริ่มต้นที่ใช้บันทึกรายการยกยอดปิดงวด",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bring_forward_journal_id = fields.Many2one(
        related="company_id.bring_forward_journal_id",
        readonly=False,
    )
