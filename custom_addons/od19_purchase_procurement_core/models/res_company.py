# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_po_director_approval_threshold = fields.Monetary(
        string="Director Approval Threshold",
        currency_field="currency_id",
        default=100000.0,
        help="Purchase orders at or above this amount require approval from "
        "a Purchase Director. Below this amount, a Purchase Manager can "
        "approve.",
    )
