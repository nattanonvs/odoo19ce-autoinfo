# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# Copyright 2026 Auto-Info
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import datetime

import pytz

from odoo import api, fields, models

CURRENCY_RATE_TYPE = [
    ("mid_rate", "Mid Rate"),
    ("selling", "Selling Rate"),
    ("buying_sight", "Buying Sight Rate"),
    ("buying_transfer", "Buying Transfer Rate"),
]


class ResCurrency(models.Model):
    _inherit = "res.currency"

    bot_currency_name = fields.Char(
        string="BOT Currency",
        size=3,
        compute="_compute_bot_currency_name",
        readonly=False,
        store=True,
        required=True,
    )
    bot_currency_rate_type = fields.Selection(
        string="BOT Currency Rate Type",
        selection=CURRENCY_RATE_TYPE,
        default="mid_rate",
        required=True,
        index=True,
    )

    @api.depends("name")
    def _compute_bot_currency_name(self):
        for currency in self:
            currency.bot_currency_name = currency.name or "-"

    def _get_rates(self, company, date):
        """Smart Date Fallback.

        The Bank of Thailand publishes the daily average exchange rate at
        18:00 (Asia/Bangkok). Before that hour, "today's" rate does not exist
        yet, so fall back to the previous day to avoid a misleading 1:1 rate.
        """
        date_value = fields.Date.to_date(date)
        now_local = datetime.datetime.now(pytz.timezone("Asia/Bangkok"))
        if (
            date_value
            and date_value == now_local.date()
            and now_local.time() < datetime.time(18, 0, 0)
        ):
            date_value = date_value - datetime.timedelta(days=1)
        return super()._get_rates(company, date_value)
