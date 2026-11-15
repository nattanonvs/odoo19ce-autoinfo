# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

PARAM_RETENTION = "od19_health.retention_days"


@tagged("post_install", "-at_install")
class TestHealthResult(TransactionCase):
    """ทดสอบอนุกรมเวลาของผลการตรวจและการลบตามนโยบาย retention."""

    def setUp(self):
        super().setUp()
        self.check = self.env["od19.health.check"].create(
            {"name": "Result Check", "code": "result_test_check", "check_type": "custom"}
        )

    def _make_result(self, run_at, value=1.0):
        return self.env["od19.health.result"].create(
            {
                "check_id": self.check.id,
                "run_at": run_at,
                "value": value,
                "state": "ok",
            }
        )

    def test_cutoff_none_when_zero(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_RETENTION, "0")
        self.assertIsNone(self.env["od19.health.result"]._cutoff())

    def test_cutoff_datetime_when_positive(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_RETENTION, "30")
        cutoff = self.env["od19.health.result"]._cutoff()
        self.assertTrue(cutoff)
        expected = fields.Datetime.now() - timedelta(days=30)
        self.assertLess(abs((cutoff - expected).total_seconds()), 60)

    def test_cron_prune_removes_old(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_RETENTION, "30")
        old = self._make_result(fields.Datetime.now() - timedelta(days=40))
        fresh = self._make_result(fields.Datetime.now())
        removed = self.env["od19.health.result"]._cron_prune()
        self.assertEqual(removed, 1)
        self.assertFalse(old.exists())
        self.assertTrue(fresh.exists())

    def test_cron_prune_keeps_all_when_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_RETENTION, "0")
        self._make_result(fields.Datetime.now() - timedelta(days=400))
        self.assertEqual(self.env["od19.health.result"]._cron_prune(), 0)
