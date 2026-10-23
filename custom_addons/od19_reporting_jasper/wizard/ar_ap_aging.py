# -*- coding: utf-8 -*-
"""R-AC-011 AR/AP Aging.

Second ported Jasper form, and the first one that is *not* bound to a single
document: the legacy wizard was opened from the Accounting reporting menu, so
it selects its scope (company, end date, accounts, partners) instead of
receiving ``active_ids``.

Odoo 19 adaptations applied to ``jrxml/ar_ap_aging_report.jrxml``:

* ``account_account_type`` was dropped after Odoo 15, so the
  ``aa.user_type_id -> account_account_type.type`` join is replaced by the
  ``account_account.account_type`` selection (``asset_receivable`` /
  ``liability_payable``).
* ``res_partner.customer`` / ``res_partner.supplier`` are replaced by
  ``customer_rank`` / ``supplier_rank``.
* The legacy code derived the Buddhist-era offset from ``date_format``, which
  only ever holds a format string, so BE was silently ignored; it now follows
  ``date_type``.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class ArApAgingReport(models.TransientModel):
    _name = "ar.ap.aging.report"
    _description = "AR/AP Aging Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="AR-AP Aging")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(
            __file__, base_name="ar_ap_aging_report"
        )
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    as_date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.context_today,
    )
    date_type = fields.Selection(
        [("AD", "AD"), ("BE", "BE")],
        string="Date Type",
        default="AD",
        required=True,
        help="AD = คริสตศักราช\nBE = พุทธศักราช",
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )
    p_Type = fields.Selection(
        [("ar", "Account Receivable"), ("ap", "Account Payable")],
        string="Account Type",
        default="ar",
        required=True,
    )
    p_Days = fields.Integer(string="Days of Range", required=True, default=30)
    p_Detail = fields.Boolean(string="Show Details")

    account_ids = fields.Many2many(
        "account.account",
        relation="od19_ar_ap_aging_report_account_rel",
        string="Account Code",
    )
    customer_ids = fields.Many2many(
        "res.partner",
        relation="od19_ar_ap_aging_report_customer_rel",
        string="Customer",
        domain=[("customer_rank", ">", 0)],
    )
    vendor_ids = fields.Many2many(
        "res.partner",
        relation="od19_ar_ap_aging_report_vendor_rel",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
    )

    def _legacy_date_text(self):
        """``p_DateText`` date part: ``23-10-2569`` (BE) / ``23-10-2026`` (AD)."""
        year_add = 543 if self.date_type == "BE" else 0
        return "{0:02d}-{1:02d}-{2:d}".format(
            self.as_date.day, self.as_date.month, self.as_date.year + year_add
        )

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        partner_ids = self.customer_ids if self.p_Type == "ar" else self.vendor_ids
        parameters = self.get_common_parameters()
        parameters.update(
            {
                "p_Days": str(self.p_Days),
                "p_Detail": str(self.p_Detail),
                "p_AccountCodeText": ", ".join(self.account_ids.mapped("code")),
                "p_DateText": "ณ วันที่ " + self._legacy_date_text(),
                "p_As_Date": str(self.as_date),
                "p_Type": self.p_Type,
                "p_Print_By": self._legacy_print_by(),
                "company_id": "%s" % self.company_id.id,
                "company_name": self.company_id.name,
                "account_ids": ("array%s" % self.account_ids.ids)
                if self.account_ids
                else "null",
                "partner_ids": ("array%s" % partner_ids.ids)
                if partner_ids
                else "null",
            }
        )
        return parameters
