# -*- coding: utf-8 -*-
import os

from odoo import http
from odoo.http import request

GUIDE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static', 'src', 'guide', 'index.html',
)


class Od19UserGuideManual(http.Controller):
    """Serve the assembled handbook to any authenticated internal user."""

    @http.route('/od19/guide', type='http', auth='user', website=False, sitemap=False)
    def guide(self, **kw):
        if not os.path.exists(GUIDE_FILE):
            return request.not_found()
        with open(GUIDE_FILE, 'rb') as fh:
            content = fh.read()
        return request.make_response(
            content,
            headers=[('Content-Type', 'text/html; charset=utf-8')],
        )
