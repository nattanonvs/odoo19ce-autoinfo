# -*- coding: utf-8 -*-
import runpy
from pathlib import Path

from odoo.tests.common import TransactionCase

MIGRATION_VERSION = "19.0.2.0.0"
MIGRATION_DIR = Path(__file__).resolve().parents[1] / "migrations" / MIGRATION_VERSION
BACKUP_TABLE = "od19_dashboard_threshold_backup"


def _load_migration(filename):
    """Return the ``migrate`` function of a migration script.

    ``migrations/19.0.2.0.0`` is not a valid Python package name (Odoo locates
    the folder by version string), so the script is executed straight from its
    path instead of being imported.
    """
    return runpy.run_path(str(MIGRATION_DIR / filename))["migrate"]


class TestDashboardThresholdMigration(TransactionCase):
    """The retired thresholds must come back as equivalent status rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env["od19.dashboard"].create({"name": "Migration dashboard"})
        cls.source = cls.env.ref("od19_dashboard.source_sale_order")
        cls.widget_model = cls.env["od19.dashboard.widget"]
        cls.pre_migrate = staticmethod(_load_migration("pre-migrate.py"))
        cls.post_migrate = staticmethod(_load_migration("post-migrate.py"))
        cls.installed_version = "19.0.1.0.0"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _legacy_status(self, value, mode, warning_value, critical_value):
        """Verbatim copy of the ``_compute_status()`` removed in Task 7.

        Kept in the test on purpose: the method no longer exists in the module,
        so this copy is the only reference for the migration equivalence check.
        """
        if value is None or mode == "none":
            return "green" if value is not None else "grey"
        if mode == "higher_is_better":
            if value <= critical_value:
                return "red"
            if value <= warning_value:
                return "yellow"
            return "green"
        if value >= critical_value:
            return "red"
        if value >= warning_value:
            return "yellow"
        return "green"

    def _add_legacy_columns(self):
        """Recreate the columns dropped by the module update (test only).

        The dev database has already been upgraded by Task 7, so the legacy
        columns have to be put back before the backup script can read them.
        """
        self.env.cr.execute(
            """
            ALTER TABLE od19_dashboard_widget
                ADD COLUMN IF NOT EXISTS threshold_mode varchar,
                ADD COLUMN IF NOT EXISTS warning_value double precision,
                ADD COLUMN IF NOT EXISTS critical_value double precision
            """
        )

    def _drop_legacy_columns(self):
        """Do what the module update does: remove the legacy columns."""
        self.env.cr.execute(
            """
            ALTER TABLE od19_dashboard_widget
               DROP COLUMN IF EXISTS threshold_mode,
               DROP COLUMN IF EXISTS warning_value,
               DROP COLUMN IF EXISTS critical_value
            """
        )

    def _legacy_widget(self, mode, warning_value, critical_value):
        """Create a widget holding the values of a pre-upgrade row.

        The threshold columns are only reachable through raw SQL. ``formula_slots``
        is cleared on purpose as well: it is the only new column that is nullable,
        so it is the only default ``post-migrate.py`` can really repair, and
        keeping the ORM value would leave that part of the script untested.
        """
        widget = self.widget_model.create(
            {
                "dashboard_id": self.dashboard.id,
                "name": "Legacy %s widget" % mode,
                "source_id": self.source.id,
                "measure_key": "__count",
            }
        )
        self.env.cr.execute(
            """
            UPDATE od19_dashboard_widget
               SET threshold_mode = %s, warning_value = %s, critical_value = %s,
                   formula_slots = NULL
             WHERE id = %s
            """,
            (mode, warning_value, critical_value, widget.id),
        )
        return widget

    def _run_migration(self):
        """Replay the real upgrade order on the current transaction."""
        self.pre_migrate(self.env.cr, self.installed_version)
        # The schema is upgraded between the two scripts: the columns are gone
        # by the time ``post-migrate`` runs, only the backup table survives.
        self._drop_legacy_columns()
        self.post_migrate(self.env.cr, self.installed_version)
        self.env.invalidate_all()

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_thresholds_become_equivalent_rules(self):
        cases = {
            "higher_is_better": (80.0, 50.0),
            "lower_is_better": (5.0, 10.0),
        }
        self._add_legacy_columns()
        widgets = {
            mode: self._legacy_widget(mode, warning, critical)
            for mode, (warning, critical) in cases.items()
        }

        self._run_migration()

        for mode, (warning_value, critical_value) in cases.items():
            widget = widgets[mode]
            rules = widget.rule_ids.sorted("sequence")
            expected_operator = "<=" if mode == "higher_is_better" else ">="
            self.assertEqual([rule.status for rule in rules], ["red", "yellow"])
            self.assertEqual([rule.operator for rule in rules], [expected_operator] * 2)
            self.assertEqual([rule.compare_type for rule in rules], ["constant"] * 2)
            self.assertEqual(
                [rule.compare_value for rule in rules], [critical_value, warning_value]
            )
            self.assertTrue(all(rule.active for rule in rules))
            # ``formula_mode``, ``formula_basis``, ``delta_basis`` and
            # ``default_status`` are NOT NULL, so the ORM already filled them
            # while adding the columns; ``formula_slots`` is nullable and is the
            # only default ``_set_widget_defaults()`` genuinely has to repair.
            self.assertEqual(widget.default_status, "green")
            self.assertEqual(widget.formula_mode, "measure")
            self.assertEqual(widget.formula_basis, "previous")
            self.assertEqual(widget.delta_basis, "previous")
            self.assertEqual(widget.formula_slots, "{}")

            # The value list has to reach every band of every mode: 7.0 sits
            # inside the yellow band of ``lower_is_better`` (5 <= value < 10) and
            # 10.0 is on its critical boundary, neither of which a list shared by
            # both modes would otherwise hit.
            for value in (-10.0, 0.0, 7.0, 10.0, 49.0, 50.0, 79.0, 80.0, 100.0):
                context = {"value": value, "goal": 0.0, "widget_values": {}, "shifts": {}}
                self.assertEqual(
                    widget._evaluate_rules(context)[0],
                    self._legacy_status(value, mode, warning_value, critical_value),
                    "Status differs for %s at value %s" % (mode, value),
                )

    def test_widgets_without_threshold_get_no_rule(self):
        self._add_legacy_columns()
        widget = self._legacy_widget("none", 0.0, 0.0)

        self._run_migration()

        self.assertFalse(widget.rule_ids)
        self.assertEqual(widget.default_status, "green")
        context = {"value": 42.0, "goal": 0.0, "widget_values": {}, "shifts": {}}
        self.assertEqual(widget._evaluate_rules(context), ("green", "default", ""))

    def test_backup_table_is_dropped(self):
        self._add_legacy_columns()
        self._legacy_widget("higher_is_better", 80.0, 50.0)

        self._run_migration()

        self.env.cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
        self.assertIsNone(self.env.cr.fetchone()[0])

    def test_migration_is_idempotent(self):
        self._add_legacy_columns()
        widget = self._legacy_widget("higher_is_better", 80.0, 50.0)

        # The backup runs twice while the legacy column is still present: the
        # second call has to keep the table it finds instead of failing on
        # ``CREATE TABLE`` or storing the rows twice.
        self.pre_migrate(self.env.cr, self.installed_version)
        self.pre_migrate(self.env.cr, self.installed_version)
        self.env.cr.execute("SELECT count(*) FROM %s" % BACKUP_TABLE)
        self.assertEqual(self.env.cr.fetchone()[0], 1)

        self._drop_legacy_columns()
        self.post_migrate(self.env.cr, self.installed_version)
        # A second conversion pass has no backup table left to read, so it must
        # not duplicate the rules.
        self.post_migrate(self.env.cr, self.installed_version)
        self.env.invalidate_all()

        self.assertEqual(len(widget.rule_ids), 2)
        self.env.cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
        self.assertIsNone(self.env.cr.fetchone()[0])
