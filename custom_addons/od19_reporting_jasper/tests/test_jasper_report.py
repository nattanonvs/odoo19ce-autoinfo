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
