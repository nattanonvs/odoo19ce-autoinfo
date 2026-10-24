# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)
"""Wizard and form views: buttons, optional source column, wizard dialogs."""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDocumentPullViews(TransactionCase):
    def _view_arch(self, xmlid):
        view = self.env.ref(xmlid, raise_if_not_found=False)
        self.assertTrue(view, "missing view %s" % xmlid)
        return view.arch_db

    def test_invoice_form_has_pull_buttons(self):
        arch = self._view_arch(
            "od19_document_pull.view_move_form_od19_document_pull"
        )
        self.assertIn("od19_action_open_pull_wizard", arch)
        self.assertIn("od19_action_open_remove_wizard", arch)

    def test_invoice_line_source_column_is_optional(self):
        arch = self._view_arch(
            "od19_document_pull.view_move_form_od19_document_pull"
        )
        self.assertIn('optional="show"', arch)
        self.assertIn("od19_source_pull_label", arch)

    def test_pull_wizard_view_exists(self):
        arch = self._view_arch(
            "od19_document_pull.view_od19_document_pull_wizard_form"
        )
        self.assertIn("action_pull", arch)

    def test_purchase_order_form_has_pull_buttons(self):
        arch = self._view_arch(
            "od19_document_pull.view_order_form_od19_document_pull"
        )
        self.assertIn("od19_action_open_pull_wizard", arch)
        self.assertIn("od19_action_open_remove_wizard", arch)
        self.assertIn("od19_pull_source_label", arch)

    def test_remove_wizard_view_has_confirmation_buttons(self):
        arch = self._view_arch(
            "od19_document_pull.view_od19_document_pull_remove_wizard_form"
        )
        self.assertIn("action_select_source", arch)
        self.assertIn("action_remove", arch)
        self.assertIn("action_back", arch)
