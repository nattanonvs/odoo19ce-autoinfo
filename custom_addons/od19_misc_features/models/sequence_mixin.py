# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Override the date/sequence constraint of ``sequence.mixin``.

The base ``sequence.mixin`` enforces that the sequence number (e.g. an invoice
number) is aligned with the document date. This is problematic for the Thai
localization where the Buddhist Era year is used and documents may be
backdated, causing the year embedded in the sequence to mismatch the record
date.

This override disables the date/sequence validation entirely so that documents
can be posted with backdated dates without raising a ``ValidationError``.
"""

from odoo import models


class SequenceMixin(models.AbstractModel):
    _inherit = "sequence.mixin"

    def _constrains_date_sequence(self):
        # Intentionally skip the date/sequence validation.
        # Required for Thai localization (Buddhist Era year + backdating).
        return True
