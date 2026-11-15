# Copyright 2026 TRAE
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

"""ทดสอบตัวช่วยของ P4 (hooks): _as_bool, _as_int, _resolve และตัวกรอง schema."""

import logging
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.od19_system_monitor import hooks


@tagged("post_install", "-at_install")
class TestHealthHooks(TransactionCase):
    """ทดสอบฟังก์ชันช่วยที่ทำงานตอนโหลดโมดูล (ไม่แตะไฟล์ log จริง)."""

    # ------------------------- _as_bool -------------------------
    def test_as_bool_truthy_values(self):
        for value in ("1", "true", "TRUE", "yes", "on", " Yes "):
            self.assertTrue(hooks._as_bool(value))

    def test_as_bool_falsy_values(self):
        for value in ("0", "false", "no", "off", ""):
            self.assertFalse(hooks._as_bool(value))

    def test_as_bool_none_uses_default(self):
        self.assertTrue(hooks._as_bool(None, True))
        self.assertFalse(hooks._as_bool(None, False))

    # ------------------------- _as_int -------------------------
    def test_as_int_parses_or_defaults(self):
        self.assertEqual(hooks._as_int("42", 0), 42)
        self.assertEqual(hooks._as_int(7, 0), 7)
        self.assertEqual(hooks._as_int("abc", 5), 5)
        self.assertEqual(hooks._as_int(None, 5), 5)

    # ------------------------- _resolve -------------------------
    def test_resolve_prefers_db_param(self):
        with patch.object(hooks, "_db_param", return_value="from-db"):
            self.assertEqual(hooks._resolve("some.key", "default"), "from-db")

    def test_resolve_falls_back_to_conf(self):
        with patch.object(hooks, "_db_param", return_value=None), patch.object(
            hooks.tools.config, "get", return_value="from-conf"
        ):
            self.assertEqual(hooks._resolve("some.key", "default"), "from-conf")

    def test_resolve_falls_back_to_default(self):
        with patch.object(hooks, "_db_param", return_value=None), patch.object(
            hooks.tools.config, "get", return_value=None
        ):
            self.assertEqual(hooks._resolve("some.key", "default"), "default")

    # ------------------------- ตัวกรอง schema -------------------------
    def test_schema_noise_filter_blocks_known_warning(self):
        record = logging.LogRecord(
            "odoo.schema",
            logging.WARNING,
            __file__,
            1,
            "Missing not-null constraint on x",
            None,
            None,
        )
        self.assertFalse(hooks._SchemaNoiseFilter().filter(record))

    def test_schema_noise_filter_allows_other_warnings(self):
        record = logging.LogRecord(
            "odoo.schema",
            logging.WARNING,
            __file__,
            1,
            "Table x created",
            None,
            None,
        )
        self.assertTrue(hooks._SchemaNoiseFilter().filter(record))
