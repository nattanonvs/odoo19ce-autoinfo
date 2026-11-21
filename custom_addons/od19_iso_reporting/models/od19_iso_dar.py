from datetime import timedelta

from odoo import api, fields, models


class Od19IsoDar(models.Model):
    _inherit = "od19.iso.dar"

    sla_due_date = fields.Date(
        string="SLA Due Date",
        compute="_compute_sla_due_date",
        store=True,
        readonly=True,
        help="วันที่ครบกำหนด SLA ของใบ DAR (วันที่สร้าง + จำนวนวัน SLA)",
    )

    @api.depends("create_date")
    def _compute_sla_due_date(self):
        """วันที่ครบ SLA = วันที่สร้างใบ + ค่า SLA_DAYS ของโมดูล DAR.

        ใช้ ``create_date`` เป็นฐาน ซึ่งตรงกับตรรกะของ ``_cron_dar_sla_reminder``
        ในโมดูล DAR. ถ้า ``create_date`` ยังไม่ถูกตั้งค่า (ระหว่าง create) จะใช้
        เวลาปัจจุบันแทน เพื่อให้ได้วันที่ครบกำหนดที่ถูกต้องเสมอ.
        """
        sla_days = self.SLA_DAYS
        for dar in self:
            base = dar.create_date or fields.Datetime.now()
            dar.sla_due_date = fields.Date.to_date(base) + timedelta(days=sla_days)
