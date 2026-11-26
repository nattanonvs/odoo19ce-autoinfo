# -*- coding: utf-8 -*-
"""Portal routes for the Service Center (``/my/service-center``).

หน้าพอร์ทัลเป็น *ผู้บริโภค* ของเทมเพลตที่ออกแบบไว้ใน Service Center:
แสดงหัวข้อ/ชุดดีไซน์ของการออกแบบ พร้อมการ์ด KPI ที่คำนวณจากข้อมูลจริง

ความปลอดภัย: ใช้ ``od19.sc.portal.page._visible_domain()`` เป็นประตูเดียว
(หน้าเผยแพร่ + กลุ่มที่มองเห็นได้) แล้วอ่านเทมเพลต/โทเค็น/KPI ด้วย ``.sudo()``
เพราะการ์ดต้อง query โมเดลปลายทางที่ผู้ใช้พอร์ทัลไม่มีสิทธิ์อ่านโดยตรง
"""
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class Od19ScPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _visible_pages(self):
        Page = request.env["od19.sc.portal.page"].sudo()
        return Page.search(
            Page._visible_domain(request.env.user), order="sequence, id")

    def _get_page(self, page_id):
        Page = request.env["od19.sc.portal.page"].sudo()
        return Page.search(
            Page._visible_domain(request.env.user) + [("id", "=", page_id)],
            limit=1)

    def _portal_values(self, page_name="service_center"):
        values = self._prepare_portal_layout_values()
        values["page_name"] = page_name
        # ``page`` is always defined so the breadcrumb template can rely on it
        # (empty on the index, the current page on the detail view).
        values["page"] = False
        return values

    def _page_values(self, page):
        """ข้อมูลที่เทมเพลตพอร์ทัลต้องใช้ — หัวข้อ, ชุดดีไซน์ และการ์ด KPI."""
        page = page.sudo()
        template = page.template_id
        tokens = {
            (t.key if t.key.startswith("--") else "--%s" % t.key): t.value
            for t in template.design_token_ids.filtered("active")
        }
        kpis = page.kpi_ids.filtered("active").sorted(lambda k: (k.sequence, k.id))
        return {
            "page": page,
            "template": template,
            "tokens": tokens,
            "cards": [kpi._card_values() for kpi in kpis],
        }

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "od19_sc_page_count" in counters:
            values["od19_sc_page_count"] = len(self._visible_pages())
        return values

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route(
        ["/my/service-center", "/my/service-center/page/<int:page>"],
        type="http", auth="user", website=True,
    )
    def portal_my_service_center(self, page=1, **kw):
        values = self._portal_values()
        pages = self._visible_pages()
        pager = portal_pager(
            url="/my/service-center",
            url_args={},
            total=len(pages),
            page=page,
            step=self._items_per_page,
        )
        values.update({
            "pages": pages[pager["offset"]:pager["offset"] + self._items_per_page],
            "pager": pager,
            "default_url": "/my/service-center",
        })
        return request.render("od19_sc_portal.portal_my_service_center", values)

    @http.route(
        "/my/service-center/<int:page_id>",
        type="http", auth="user", website=True,
    )
    def portal_my_service_center_page(self, page_id, **kw):
        page = self._get_page(page_id)
        if not page:
            return request.not_found()
        values = self._portal_values()
        values.update(self._page_values(page))
        return request.render(
            "od19_sc_portal.portal_my_service_center_page", values)
