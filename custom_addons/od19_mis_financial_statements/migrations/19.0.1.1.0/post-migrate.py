"""Refresh three Balance Sheet KPI expressions so the statement balances.

The MIS data of this module is declared with ``noupdate="True"`` (see
``data/mis_report_balance_sheet.xml``).  Odoo therefore does **not** rewrite
the stored ``mis.report.kpi`` expressions of an already installed database
when the module is updated with ``-u``.  This migration applies the corrected
expressions explicitly:

* ``bs_3300`` (กำไร/ขาดทุนสะสม) additionally picks up the *unallocated*
  balance (``balu``) of the ``equity_unaffected`` account (999999), which
  ``bale`` drops because that account has ``include_initial_balance = False``.
* ``bs_1110`` widens its code filter from ``111%.%`` to ``111%`` so the
  6-digit clearing accounts (111202 / 111204 / 111205) are included.
* ``bs_2130`` widens its code filter from ``213%.%`` to ``213%`` so the
  6-digit clearing account 213200 is included.

With these three expressions the balance sheet equation closes
(``bs_check = 0.00``).
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODULE = "od19_mis_financial_statements"

# xmlid (without module prefix) -> corrected expression
EXPRESSIONS = {
    "mis_kpi_bs_1110": "bale[('code','=like','111%')]",
    "mis_kpi_bs_2130": "-bale[('code','=like','213%')]",
    "mis_kpi_bs_3300": (
        "-bale[('code','=like','3300%.%')] "
        "- bale[('account_type','=','equity_unaffected')] "
        "- balu[('account_type','=','equity_unaffected')]"
    ),
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    for xmlid, expression in EXPRESSIONS.items():
        kpi = env.ref(f"{MODULE}.{xmlid}", raise_if_not_found=False)
        if not kpi:
            _logger.warning("%s: KPI %s not found, skipped", MODULE, xmlid)
            continue
        kpi.sudo().expression = expression
        _logger.info("%s: refreshed expression of %s", MODULE, xmlid)
