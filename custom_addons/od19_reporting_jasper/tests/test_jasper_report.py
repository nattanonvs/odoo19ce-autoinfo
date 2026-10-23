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
