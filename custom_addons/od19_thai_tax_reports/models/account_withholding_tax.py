# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountWithholdingTax(models.Model):
    """Add the ภ.ง.ด.54 income tax form to the OCA withholding tax types.

    OCA ``l10n_th_account_tax`` offers pnd1/pnd2/pnd3/pnd3a/pnd53 only. The
    ภ.ง.ด.54 return (มาตรา 3 เตรส) covers the same 40(5)-40(8) income as
    ภ.ง.ด.53 but is filed by government agencies, state enterprises,
    associations and foundations, so it needs its own flag on the type.
    """

    _inherit = "account.withholding.tax"

    income_tax_form = fields.Selection(
        selection_add=[("pnd54", "PND54")],
        ondelete={"pnd54": "set null"},
    )
