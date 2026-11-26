# -*- coding: utf-8 -*-
"""Portal Page — ผูก Designed Template เข้ากับหน้าพอร์ทัล.

หน้าหนึ่งหน้าอ้าง ``od19.sc.template`` (ดีไซน์/โทเค็นที่ออกแบบไว้) และถือ
การ์ด KPI ของตัวเอง เมื่อเผยแพร่แล้วผู้ใช้พอร์ทัลจะเปิดดูผ่าน
``/my/service-center`` ได้
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Od19ScPortalPage(models.Model):
    _name = "od19.sc.portal.page"
    _description = "Service Center — Portal Page"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    template_id = fields.Many2one(
        "od19.sc.template", required=True, ondelete="restrict", index=True,
        help="เทมเพลตที่ออกแบบไว้ใน Service Center (ให้หัวข้อและชุดดีไซน์)")
    intro = fields.Html(help="คำอธิบายสั้น ๆ ที่แสดงเหนือการ์ดรายงาน")
    sequence = fields.Integer(default=10)
    is_published = fields.Boolean(
        default=True, help="เผยแพร่ให้ผู้ใช้พอร์ทัลเห็น")
    group_ids = fields.Many2many(
        "res.groups", string="Visible to Groups",
        help="ถ้าเว้นว่าง = ผู้ใช้พอร์ทัลทุกคนเห็นได้")
    active = fields.Boolean(default=True)

    kpi_ids = fields.One2many("od19.sc.portal.kpi", "page_id", string="KPI Cards")
    kpi_count = fields.Integer(compute="_compute_kpi_count")

    @api.depends("kpi_ids")
    def _compute_kpi_count(self):
        for page in self:
            page.kpi_count = len(page.kpi_ids)

    # ------------------------------------------------------------------
    # Visibility
    # ------------------------------------------------------------------
    @api.model
    def _visible_domain(self, user):
        """โดเมนกลางของหน้า/การ์ดที่ ``user`` มีสิทธิ์เห็น.

        ใช้ทั้งในคอนโทรลเลอร์พอร์ทัลและเป็นจุดอ้างอิงความปลอดภัยเดียว
        """
        return [
            ("active", "=", True),
            ("is_published", "=", True),
            "|",
            ("group_ids", "=", False),
            ("group_ids", "in", user.all_group_ids.ids),
        ]

    def action_open_portal(self):
        """เปิดหน้าพอร์ทัลของหน้านี้ในแท็บใหม่ (ปุ่มบนฟอร์มหลังบ้าน)."""
        self.ensure_one()
        if not self.is_published:
            raise UserError(_("Publish the page before opening it in the portal."))
        return {
            "type": "ir.actions.act_url",
            "url": "/my/service-center/%s" % self.id,
            "target": "new",
        }
