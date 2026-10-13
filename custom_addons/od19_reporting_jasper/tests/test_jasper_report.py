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
