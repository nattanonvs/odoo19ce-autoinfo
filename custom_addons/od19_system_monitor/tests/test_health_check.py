# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

import os
import shutil
import tempfile

from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger

PARAM_ENABLED = "od19_health.enabled"
PARAM_RETENTION = "od19_health.retention_days"


@tagged("post_install", "-at_install")
class TestHealthCheck(TransactionCase):
    """ทดสอบนิยามการตรวจ (check): ข้อจำกัด การวัด และการรัน."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ปิดการตรวจชุดเริ่มต้นเพื่อให้ผลลัพธ์ในแต่ละเทสต์แน่นอน
        cls.env["od19.health.check"].search([]).write({"active": False})

    def _make_check(self, code, **kwargs):
        vals = {"name": code, "code": code, "check_type": "custom"}
        vals.update(kwargs)
        return self.env["od19.health.check"].create(vals)

    # ------------------------- ข้อจำกัด -------------------------
    def test_unique_code_constraint(self):
        self._make_check("unique_check_code")
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self._make_check("unique_check_code")
            self.env.flush_all()

    # ------------------------- เกณฑ์สถานะ -------------------------
    def test_threshold_state(self):
        check = self._make_check(
            "threshold_check", warning_threshold=10, critical_threshold=20
        )
        self.assertEqual(check._threshold_state(5), "ok")
        self.assertEqual(check._threshold_state(10), "warning")
        self.assertEqual(check._threshold_state(25), "critical")

    def test_state_from_threshold(self):
        check = self._make_check(
            "state_from_threshold", warning_threshold=10, critical_threshold=20
        )
        measure = check._state_from_threshold(15, "15", "ข้อความ")
        self.assertEqual(measure["state"], "warning")
        self.assertEqual(measure["value_label"], "15")
        forced = check._state_from_threshold(
            0, "-", "ไม่ทราบ", status="unknown", force_state="unknown"
        )
        self.assertEqual(forced["state"], "unknown")

    # ------------------------- การวัด -------------------------
    def test_measure_custom(self):
        check = self._make_check("custom_measure")
        measure = check._measure()
        self.assertEqual(measure["status"], "reported")
        self.assertEqual(measure["state"], "unknown")

    def test_dir_size_missing_path(self):
        Check = self.env["od19.health.check"]
        self.assertEqual(Check._dir_size(""), (0, 0))
        self.assertEqual(Check._dir_size("C:/definitely/not/here/od19"), (0, 0))

    def test_dir_size_counts_files(self):
        path = tempfile.mkdtemp()
        try:
            with open(os.path.join(path, "a.txt"), "w", encoding="utf-8") as handle:
                handle.write("hello")
            size, count = self.env["od19.health.check"]._dir_size(path)
            self.assertEqual(count, 1)
            self.assertEqual(size, 5)
        finally:
            shutil.rmtree(path, ignore_errors=True)

    # ------------------------- การรัน -------------------------
    def test_process_creates_result_and_updates_last(self):
        check = self._make_check("process_check")
        outcome = check._process()
        self.assertEqual(outcome["check"], "process_check")
        self.assertTrue(check.last_run)
        self.assertEqual(check.last_state, "unknown")
        self.assertEqual(len(check.result_ids), 1)
        self.assertEqual(check.result_ids[0].state, "unknown")

    def test_action_run_now(self):
        check = self._make_check("run_now_check")
        self.assertTrue(check.action_run_now())
        self.assertEqual(len(check.result_ids), 1)
        self.assertTrue(check.last_run)

    def test_action_view_results(self):
        check = self._make_check("view_results_check")
        action = check.action_view_results()
        self.assertEqual(action["res_model"], "od19.health.result")
        self.assertIn(("check_id", "=", check.id), action["domain"])

    # ------------------------- cron / ภาพรวม -------------------------
    def test_overall_state_unknown_without_runs(self):
        self.assertEqual(self.env["od19.health.check"]._overall_state(), "unknown")

    def test_overall_state_worst(self):
        now = fields.Datetime.now()
        ok = self._make_check("overall_ok")
        warn = self._make_check("overall_warning")
        ok.write({"last_run": now, "last_state": "ok"})
        warn.write({"last_run": now, "last_state": "warning"})
        self.assertEqual(self.env["od19.health.check"]._overall_state(), "warning")
        crit = self._make_check("overall_critical")
        crit.write({"last_run": now, "last_state": "critical"})
        self.assertEqual(self.env["od19.health.check"]._overall_state(), "critical")

    def test_monitor_enabled_toggle(self):
        params = self.env["ir.config_parameter"].sudo()
        params.set_param(PARAM_ENABLED, "False")
        self.assertFalse(self.env["od19.health.check"]._monitor_enabled())
        params.set_param(PARAM_ENABLED, "True")
        self.assertTrue(self.env["od19.health.check"]._monitor_enabled())

    def test_cron_run_checks_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_ENABLED, "False")
        self._make_check("cron_disabled_check")
        self.env["od19.health.check"]._cron_run_checks()
        self.assertEqual(self.env["od19.health.result"].search_count([]), 0)

    def test_cron_run_checks_enabled(self):
        self.env["ir.config_parameter"].sudo().set_param(PARAM_ENABLED, "True")
        check = self._make_check("cron_enabled_check")
        self.env["od19.health.check"]._cron_run_checks()
        self.assertEqual(
            self.env["od19.health.result"].search_count([("check_id", "=", check.id)]),
            1,
        )
