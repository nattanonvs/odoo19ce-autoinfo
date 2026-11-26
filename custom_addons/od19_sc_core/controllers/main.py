# -*- coding: utf-8 -*-
"""HTTP surface ของเอนจิน: inbound webhook + ส่ง CSS ธีมแบบไดนามิก"""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class Od19ScController(http.Controller):

    @http.route("/od19_sc/webhook/<int:endpoint_id>", type="jsonrpc", auth="public",
                methods=["POST"], csrf=False)
    def sc_webhook(self, endpoint_id, **kwargs):
        payload = request.get_json_data() or {}
        return request.env["od19.sc.integration.endpoint"].sudo()._webhook_receive(
            endpoint_id, payload)

    @http.route("/od19_sc/theme.css", type="http", auth="public", methods=["GET"], csrf=False)
    def sc_theme_css(self, **kwargs):
        templates = request.env["od19.sc.template"].sudo().search([("active", "=", True)])
        css = templates[:1]._build_theme_css() if templates else ":root {}"
        return request.make_response(css, headers=[
            ("Content-Type", "text/css; charset=utf-8"),
            ("Cache-Control", "no-cache"),
        ])
