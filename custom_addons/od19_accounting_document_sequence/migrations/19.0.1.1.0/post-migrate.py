"""Sync document sequences with the legacy Odoo 15 (``od15_stage``) settings.

``data/ir_sequence_data.xml`` is declared with ``noupdate="1"``: Odoo keeps
whatever is already stored in the database and never re-applies the file on a
module update. The sequences in that file were corrected to match the Odoo 15
configuration (``use_date_range`` + ``implementation``) so the numbering of the
migrated documents stays identical between the two systems. An explicit
post-migration is therefore required to push the new values onto databases
where the module is already installed.

Reference: the ``od15_stage`` ``ir.sequence`` dump.
- 49 of 54 sequences use a yearly date range.
- 26 financial documents are ``no_gap``.
- The five sequences without ``use_date_range`` (ADVR, ADVC, ASSC, ASLT, WC)
  intentionally match od15, which leaves them without a date range.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

MODULE = "od19_accounting_document_sequence"

#: xmlid -> (use_date_range, implementation) as configured in Odoo 15.
TARGETS = {
    # Billing & Prepayments
    "seq_billing_no": (True, "standard"),
    "seq_prepayment_no": (True, "no_gap"),
    # Cheque Book & Cash
    "seq_cheque_book": (True, "no_gap"),
    "seq_cash_in": (True, "standard"),
    "seq_cash_out": (True, "standard"),
    # Advances (od15 has no date range on these two)
    "seq_advance_request": (False, "standard"),
    "seq_advance_clear": (False, "standard"),
    # Petty Cash
    "seq_petty_cash_request": (True, "standard"),
    # Withholding Tax
    "seq_wht": (True, "no_gap"),
    "seq_wht1": (True, "no_gap"),
    "seq_wht2": (True, "no_gap"),
    "seq_wht3": (True, "no_gap"),
    "seq_wht53": (True, "no_gap"),
    # VAT
    "seq_vat_purchase": (True, "no_gap"),
    "seq_vat_sale": (True, "no_gap"),
    # Asset (od15 has no date range on these two)
    "seq_asset_stock_check": (False, "standard"),
    "seq_asset_location_transfer": (False, "standard"),
    # Bring Forward
    "seq_bring_forward": (True, "no_gap"),
    # Warranty (od15 has no date range)
    "seq_warranty_card": (False, "no_gap"),
    # Voucher sequences
    "seq_journal_misc": (True, "standard"),
    "seq_journal_voucher": (True, "standard"),
    "seq_voucher_expense": (True, "standard"),
    "seq_voucher_advance": (True, "no_gap"),
    "seq_voucher_advance_v": (True, "no_gap"),
    "seq_voucher_bf": (True, "no_gap"),
    "seq_voucher_cash": (True, "no_gap"),
    "seq_voucher_cbtv": (True, "no_gap"),
    "seq_voucher_customer_invoice": (True, "standard"),
    "seq_voucher_customer_payment": (True, "standard"),
    "seq_voucher_receipt": (True, "no_gap"),
    "seq_voucher_tax_invoice": (True, "no_gap"),
    "seq_voucher_exchange_diff": (True, "standard"),
    "seq_voucher_expense_journal": (True, "standard"),
    "seq_voucher_fixed_asset": (True, "standard"),
    "seq_voucher_inventory_valuation": (True, "standard"),
    # Bank vouchers
    "seq_kbank_ca_023": (True, "standard"),
    "seq_kbank_ca_609": (True, "standard"),
    "seq_kbank_fa_023": (True, "standard"),
    "seq_kbank_fa_609": (True, "standard"),
    "seq_kbank_sa_023": (True, "standard"),
    "seq_kbank_sa_609": (True, "standard"),
    "seq_scb_sa_140": (True, "no_gap"),
    "seq_uob_ca_797": (True, "no_gap"),
    "seq_uob_fa_797": (True, "no_gap"),
    "seq_uob_sa_797": (True, "no_gap"),
    # Journal vouchers
    "seq_voucher_payment_journal": (True, "standard"),
    "seq_voucher_petty_cash": (True, "standard"),
    "seq_voucher_petty_cash_v": (True, "standard"),
    "seq_voucher_purchases_journal": (True, "standard"),
    "seq_voucher_received_journal": (True, "standard"),
    "seq_voucher_sales_journal": (True, "no_gap"),
    "seq_voucher_vendor_bills": (True, "no_gap"),
    "seq_voucher_vendor_payment": (True, "no_gap"),
    "seq_voucher_cheque": (True, "no_gap"),
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    updated = 0
    missing = []
    for xmlid, (use_date_range, implementation) in TARGETS.items():
        seq = env.ref(f"{MODULE}.{xmlid}", raise_if_not_found=False)
        if not seq:
            missing.append(xmlid)
            continue
        vals = {}
        if seq.use_date_range != use_date_range:
            vals["use_date_range"] = use_date_range
        if seq.implementation != implementation:
            vals["implementation"] = implementation
        if vals:
            seq.write(vals)
            updated += 1
    if missing:
        _logger.warning(
            "%s: %s sequence xmlid(s) not found: %s",
            MODULE,
            len(missing),
            ", ".join(missing),
        )
    _logger.info(
        "%s: synced %s/%s sequences to od15 settings",
        MODULE,
        updated,
        len(TARGETS),
    )
