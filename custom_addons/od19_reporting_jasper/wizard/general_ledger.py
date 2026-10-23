# -*- coding: utf-8 -*-
"""General Ledger (รายงานบัญชีแยกประเภท).

Third ported Jasper form.  Like AR/AP Aging it is not bound to a single
document: the legacy wizard was opened from the Accounting reporting menu and
selects its own scope (company, date range, accounts, journals, analytic
accounts).

Odoo 19 adaptations applied to ``jrxml/general_ledger.jrxml``:

* ``account_account`` no longer stores ``code`` / ``name`` as plain columns:
  the code is read from the company-aware ``code_store`` jsonb and the label
  from the translated ``name`` jsonb.
* ``account_move.voucher_running_no`` was a legacy ``dtr_journal_entry`` field
  with no Odoo 19 equivalent, so the "เลขที่ Voucher" column is intentionally
  left empty.
* ``account_move_line.analytic_account_id`` is replaced by the
  ``analytic_distribution`` jsonb, so the analytic filter tests the keys.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class GeneralLedgerReport(models.TransientModel):
    _name = "general.ledger.report"
    _description = "General Ledger Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="General Ledger")
    jasper_file = fields.Char(default=lambda self: self.get_jasper_file(__file__))
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    p_From_Date = fields.Date(
        string="From Date", required=True, default=fields.Date.context_today
    )
    p_To_Date = fields.Date(
        string="To Date", required=True, default=fields.Date.context_today
    )
    date_format = fields.Selection(
        [(value, value) for value in DATE_FORMATS],
        string="Date Format",
        default="dd-MM-yyyy",
        required=True,
    )
    locale = fields.Selection(
        [("th_TH", "พ.ศ."), ("en_EN", "ค.ศ.")],
        string="Calendars Year",
        default="th_TH",
        required=True,
    )
    p_State = fields.Selection(
        [("all_posted_entries", "เฉพาะที่ผ่านรายการแล้ว"), ("all_entries", "ทั้งหมด")],
        string="Target Moves",
        default="all_posted_entries",
        required=True,
    )
    p_Sort = fields.Selection(
        [("account", "Account Code"), ("date", "Date")],
        string="Sorting",
        default="account",
        required=True,
    )

    account_ids = fields.Many2many(
        "account.account",
        relation="od19_general_ledger_report_account_rel",
        string="Account Code",
    )
    journal_ids = fields.Many2many(
        "account.journal",
        relation="od19_general_ledger_report_journal_rel",
        string="Journal Name",
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        relation="od19_general_ledger_report_analytic_rel",
        string="Analytic Accounts",
    )

    def get_locale(self):
        return self.locale

    def _legacy_date_text(self, value):
        """``dd-mm-yyyy`` text with the Buddhist-era offset on ``th_TH``."""
        year_add = 543 if self.locale == "th_TH" else 0
        return "{0:02d}-{1:02d}-{2:d}".format(
            value.day, value.month, value.year + year_add
        )

    def _legacy_where(self):
        """Extra SQL predicate appended to the report query."""
        p_where = ""
        if self.account_ids:
            p_where += " and aml.account_id in (%s)" % ", ".join(
                str(i) for i in self.account_ids.ids
            )
        if self.journal_ids:
            p_where += " and am.journal_id in (%s)" % ", ".join(
                str(i) for i in self.journal_ids.ids
            )
        if self.analytic_account_ids:
            keys = ", ".join("'%s'" % i for i in self.analytic_account_ids.ids)
            p_where += " and aml.analytic_distribution ?| array[%s]" % keys
        if self.p_State == "all_posted_entries":
            p_where += " and am.state = 'posted'"
        return p_where

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        account_code = "aa.code_store->>(am.company_id::text)"
        if self.p_Sort == "account":
            p_sort = " order by %s, aml.date" % account_code
            p_sorting_text = "รหัสบัญชี"
        else:
            p_sort = " order by aml.date, %s" % account_code
            p_sorting_text = "วันที่"
        return {
            "p_Sort": p_sort,
            "p_SortingText": p_sorting_text,
            "p_State": "เฉพาะที่ผ่านรายการแล้ว"
            if self.p_State == "all_posted_entries"
            else "ทั้งหมด",
            "p_Where": "%s and aml.company_id = %s"
            % (self._legacy_where(), self.company_id.id),
            "p_AccountCodeText": ", ".join(self.account_ids.mapped("code"))
            or "ทั้งหมด",
            "p_JournalText": ", ".join(self.journal_ids.mapped("code")) or "ทั้งหมด",
            "p_AnalyticAccountText": ", ".join(self.analytic_account_ids.mapped("name"))
            or "ทั้งหมด",
            "p_DateFormat": str(self.date_format),
            "p_From_Date": str(self.p_From_Date),
            "p_To_Date": str(self.p_To_Date),
            "p_From_Date_Text": self._legacy_date_text(self.p_From_Date),
            "p_To_Date_Text": self._legacy_date_text(self.p_To_Date),
            "p_Print_By": self._legacy_print_by(),
        }
