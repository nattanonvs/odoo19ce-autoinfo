# -*- coding: utf-8 -*-
"""Trial Balance (งบทดลอง).

Fourth ported Jasper form.  Like AR/AP Aging and General Ledger it is not bound
to a single document: the legacy wizard was opened from the Accounting
reporting menu and selects its own scope (company, date range, target moves,
journals, analytic accounts).

Odoo 19 adaptations applied to ``jrxml/trial_balance_report.jrxml``:

* ``account_account`` no longer stores ``code`` / ``name`` as plain columns:
  the code is read from the company-aware ``code_store`` jsonb and the label
  from the translated ``name`` jsonb.
* ``account_account_type`` was dropped after Odoo 15, so the
  ``aa.user_type_id -> account_account_type.name`` join is replaced by the
  ``account_account.account_type`` selection.
* The legacy year-end adjustment (``account_move.is_year_end`` and the
  ``dtr_year_end`` table) has no Odoo 19 equivalent, so the balance brought
  forward is simply every posted entry dated before the start date.
* ``account_move_line.analytic_account_id`` is replaced by the
  ``analytic_distribution`` jsonb, so the analytic filter tests the keys.
"""
from odoo import fields, models

from .invoice_form import DATE_FORMATS


class TrialBalanceReport(models.TransientModel):
    _name = "trial.balance.report"
    _description = "Trial Balance Report"
    _inherit = "od19.jasper.report"

    name = fields.Char(default="Trial Balance")
    jasper_file = fields.Char(
        default=lambda self: self.get_jasper_file(
            __file__, base_name="trial_balance_report"
        )
    )
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
    p_State = fields.Selection(
        [("all_posted_entries", "เฉพาะที่ผ่านรายการแล้ว"), ("all_entries", "ทั้งหมด")],
        string="Target Moves",
        default="all_posted_entries",
        required=True,
    )
    p_Show_Balance_Zero = fields.Selection(
        [("not_zero", "ไม่รวมรายการที่เป็น 0"), ("all", "ทั้งหมด")],
        string="Balance Zero",
        default="not_zero",
        required=True,
    )
    p_language = fields.Selection(
        [("thai", "Thai"), ("english", "English")],
        string="Language",
        default="thai",
        required=True,
    )

    journal_ids = fields.Many2many(
        "account.journal",
        relation="od19_trial_balance_report_journal_rel",
        string="Journal Name",
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        relation="od19_trial_balance_report_analytic_rel",
        string="Analytic Accounts",
    )

    def _legacy_date_text(self, value):
        """``dd-mm-yyyy`` text with the Buddhist-era offset on ``BE``."""
        year_add = 543 if self.date_type == "BE" else 0
        return "{0:02d}-{1:02d}-{2:d}".format(
            value.day, value.month, value.year + year_add
        )

    def _legacy_where(self):
        """Extra SQL predicate appended to the report query."""
        p_where = ""
        if self.journal_ids:
            p_where += " and amd.journal_id in (%s)" % ", ".join(
                str(i) for i in self.journal_ids.ids
            )
        if self.analytic_account_ids:
            keys = ", ".join("'%s'" % i for i in self.analytic_account_ids.ids)
            p_where += " and amld.analytic_distribution ?| array[%s]" % keys
        if self.p_State == "all_posted_entries":
            p_where += " and amd.state = 'posted'"
        return p_where

    def get_parameters(self):
        """Values handed to jasperstarter as ``-P key=value``."""
        is_english = self.p_language == "english"
        all_text = "All" if is_english else "ทั้งหมด"
        if is_english:
            state_text = (
                "All posted entries"
                if self.p_State == "all_posted_entries"
                else "All"
            )
        else:
            state_text = (
                "เฉพาะที่ผ่านรายการแล้ว"
                if self.p_State == "all_posted_entries"
                else "ทั้งหมด"
            )
        return {
            "p_Show_Balance_Zero": "Y" if self.p_Show_Balance_Zero == "all" else "N",
            "p_State": state_text,
            "p_Where": "%s and amld.company_id = %s"
            % (self._legacy_where(), self.company_id.id),
            "p_Company": "%s" % self.company_id.id,
            "p_JournalText": ", ".join(self.journal_ids.mapped("code")) or all_text,
            "p_AnalyticAccountText": ", ".join(
                self.analytic_account_ids.mapped("name")
            )
            or all_text,
            "p_DateFormat": str(self.date_format),
            "p_From_Date": str(self.p_From_Date),
            "p_To_Date": str(self.p_To_Date),
            "p_From_Date_Text": self._legacy_date_text(self.p_From_Date),
            "p_To_Date_Text": self._legacy_date_text(self.p_To_Date),
            "p_Print_By": self._legacy_print_by(),
            "p_language": self.p_language,
        }

    def action_clear_journal(self):
        self.ensure_one()
        self.journal_ids = self.env["account.journal"].browse(0)
        return {"type": "ir.actions.do_nothing"}

    def action_clear_analytic(self):
        self.ensure_one()
        self.analytic_account_ids = self.env["account.analytic.account"].browse(0)
        return {"type": "ir.actions.do_nothing"}
