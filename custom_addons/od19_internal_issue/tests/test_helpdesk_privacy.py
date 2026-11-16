from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPlaceholder(TransactionCase):
    def test_module_installed(self):
        self.assertIn("helpdesk.ticket", self.env)
