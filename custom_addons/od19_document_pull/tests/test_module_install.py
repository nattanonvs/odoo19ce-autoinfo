# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestModuleInstall(TransactionCase):
    def test_mixin_is_registered(self):
        self.assertIn("od19.document.pull.mixin", self.env)

    def test_account_move_inherits_mixin(self):
        move = self.env["account.move"].new({})
        self.assertTrue(
            hasattr(move, "_od19_pull_source_specs"),
            "account.move must inherit od19.document.pull.mixin",
        )
