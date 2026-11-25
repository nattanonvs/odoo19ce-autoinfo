import logging

from odoo import api, fields, models

from .blog_content import _od19_write_translations

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seeded notices
#
# (xmlid suffix, notice_type, published_date, expiry_date, website_url,
#  {lang: name}, {lang: body})
#
# ``od19_setup_notices`` is replayed on every upgrade through a <function> tag
# in ``data/setup_functions.xml``.  Each notice is tracked by an ir.model.data
# xmlid, so re-running the setup refreshes the existing notice (and repairs its
# translations) instead of creating a duplicate.
# ---------------------------------------------------------------------------
NOTICES = [
    (
        "notice_new_year_closure", "info", "2025-12-20", "2027-01-15", False,
        {"en_US": "New Year holiday — office closure",
         "th_TH": "แจ้งปิดทำการช่วงวันหยุดปีใหม่"},
        {"en_US": "<p>Our offices will be closed for the New Year holidays. "
                  "Emergency support for active maintenance contracts stays available "
                  "through the usual service hotline.</p>",
         "th_TH": "<p>สำนักงานของเราจะปิดทำการในช่วงวันหยุดปีใหม่ "
                  "โดยทีมสนับสนุนฉุกเฉินสำหรับสัญญาบริการที่ยังมีผลยังพร้อมให้บริการผ่านสายด่วนบริการตามปกติ</p>"},
    ),
    (
        "notice_portal_maintenance", "warning", "2026-01-05", False, False,
        {"en_US": "Scheduled maintenance — Customer Portal",
         "th_TH": "แจ้งปิดปรับปรุงระบบ — Customer Portal"},
        {"en_US": "<p>The Customer Portal will be briefly unavailable during a scheduled "
                  "maintenance window. During this time the portal may be read-only or "
                  "temporarily offline. We apologise for any inconvenience.</p>",
         "th_TH": "<p>ระบบ Customer Portal จะปิดให้บริการชั่วคราวในช่วงเวลาปรับปรุงระบบตามกำหนด "
                  "ในระหว่างนี้อาจใช้งานได้เฉพาะการอ่านหรือไม่สามารถเข้าใช้งานได้ชั่วคราว "
                  "ขออภัยในความไม่สะดวก</p>"},
    ),
    (
        "notice_iso_recertified", "info", "2024-12-04", False, "/quality-certifications",
        {"en_US": "ISO 9001:2015 certification renewed",
         "th_TH": "ต่ออายุการรับรอง ISO 9001:2015"},
        {"en_US": "<p>Our quality management system has been re-certified to ISO 9001:2015. "
                  "This certification covers project delivery, service operations and "
                  "procurement. See our <a href=\"/quality-certifications\">Quality &amp; "
                  "Certifications</a> page for details.</p>",
         "th_TH": "<p>ระบบบริหารคุณภาพของบริษัทได้รับการรับรอง ISO 9001:2015 ต่ออายุแล้ว "
                  "โดยครอบคลุมงานส่งมอบโครงการ งานบริการ และงานจัดซื้อ "
                  "ดูรายละเอียดได้ที่หน้า <a href=\"/quality-certifications\">คุณภาพและการรับรอง</a></p>"},
    ),
]


class Od19CustomerNotice(models.Model):
    """Notices published to customers inside the portal (``/my``).

    A lightweight, website-facing counterpart to ``od19_announcement``:
    staff announcements target employees, whereas these notices are shown to
    logged-in customers on their portal home page.
    """

    _name = "od19.customer.notice"
    _description = "Customer Notice"
    _order = "published_date desc, id desc"

    name = fields.Char(string="Title", required=True, translate=True)
    body = fields.Html(translate=True, sanitize_attributes=False)
    notice_type = fields.Selection(
        [
            ("info", "Information"),
            ("warning", "Warning"),
            ("mandatory", "Important"),
        ],
        string="Type",
        default="info",
        required=True,
    )
    published = fields.Boolean(default=False)
    published_date = fields.Date(readonly=True)
    expiry_date = fields.Date(help="Hide this notice automatically after this date.")
    website_url = fields.Char(
        string="Details link",
        help="Optional URL shown as a link under the notice.",
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("published") and not vals.get("published_date"):
                vals["published_date"] = fields.Date.context_today(self)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("published") and not vals.get("published_date"):
            vals = dict(vals, published_date=fields.Date.context_today(self))
        return super().write(vals)

    @api.model
    def od19_published_notices(self, limit=5):
        """Return the notices a customer should currently see."""
        today = fields.Date.context_today(self)
        domain = [
            ("published", "=", True),
            ("active", "=", True),
            "|", ("expiry_date", "=", False), ("expiry_date", ">=", today),
        ]
        return self.sudo().search(domain, limit=limit)

    def action_publish(self):
        self.write({"published": True})

    def action_unpublish(self):
        self.write({"published": False})

    # ------------------------------------------------------------------
    # Seed data (replayed on every upgrade, idempotent)
    # ------------------------------------------------------------------
    @api.model
    def od19_setup_notices(self):
        """Seed the default portal notices, keyed by an ir.model.data xmlid."""
        ModelData = self.env["ir.model.data"].sudo()
        for suffix, notice_type, published_date, expiry_date, url, name, body in NOTICES:
            data = ModelData.search([
                ("module", "=", "od19_website"),
                ("name", "=", suffix),
                ("model", "=", self._name),
            ], limit=1)
            notice = self.sudo().browse(data.res_id).exists() if data else self.browse()
            values = {
                "notice_type": notice_type,
                "published": True,
                "published_date": published_date,
                "expiry_date": expiry_date or False,
                "website_url": url or False,
            }
            if notice:
                notice.sudo().write(values)
            else:
                notice = self.sudo().create(dict(
                    values, name=name["en_US"], body=body["en_US"]))
                if data:
                    data.res_id = notice.id
                else:
                    ModelData.create({
                        "module": "od19_website",
                        "name": suffix,
                        "model": self._name,
                        "res_id": notice.id,
                        "noupdate": True,
                    })
            _od19_write_translations(notice, {"name": name, "body": body})
        _logger.info("Customer notices verified (%d seeds).", len(NOTICES))
