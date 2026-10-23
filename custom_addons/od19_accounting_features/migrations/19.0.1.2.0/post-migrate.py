"""Delete the retired advisory WHT Certificate reports.

The four payment-based WHT Certificate PDFs (PND1 / PND3 / PND53 /
PND53 Tris) were removed from the module data in favour of the
GL-accurate certificate printed from the OCA model
``withholding.tax.cert`` (module ``od19_thai_tax_reports``).

Odoo does not delete records when their XML data file disappears, so the
``ir.actions.report`` rows and their QWeb templates of an already updated
database would survive here and keep a broken *Print* entry that points at
a template that no longer exists. They are removed explicitly.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODULE = "od19_accounting_features"
#: Matches both the report actions (``action_report_wht_*``) and the QWeb
#: templates (``report_wht_*``) of the retired reports.
RETIRED_NAME_PATTERN = "%report_wht_%"


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    imd = env["ir.model.data"].sudo()
    stale = imd.search(
        [
            ("module", "=", MODULE),
            ("model", "in", ["ir.actions.report", "ir.ui.view"]),
            ("name", "like", RETIRED_NAME_PATTERN),
        ]
    )
    if not stale:
        _logger.info("%s: no retired WHT report record to delete", MODULE)
        return

    by_model = {}
    for data in stale:
        by_model.setdefault(data.model, []).append(data.res_id)
    removed = 0
    for model, res_ids in by_model.items():
        records = env[model].sudo().browse(res_ids).exists()
        removed += len(records)
        records.unlink()
    _logger.info("%s: deleted %s retired WHT report record(s)", MODULE, removed)
