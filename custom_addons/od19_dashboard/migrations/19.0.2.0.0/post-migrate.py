"""Turn the backed up thresholds into status rows.

Runs after the schema upgrade: the widget columns are gone, the rule table and
the new widget columns exist, and the temporary table filled by
``pre-migrate.py`` is the only remaining source of truth.
"""

import logging

_logger = logging.getLogger(__name__)

BACKUP_TABLE = "od19_dashboard_threshold_backup"

#: One row per rule to create: ``(threshold_mode, operator, sequence, status,
#: column, label)``. ``higher_is_better`` alerts when the value falls *below*
#: the bound, ``lower_is_better`` when it climbs *above* it; in both cases the
#: critical (red) rule must be evaluated before the warning (yellow) one so the
#: first-match-wins engine reproduces the retired ``_compute_status()``.
RULE_SPECS = [
    ("higher_is_better", "<=", 10, "red", "critical_value", "Migrated critical value"),
    ("higher_is_better", "<=", 20, "yellow", "warning_value", "Migrated warning value"),
    ("lower_is_better", ">=", 10, "red", "critical_value", "Migrated critical value"),
    ("lower_is_better", ">=", 20, "yellow", "warning_value", "Migrated warning value"),
]


def migrate(cr, version):
    if not version:
        return
    _convert_thresholds(cr)
    _set_widget_defaults(cr)


def _convert_thresholds(cr):
    """Insert the status rules of every widget that had a threshold."""
    cr.execute("SELECT to_regclass(%s)", (BACKUP_TABLE,))
    if not cr.fetchone()[0]:
        _logger.info(
            "od19_dashboard: no threshold backup table, nothing to convert"
        )
        return
    for mode, operator, sequence, status, column, label in RULE_SPECS:
        # ``column`` comes from the constant list above, never from user input.
        cr.execute(
            """
            INSERT INTO od19_dashboard_widget_rule
                 (widget_id, sequence, name, active, operator, compare_type,
                  compare_value, compare_percent, compare_widget_id, status)
            SELECT backup.widget_id, %s, %s, true, %s, 'constant',
                   COALESCE(backup.{column}, 0.0), 0.0, NULL, %s
              FROM od19_dashboard_threshold_backup AS backup
             WHERE backup.threshold_mode = %s
            """.format(column=column),
            (sequence, label, operator, status, mode),
        )
        _logger.info(
            "od19_dashboard: created %s '%s' rules for '%s' widgets",
            cr.rowcount,
            status,
            mode,
        )
    cr.execute("DROP TABLE %s" % BACKUP_TABLE)


def _set_widget_defaults(cr):
    """Give the new columns of the existing widgets their documented default.

    The ORM fills them from the field defaults while adding the columns, but
    the update does not run on a database where the fields already existed, so
    the values are set explicitly to keep the result deterministic.
    """
    cr.execute(
        """
        UPDATE od19_dashboard_widget
           SET formula_mode   = COALESCE(formula_mode, 'measure'),
               formula_slots  = COALESCE(formula_slots, '{}'),
               formula_basis  = COALESCE(formula_basis, 'previous'),
               delta_basis    = COALESCE(delta_basis, 'previous'),
               default_status = COALESCE(default_status, 'green')
        """
    )
