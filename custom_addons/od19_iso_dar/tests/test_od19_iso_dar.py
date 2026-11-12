from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestIsoDar(TransactionCase):
    def test_module_installed(self):
        self.assertIn("od19.iso.dar", self.env)
