# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบการพยากรณ์ความจุ (P5): _forecast, _state, _fill และ create."""

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged

MB = 1024 ** 2
GB = 1024 ** 3


@tagged("post_install", "-at_install")
class TestHealthCapacity(TransactionCase):
    """ทดสอบการประมาณอัตราเติบโตของฐานข้อมูลและ filestore."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Check = cls.env["od19.health.check"]
        cls.db_check = Check.search([("code", "=", "db_size")], limit=1)
        if not cls.db_check:
            cls.db_check = Check.create(
                {"name": "DB Size", "code": "db_size", "check_type": "db_size"}
            )
        cls.db_check.write({"active": True})
        cls.fs_check = Check.search([("code", "=", "filestore_size")], limit=1)
        Result = cls.env["od19.health.result"]
        # ล้างผลเดิมเพื่อให้การคำนวณแน่นอน
        Result.search(
            [("check_id", "in", (cls.db_check | cls.fs_check).ids)]
        ).unlink()
        if cls.fs_check:
            cls.fs_check.write({"last_value": 0})
        cls.base = fields.Datetime.now() - timedelta(days=7)
        Result.create(
            {
                "check_id": cls.db_check.id,
                "run_at": cls.base,
                "state": "ok",
                "value": 1000,
            }
        )
        Result.create(
            {
                "check_id": cls.db_check.id,
                "run_at": cls.base + timedelta(days=7),
                "state": "ok",
                "value": 2000,
            }
        )
        cls.db_check.write({"last_value": 2000})

    # ------------------------- _forecast -------------------------
    def test_forecast_computes_rate(self):
        Wizard = self.env["od19.health.capacity.wizard"]
        data = Wizard._forecast("db_size", 30)
        self.assertEqual(data["current"], 2000)
        self.assertAlmostEqual(data["per_day"], 1000 / 7.0, places=3)
        self.assertEqual(data["span_days"], 7)
        self.assertAlmostEqual(
            data["forecast"], 2000 + (1000 / 7.0) * 30, places=2
        )

    def test_forecast_missing_check_is_empty(self):
        Wizard = self.env["od19.health.capacity.wizard"]
        data = Wizard._forecast("no_such_code", 30)
        self.assertEqual(data["current"], 0.0)
        self.assertEqual(data["per_day"], 0.0)
        self.assertEqual(data["span_days"], 0)

    # ------------------------- _state -------------------------
    def test_state_thresholds(self):
        Wizard = self.env["od19.health.capacity.wizard"]
        zero = {"current": 0.0, "per_day": 0.0, "forecast": 0.0, "span_days": 0}
        self.assertEqual(Wizard._state(zero, zero), "ok")
        warn = dict(zero, per_day=600 * MB)
        self.assertEqual(Wizard._state(warn, zero), "warning")
        crit = dict(zero, per_day=2 * GB)
        self.assertEqual(Wizard._state(crit, zero), "critical")

    # ------------------------- create / action -------------------------
    def test_create_autofills_forecast(self):
        wizard = self.env["od19.health.capacity.wizard"].create(
            {"forecast_days": 30}
        )
        self.assertEqual(wizard.db_current, 2000)
        self.assertTrue(wizard.db_current_label)
        self.assertTrue(wizard.summary)
        self.assertEqual(wizard.sample_days, 7)

    def test_action_compute_returns_action(self):
        wizard = self.env["od19.health.capacity.wizard"].create(
            {"forecast_days": 10}
        )
        action = wizard.action_compute()
        self.assertEqual(action["res_model"], "od19.health.capacity.wizard")
        self.assertEqual(action["target"], "new")
