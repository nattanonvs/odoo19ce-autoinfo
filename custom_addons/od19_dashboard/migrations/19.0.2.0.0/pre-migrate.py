"""Back up the per-widget thresholds before the ORM drops their columns.

The widget model no longer declares ``threshold_mode``, ``warning_value`` and
``critical_value``, so updating the module deletes those columns. This script
runs *before* the schema is touched and copies the values into a temporary
table that ``post-migrate.py`` can still read: ``migrate(cr, version)`` never
receives an ``env``, so the ORM is not available at that point either.
"""

import logging

_logger = logging.getLogger(__name__)

BACKUP_TABLE = "od19_dashboard_threshold_backup"


def migrate(cr, version):
    if not version:
        return
    if not _has_legacy_column(cr):
        _logger.info(
            "od19_dashboard: no legacy threshold column found, nothing to back up"
        )
        return
    cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
    if cr.fetchone()[0]:
        _logger.info(
            "od19_dashboard: %s already exists, keeping its content", BACKUP_TABLE
        )
        return
    cr.execute(
        """
        CREATE TABLE od19_dashboard_threshold_backup (
            widget_id integer PRIMARY KEY,
            threshold_mode varchar,
            warning_value double precision,
            critical_value double precision
        )
        """
    )
    cr.execute(
        """
        INSERT INTO od19_dashboard_threshold_backup
             (widget_id, threshold_mode, warning_value, critical_value)
        SELECT id, threshold_mode, warning_value, critical_value
          FROM od19_dashboard_widget
         WHERE threshold_mode IS NOT NULL
           AND threshold_mode <> 'none'
        """
    )
    _logger.info("od19_dashboard: backed up %s widget thresholds", cr.rowcount)


def _has_legacy_column(cr):
    """Return True when the widget table still has the threshold column."""
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'od19_dashboard_widget'
           AND column_name = 'threshold_mode'
        """
    )
    return bool(cr.fetchone())
