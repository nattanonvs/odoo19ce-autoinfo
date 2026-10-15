# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# Copyright 2026 Auto-Info
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import datetime

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResCurrencyRateProviderBOT(models.Model):
    _inherit = "res.currency.rate.provider"

    service = fields.Selection(
        selection_add=[("BOT", "Bank of Thailand")],
        ondelete={"BOT": "set default"},
    )

    @api.depends("service")
    def _compute_available_currency_ids(self):
        res = super()._compute_available_currency_ids()
        Currency = self.env["res.currency"]
        for provider in self:
            if provider.service == "BOT":
                provider.available_currency_ids = Currency.search(
                    [("bot_currency_name", "in", provider._get_supported_currencies())]
                )
        return res

    def _schedule_last_successful_run(self, newest_date):
        """Keep the company's "last update" stamps in sync with the provider."""
        res = super()._schedule_last_successful_run(newest_date)
        for provider in self:
            provider.company_id.sudo().write(
                {
                    "autoinfo_currency_rate_last_update": fields.Datetime.now(),
                    "autoinfo_currency_rate_last_rate_date": newest_date,
                }
            )
        return res

    def _get_supported_currencies(self):
        self.ensure_one()
        if self.service != "BOT":
            return super()._get_supported_currencies()

        # List of currencies obtained from:
        # https://apigw1.bot.or.th/bot/public/Stat-ExchangeRate/v2
        return [
            "USD",
            "GBP",
            "EUR",
            "JPY",
            "HKD",
            "MYR",
            "SGD",
            "BND",
            "PHP",
            "IDR",
            "INR",
            "CHF",
            "AUD",
            "NZD",
            "CAD",
            "SEK",
            "DKK",
            "NOK",
            "CNY",
            "MXN",
            "ZAR",
            "KRW",
            "TWD",
            "KWD",
            "SAR",
            "AED",
            "MMK",
            "BDT",
            "CZK",
            "KHR",
            "KES",
            "LAK",
            "RUB",
            "VND",
            "EGP",
            "PLN",
            "LKR",
            "IQD",
            "BHD",
            "OMR",
            "JOD",
            "QAR",
            "MVR",
            "NPR",
            "PGK",
            "ILS",
            "HUF",
            "PKR",
        ]

    def _get_currency_unit(self, bot_currency_name):
        """Return the unit used by the BOT feed (e.g. JPY is quoted per 100)."""
        unit = 1.0
        if bot_currency_name == "JPY":
            unit = 100.0
        return unit

    def _update_content_currency_update(
        self, bot_currency, content, result, date_from, date_to
    ):
        data = result["data"]
        last_updated = data["data_header"]["last_updated"]
        date_last_update = datetime.datetime.strptime(last_updated, "%Y-%m-%d").date()
        if date_from > date_last_update and date_to > date_last_update:
            raise UserError(self.env._("BOT Last Updated: %s", last_updated))
        unit = self._get_currency_unit(bot_currency.bot_currency_name)
        for data_detail in data["data_detail"]:
            period = (
                fields.Date.to_string(fields.Date.from_string(data_detail["period"]))
                if data_detail["period"]
                else False
            )
            if not period:
                continue
            content.setdefault(period, {})[bot_currency.name] = unit / float(
                data_detail[bot_currency.bot_currency_rate_type]
            )

    def _obtain_rates(self, base_currency, currencies, date_from, date_to):
        self.ensure_one()
        if self.service != "BOT":
            return super()._obtain_rates(base_currency, currencies, date_from, date_to)

        if base_currency != "THB":
            raise UserError(
                self.env._(
                    "Bank of Thailand is suitable only for companies with THB as "
                    "base currency!"
                )
            )
        ICP = self.env["ir.config_parameter"].sudo()
        bot_token = self.company_id.bot_token
        if not bot_token:
            raise UserError(self.env._("No bot.or.th credentials specified!"))
        hostname = ICP.get_param("hostname_TH_BOT")
        route_bot = ICP.get_param("route_TH_BOT_exchange_daily")
        default_url = "{}{}/?start_period={}&end_period={}".format(
            hostname,
            route_bot,
            date_from.strftime("%Y-%m-%d"),
            date_to.strftime("%Y-%m-%d"),
        )
        headers = {
            "Authorization": bot_token,
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        bot_currencies = self.env["res.currency"].search(
            [("name", "in", currencies)]
        )
        content = {}
        for bot_currency in bot_currencies:
            url = f"{default_url}&currency={bot_currency.bot_currency_name}"
            response = requests.get(url, headers=headers, timeout=15)
            data_dict = response.json()
            result = data_dict.get("result", False)
            if not result:
                raise UserError(
                    self.env._(
                        "httpCode: %(code)s\nmoreInformation: %(info)s",
                        code=data_dict.get("httpCode", False),
                        info=data_dict.get("moreInformation", False),
                    )
                )
            self._update_content_currency_update(
                bot_currency, content, result, date_from, date_to
            )
        return content
