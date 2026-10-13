import datetime

from odoo import http
from odoo.http import request


class AutoInfoWebsite(http.Controller):
    """Controllers for the Auto-Info corporate website and employee portal."""

    @http.route(
        ["/employee-portal"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def employee_portal(self, **kwargs):
        """Employee portal homepage.

        Only authenticated internal users can access this page.
        """
        Announcement = request.env["announcement"]
        today = datetime.date.today()
        announcements = Announcement.sudo().search(
            [
                ("published", "=", True),
                "|",
                ("expiry_date", "=", False),
                ("expiry_date", ">=", today),
            ],
            limit=5,
            order="published_date desc, create_date desc",
        )
        return request.render(
            "od19_website.od19_employee_portal",
            {
                "user": request.env.user,
                "datetime": datetime,
                "announcements": announcements,
            },
        )
