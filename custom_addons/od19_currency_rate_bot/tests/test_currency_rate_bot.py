# Copyright 2026 Auto-Info
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

# ``requests`` is mocked, so the "cannot reach the Bank of Thailand API" trace
# written by the provider is the behaviour under test: keep it out of the log.
BOT_LOGGERS = (
    "odoo.addons.od19_currency_rate_bot.models.res_currency_rate_provider",
    "odoo.addons.currency_rate_update.models.res_currency_rate_provider",
)


@tagged("post_install", "-at_install")
class TestCurrencyRateBotOffline(TransactionCase):
    """The Bank of Thailand provider must degrade gracefully when offline.

    These tests guard the network error handling in
    ``ResCurrencyRateProviderBOT._obtain_rates``: a connection failure must
    surface as a readable ``UserError`` instead of a raw ``requests``
    traceback, and the scheduled update must not crash.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.sudo().write({"bot_token": "test-token"})

        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True

        cls.thb = cls.env.ref("base.THB")
        cls.thb.active = True
        cls.company.currency_id = cls.thb

        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("hostname_TH_BOT", "https://gateway.api.bot.or.th")
        ICP.set_param(
            "route_TH_BOT_exchange_daily",
            "/Stat-ExchangeRate/v2/DAILY_AVG_EXG_RATE",
        )

        Provider = cls.env["res.currency.rate.provider"]
        cls.provider = Provider.search(
            [("service", "=", "BOT"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        if cls.provider:
            cls.provider.currency_ids = [(6, 0, cls.usd.ids)]
        else:
            cls.provider = Provider.create(
                {
                    "service": "BOT",
                    "company_id": cls.company.id,
                    "currency_ids": [(6, 0, cls.usd.ids)],
                }
            )

    def _obtain(self):
        return self.provider._obtain_rates(
            "THB", ["USD"], date(2026, 1, 1), date(2026, 1, 2)
        )

    # ------------------------------------------------------------------
    # Network outage
    # ------------------------------------------------------------------
    @mute_logger(*BOT_LOGGERS)
    @patch("requests.get")
    def test_connection_error_raises_friendly_user_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("no network")
        with self.assertRaises(UserError) as cm:
            self._obtain()
        self.assertIn("Bank of Thailand API", str(cm.exception))

    @mute_logger(*BOT_LOGGERS)
    @patch("requests.get")
    def test_timeout_raises_friendly_user_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("timed out")
        with self.assertRaises(UserError) as cm:
            self._obtain()
        self.assertIn("Bank of Thailand API", str(cm.exception))

    @mute_logger(*BOT_LOGGERS)
    @patch("requests.get")
    def test_scheduled_update_does_not_crash_when_offline(self, mock_get):
        """The cron path swallows provider failures instead of raising."""
        mock_get.side_effect = requests.exceptions.ConnectionError("no network")
        self.provider._update(date(2026, 1, 1), date(2026, 1, 2), newest_only=True)
        mock_get.assert_called()

    # ------------------------------------------------------------------
    # Happy path (guards against the error handling swallowing success)
    # ------------------------------------------------------------------
    @patch("requests.get")
    def test_rates_returned_when_api_reachable(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            "result": {
                "data": {
                    "data_header": {"last_updated": "2026-01-02"},
                    "data_detail": [{"period": "2026-01-02", "mid_rate": "32.50"}],
                }
            }
        }
        mock_get.return_value = response
        content = self._obtain()
        self.assertEqual(list(content), ["2026-01-02"])
        self.assertAlmostEqual(content["2026-01-02"]["USD"], 1 / 32.50)
