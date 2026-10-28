import os

from odoo import fields
from odoo.tests.common import TransactionCase


class TestJasperReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_model = cls.env.ref("account.model_account_move")
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "is_company": True}
        )

    def test_create_report_template(self):
        template = self.env["jasper.report.template"].create(
            {
                "name": "Customer Invoice",
                "model_id": self.account_model.id,
                "report_type": "qweb",
                "template": "<t t-name='test'>Hello</t>",
            }
        )
        self.assertEqual(template.name, "Customer Invoice")
        self.assertEqual(template.report_type, "qweb")
        self.assertTrue(template.active)

    def test_qweb_requires_template_content(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env["jasper.report.template"].create(
                {
                    "name": "No Template",
                    "model_id": self.account_model.id,
                    "report_type": "qweb",
                }
            )

    def test_jasper_requires_url(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env["jasper.report.template"].create(
                {
                    "name": "No URL",
                    "model_id": self.account_model.id,
                    "report_type": "jasper",
                }
            )

    def test_create_report_action(self):
        template = self.env["jasper.report.template"].create(
            {
                "name": "Customer Invoice",
                "model_id": self.account_model.id,
                "report_type": "qweb",
                "template": "<t t-name='test'>Hello</t>",
            }
        )
        action = self.env["jasper.report.action"].create(
            {
                "name": "Print Invoice",
                "template_id": template.id,
            }
        )
        self.assertEqual(action.name, "Print Invoice")
        self.assertEqual(action.template_id, template)
        self.assertEqual(action.model_id, template.model_id)

    def test_action_print_qweb(self):
        template = self.env["jasper.report.template"].create(
            {
                "name": "Customer Invoice",
                "model_id": self.account_model.id,
                "report_type": "qweb",
                "template": "<t t-name='test'>Hello</t>",
            }
        )
        action = self.env["jasper.report.action"].create(
            {
                "name": "Print Invoice",
                "template_id": template.id,
            }
        )
        result = action.action_print(record_ids=[])
        self.assertTrue(result)

    def test_action_print_jasper(self):
        template = self.env["jasper.report.template"].create(
            {
                "name": "Customer Invoice Jasper",
                "model_id": self.account_model.id,
                "report_type": "jasper",
                "jasper_url": "http://jasper.example.com/report",
            }
        )
        action = self.env["jasper.report.action"].create(
            {
                "name": "Print Invoice Jasper",
                "template_id": template.id,
            }
        )
        result = action.action_print(record_ids=[])
        self.assertEqual(result.get("type"), "ir.actions.act_url")


class TestArApAgingReport(TransactionCase):
    def test_default_jasper_file_is_shipped(self):
        report = self.env["ar.ap.aging.report"].create({})
        self.assertTrue(report.jasper_file.endswith("ar_ap_aging_report.jasper"))

    def test_parameters_follow_legacy_contract(self):
        report = self.env["ar.ap.aging.report"].create(
            {"as_date": "2026-10-23", "p_Type": "ar", "p_Days": 15}
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Type"], "ar")
        self.assertEqual(parameters["p_Days"], "15")
        self.assertEqual(parameters["p_Detail"], "False")
        self.assertEqual(parameters["p_As_Date"], "2026-10-23")
        self.assertEqual(parameters["p_AccountCodeText"], "")
        self.assertEqual(parameters["company_id"], "%s" % report.company_id.id)
        self.assertEqual(parameters["company_name"], report.company_id.name)
        self.assertEqual(parameters["account_ids"], "null")
        self.assertEqual(parameters["partner_ids"], "null")
        self.assertEqual(parameters["p_Print_By"], self.env.user.name)

    def test_date_text_follows_date_type(self):
        report = self.env["ar.ap.aging.report"].create(
            {"as_date": "2026-10-23", "date_type": "BE"}
        )
        self.assertEqual(report._legacy_date_text(), "23-10-2569")
        self.assertEqual(report.get_parameters()["p_DateText"], "ณ วันที่ 23-10-2569")
        report.date_type = "AD"
        self.assertEqual(report._legacy_date_text(), "23-10-2026")

    def test_partner_scope_follows_account_type(self):
        customer = self.env["res.partner"].create(
            {"name": "Aging Customer", "customer_rank": 1}
        )
        vendor = self.env["res.partner"].create(
            {"name": "Aging Vendor", "supplier_rank": 1}
        )
        report = self.env["ar.ap.aging.report"].create(
            {
                "p_Type": "ar",
                "customer_ids": [(6, 0, customer.ids)],
                "vendor_ids": [(6, 0, vendor.ids)],
            }
        )
        self.assertEqual(
            report.get_parameters()["partner_ids"], "array[%s]" % customer.id
        )
        report.p_Type = "ap"
        self.assertEqual(
            report.get_parameters()["partner_ids"], "array[%s]" % vendor.id
        )


class TestGeneralLedgerReport(TransactionCase):
    def test_default_jasper_file_is_shipped(self):
        report = self.env["general.ledger.report"].create({})
        self.assertTrue(report.jasper_file.endswith("general_ledger.jasper"))

    def test_parameters_follow_legacy_contract(self):
        report = self.env["general.ledger.report"].create(
            {"p_From_Date": "2026-01-01", "p_To_Date": "2026-10-23"}
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_State"], "เฉพาะที่ผ่านรายการแล้ว")
        self.assertEqual(parameters["p_AccountCodeText"], "ทั้งหมด")
        self.assertEqual(parameters["p_JournalText"], "ทั้งหมด")
        self.assertEqual(parameters["p_AnalyticAccountText"], "ทั้งหมด")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_From_Date"], "2026-01-01")
        self.assertEqual(parameters["p_To_Date"], "2026-10-23")
        self.assertEqual(
            parameters["p_Where"],
            " and am.state = 'posted' and aml.company_id = %s"
            % report.company_id.id,
        )
        self.assertEqual(parameters["p_Print_By"], self.env.user.name)

    def test_sort_follows_selection(self):
        report = self.env["general.ledger.report"].create({})
        self.assertIn("aa.code_store", report.get_parameters()["p_Sort"])
        self.assertEqual(report.get_parameters()["p_SortingText"], "รหัสบัญชี")
        report.p_Sort = "date"
        self.assertTrue(
            report.get_parameters()["p_Sort"].startswith(" order by aml.date")
        )
        self.assertEqual(report.get_parameters()["p_SortingText"], "วันที่")

    def test_date_text_follows_locale(self):
        report = self.env["general.ledger.report"].create(
            {"p_From_Date": "2026-01-05", "p_To_Date": "2026-10-23"}
        )
        self.assertEqual(report.get_parameters()["p_From_Date_Text"], "05-01-2569")
        report.locale = "en_EN"
        self.assertEqual(report.get_parameters()["p_From_Date_Text"], "05-01-2026")

    def test_where_follows_filters(self):
        account = self.env["account.account"].search([], limit=1)
        journal = self.env["account.journal"].search([], limit=1)
        self.assertTrue(account and journal)
        report = self.env["general.ledger.report"].create(
            {
                "account_ids": [(6, 0, account.ids)],
                "journal_ids": [(6, 0, journal.ids)],
                "p_State": "all_entries",
            }
        )
        where = report.get_parameters()["p_Where"]
        self.assertIn("aml.account_id in (%s)" % account.id, where)
        self.assertIn("am.journal_id in (%s)" % journal.id, where)
        self.assertNotIn("am.state = 'posted'", where)


class TestTrialBalanceReport(TransactionCase):
    def test_default_jasper_file_is_shipped(self):
        report = self.env["trial.balance.report"].create({})
        self.assertTrue(report.jasper_file.endswith("trial_balance_report.jasper"))

    def test_parameters_follow_legacy_contract(self):
        report = self.env["trial.balance.report"].create(
            {"p_From_Date": "2026-01-01", "p_To_Date": "2026-10-23"}
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_Show_Balance_Zero"], "N")
        self.assertEqual(parameters["p_State"], "เฉพาะที่ผ่านรายการแล้ว")
        self.assertEqual(parameters["p_JournalText"], "ทั้งหมด")
        self.assertEqual(parameters["p_AnalyticAccountText"], "ทั้งหมด")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_From_Date"], "2026-01-01")
        self.assertEqual(parameters["p_To_Date"], "2026-10-23")
        self.assertEqual(parameters["p_Company"], "%s" % report.company_id.id)
        self.assertEqual(
            parameters["p_Where"],
            " and amd.state = 'posted' and amld.company_id = %s"
            % report.company_id.id,
        )
        self.assertEqual(parameters["p_Print_By"], self.env.user.name)
        self.assertEqual(parameters["p_language"], "thai")

    def test_show_balance_zero_all_flag(self):
        report = self.env["trial.balance.report"].create(
            {"p_Show_Balance_Zero": "all"}
        )
        self.assertEqual(report.get_parameters()["p_Show_Balance_Zero"], "Y")

    def test_date_text_follows_date_type(self):
        report = self.env["trial.balance.report"].create(
            {"p_From_Date": "2026-01-05", "p_To_Date": "2026-10-23"}
        )
        self.assertEqual(report.get_parameters()["p_From_Date_Text"], "05-01-2026")
        report.date_type = "BE"
        self.assertEqual(report.get_parameters()["p_From_Date_Text"], "05-01-2569")

    def test_language_switches_labels(self):
        report = self.env["trial.balance.report"].create({"p_language": "english"})
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_language"], "english")
        self.assertEqual(parameters["p_State"], "All posted entries")
        self.assertEqual(parameters["p_JournalText"], "All")
        self.assertEqual(parameters["p_AnalyticAccountText"], "All")

    def test_where_follows_filters(self):
        journal = self.env["account.journal"].search([], limit=1)
        self.assertTrue(journal)
        report = self.env["trial.balance.report"].create(
            {
                "journal_ids": [(6, 0, journal.ids)],
                "p_State": "all_entries",
            }
        )
        where = report.get_parameters()["p_Where"]
        self.assertIn("amd.journal_id in (%s)" % journal.id, where)
        self.assertNotIn("amd.state = 'posted'", where)


class TestPlBsReport(TransactionCase):
    def test_default_jasper_file_is_shipped(self):
        for model in ("pl.bs.report", "profit.loss.report", "balance.sheet.report"):
            report = self.env[model].create({})
            self.assertTrue(report.jasper_file.endswith("pl_bs.jasper"))

    def test_profit_loss_parameters_follow_legacy_contract(self):
        report = self.env["profit.loss.report"].create(
            {"rpt_month": "10", "rpt_year": "2026"}
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["report_name"], "Profit and Loss")
        self.assertEqual(parameters["company_id"], "%s" % report.company_id.id)
        self.assertEqual(parameters["p_Level"], "3")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_Print_By"], self.env.user.name)
        self.assertEqual(parameters["show_dr_cr"], "0")
        self.assertEqual(parameters["show_comp"], "0")
        self.assertEqual(parameters["report_date"], "ประจำงวด มกราคม - ตุลาคม 2569")
        self.assertIn("b.date >= '2026-01-01'", parameters["move_criteria"])
        self.assertIn("b.date <= date '2026-10-31'", parameters["move_criteria"])
        self.assertIn("a.state = 'posted'", parameters["move_criteria"])
        self.assertIn(
            "b.company_id = %s" % report.company_id.id, parameters["move_criteria"]
        )

    def test_report_template_maps_to_level(self):
        report = self.env["profit.loss.report"].create({})
        self.assertEqual(report.get_parameters()["p_Level"], "3")
        report.report_template = "pl_bs_lvl4"
        self.assertEqual(report.get_parameters()["p_Level"], "4")
        report.report_template = "pl_bs"
        self.assertEqual(report.get_parameters()["p_Level"], "5")

    def test_report_name_falls_back_to_wizard_name(self):
        report = self.env["profit.loss.report"].create({"rpt_nm": "งบกำไรขาดทุน"})
        self.assertEqual(report.get_parameters()["report_name"], "งบกำไรขาดทุน")

    def test_account_criteria_scope_by_statement(self):
        profit_loss = self.env["profit.loss.report"].create({})
        criteria = profit_loss.get_parameters()["account_criteria"]
        self.assertIn("aa.account_type in (", criteria)
        self.assertIn("'income'", criteria)
        self.assertIn("'expense_direct_cost'", criteria)
        self.assertNotIn("'asset_current'", criteria)

        balance_sheet = self.env["balance.sheet.report"].create({})
        criteria = balance_sheet.get_parameters()["account_criteria"]
        self.assertIn("'asset_current'", criteria)
        self.assertIn("'equity_unaffected'", criteria)
        self.assertIn("aa.account_type = 'equity_unaffected'", criteria)
        self.assertNotIn("'income'", criteria)

    def test_comparison_criteria_only_when_comparing(self):
        report = self.env["balance.sheet.report"].create(
            {"rpt_month": "10", "rpt_year": "2026", "cmp_month": "10", "cmp_year": "2025"}
        )
        parameters = report.get_parameters()
        self.assertIn("where 1 = 0", parameters["comp_criteria"])
        self.assertEqual(parameters["show_comp"], "0")

        report.show_type = "comp"
        parameters = report.get_parameters()
        self.assertIn("b.date <= date '2025-10-31'", parameters["comp_criteria"])
        self.assertEqual(parameters["show_comp"], "1")
        self.assertEqual(parameters["show_dr_cr"], "0")

    def test_display_condition_dr_cr(self):
        report = self.env["profit.loss.report"].create({"show_type": "drcr"})
        parameters = report.get_parameters()
        self.assertEqual(parameters["show_dr_cr"], "1")
        self.assertEqual(parameters["show_comp"], "0")

    def test_language_switches_labels(self):
        today = fields.Date.context_today(self.env["balance.sheet.report"])
        report = self.env["balance.sheet.report"].create(
            {
                "p_language": "english",
                "rpt_month": str(today.month),
                "rpt_year": str(today.year),
            }
        )
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_language"], "english")
        self.assertEqual(parameters["report_name"], "Balance Sheet")
        self.assertTrue(parameters["report_date"].startswith("As at "))
        report.p_language = "thai"
        self.assertEqual(report.get_parameters()["report_name"], "Balance Sheet")
        self.assertTrue(report.get_parameters()["report_date"].startswith("ณ วันที่ "))

    def test_period_options_use_explicit_dates(self):
        report = self.env["profit.loss.report"].create(
            {
                "options": "period",
                "period_start": "2026-03-01",
                "period_end": "2026-03-31",
            }
        )
        parameters = report.get_parameters()
        self.assertIn("b.date >= '2026-03-01'", parameters["move_criteria"])
        self.assertIn("b.date <= '2026-03-31'", parameters["move_criteria"])
        self.assertIn("where 1 = 0", parameters["comp_criteria"])

    def test_balance_sheet_injects_current_year_earnings(self):
        report = self.env["balance.sheet.report"].create(
            {"rpt_month": "10", "rpt_year": "2026"}
        )
        parameters = report.get_parameters()
        self.assertIsInstance(parameters["pl_dr"], str)
        self.assertIsInstance(parameters["pl_balance"], str)
        self.assertIsInstance(parameters["pl_cmp_balance"], str)


class TestJournalVoucherForm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Voucher Partner", "is_company": True}
        )
        cls.move = cls.env["account.move"].create(
            {"move_type": "entry", "partner_id": cls.partner.id}
        )

    def _report(self, move=True, **values):
        report = self.env["journal.voucher.form"].create(values)
        if move:
            report = report.with_context(active_ids=self.move.ids)
        return report

    def test_default_jasper_file_is_shipped(self):
        report = self.env["journal.voucher.form"].create({})
        self.assertTrue(report.jasper_file.endswith("journal_voucher_form.jasper"))

    def test_parameters_follow_legacy_contract(self):
        report = self._report()
        parameters = report.get_parameters()
        self.assertEqual(
            parameters["p_ID"],
            "WHERE al.balance != 0 AND am.id in (%s)" % self.move.id,
        )
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_ISO"], "")
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(report.name, self.move.display_name)

    def test_locale_follows_date_type(self):
        report = self._report(date_type="BE")
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_signature_toggles_flow_to_parameters(self):
        report = self._report(p_EName=False, p_ESignature=False)
        parameters = report.get_parameters()
        self.assertEqual(parameters["p_EName"], "False")
        self.assertEqual(parameters["p_ESignature"], "False")

    def test_no_document_selected_raises(self):
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self._report(move=False).get_parameters()

    def test_partner_ids_for_send_by_email(self):
        report = self._report()
        self.assertEqual(report.get_partner_ids_for_send_by_email(), self.partner)


class TestInvoiceFormPorts(TransactionCase):
    """Batch 1 of the ``dtr_accounting_form`` port.

    Covers the six printable forms F-AC-002/003/005/006/007/008.  Every form
    re-uses the shared engine, so the tests assert the legacy parameter
    contract and that the compiled ``.jasper`` ships with the module.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Form Partner", "is_company": True}
        )
        cls.sale_journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )

    def _move(self, **values):
        vals = {"partner_id": self.partner.id, "journal_id": self.sale_journal.id}
        vals.update(values)
        return self.env["account.move"].create(vals)

    def _shipped(self, model):
        report = self.env[model].create({})
        self.assertTrue(report.jasper_file.endswith(".jasper"))
        self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)
        return report

    # ------------------------------------------------------------- shipping
    def test_compiled_templates_are_shipped(self):
        for model in ("credit.note.form", "debit.note.form", "billing.form",
                      "prepayment.form", "receipt.cash.form", "receipt.form"):
            self._shipped(model)

    def test_compiled_names_match_python_module(self):
        self._shipped("credit.note.form").jasper_file.endswith("credit_note_form.jasper")
        self.assertTrue(self._shipped("debit.note.form").jasper_file.endswith(
            "debit_note_form.jasper"))
        self.assertTrue(self._shipped("billing.form").jasper_file.endswith(
            "billing_form.jasper"))
        self.assertTrue(self._shipped("prepayment.form").jasper_file.endswith(
            "prepayment_form.jasper"))
        self.assertTrue(self._shipped("receipt.form").jasper_file.endswith(
            "receipt_form.jasper"))

    # ---------------------------------------------------------- credit note
    def test_credit_note_parameters_follow_legacy_contract(self):
        move = self._move(move_type="out_refund")
        report = self.env["credit.note.form"].with_context(
            active_ids=move.ids
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "where invoice.id in (%s)" % move.id)
        self.assertEqual(parameters["iscopy"], "0")
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_locale"], "en")
        self.assertEqual(parameters["p_DateFormat"], "dd-MM-yyyy")
        self.assertEqual(report.name, move.display_name)

    def test_credit_note_rejects_plain_invoice(self):
        from odoo.exceptions import ValidationError
        move = self._move(move_type="out_invoice")
        report = self.env["credit.note.form"].with_context(
            active_ids=move.ids
        ).create({})
        with self.assertRaises(ValidationError):
            report.get_parameters()

    # ----------------------------------------------------------- debit note
    def test_debit_note_parameters_follow_legacy_contract(self):
        move = self._move(move_type="out_invoice", dncn="dn")
        report = self.env["debit.note.form"].with_context(
            active_ids=move.ids
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "where invoice.id in (%s)" % move.id)
        self.assertEqual(parameters["p_locale"], "en")
        report.date_type = "BE"
        self.assertEqual(report.get_parameters()["p_locale"], "th")

    def test_debit_note_rejects_plain_invoice(self):
        from odoo.exceptions import ValidationError
        move = self._move(move_type="out_invoice")
        report = self.env["debit.note.form"].with_context(
            active_ids=move.ids
        ).create({})
        with self.assertRaises(ValidationError):
            report.get_parameters()

    # -------------------------------------------------------------- billing
    def test_billing_parameters_follow_legacy_contract(self):
        move = self._move(move_type="out_invoice")
        report = self.env["billing.form"].with_context(
            active_ids=move.ids
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "WHERE bill.id in (%s)" % move.id)
        self.assertTrue(parameters["p_Path"].endswith("/"))
        self.assertEqual(parameters["p_ISO"], "")
        self.assertEqual(parameters["p_EName"], "True")
        self.assertEqual(parameters["p_ESignature"], "True")
        self.assertEqual(parameters["p_Iscopy"], "0")
        self.assertEqual(report.get_partner_ids_for_send_by_email(), self.partner)

    # ----------------------------------------------------------- prepayment
    def test_prepayment_parameters_follow_legacy_contract(self):
        payment = self.env["account.payment"].create(
            {"partner_id": self.partner.id, "amount": 1500.0}
        )
        report = self.env["prepayment.form"].with_context(
            active_ids=payment.ids
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "WHERE bill.id in (%s)" % payment.id)
        self.assertEqual(parameters["p_language"], "thai")
        self.assertEqual(parameters["p_ESignature"], "True")

    # --------------------------------------------------------- receipt cash
    def test_receipt_cash_parameters_follow_legacy_contract(self):
        payment = self.env["account.payment"].create(
            {"partner_id": self.partner.id, "amount": 300.0}
        )
        report = self.env["receipt.cash.form"].with_context(
            active_ids=payment.ids
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "WHERE cash.id in (%s)" % payment.id)
        self.assertEqual(parameters["p_Tax"], "1")
        report.p_Tax = "2"
        self.assertEqual(report.get_parameters()["p_Tax"], "2")

    # -------------------------------------------------------------- receipt
    def test_receipt_parameters_follow_legacy_contract(self):
        payment = self.env["account.payment"].create(
            {"partner_id": self.partner.id, "amount": 700.0}
        )
        report = self.env["receipt.form"].with_context(
            active_ids=payment.ids
        ).create({})
        parameters = report.get_parameters()
        self.assertEqual(parameters["ids"], "WHERE pay.id in (%s)" % payment.id)
        self.assertEqual(parameters["p_Tax"], "1")
        self.assertEqual(parameters["p_EName"], "True")
        self.assertTrue(parameters["p_Path"].endswith("/"))
