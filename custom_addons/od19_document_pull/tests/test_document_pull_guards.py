# Copyright 2026 OD19
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDocumentPullGuards(AccountTestInvoicingCommon):
    def test_editable_states_default_is_draft_only(self):
        move = self.env["account.move"].new({"move_type": "in_invoice"})
        self.assertEqual(move._od19_pull_editable_states(), ("draft",))

    def test_check_editable_raises_when_posted(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, post=True, amounts=[100.0]
        )
        with self.assertRaises(UserError):
            bill._od19_pull_check_editable()

    def test_open_pull_wizard_returns_act_window(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, invoice_date="2026-01-01"
        )
        action = bill.od19_action_open_pull_wizard()
        self.assertEqual(action["res_model"], "od19.document.pull.wizard")
        self.assertEqual(action["target"], "new")
        self.assertEqual(action["context"]["default_res_id"], bill.id)
        self.assertEqual(action["context"]["default_res_model"], "account.move")

    def test_open_remove_wizard_returns_act_window(self):
        bill = self.init_invoice(
            "in_invoice", partner=self.partner_a, invoice_date="2026-01-01"
        )
        action = bill.od19_action_open_remove_wizard()
        self.assertEqual(action["res_model"], "od19.document.pull.remove.wizard")
        self.assertEqual(action["context"]["default_res_id"], bill.id)

    def test_source_lineage_fields_exist(self):
        aml = self.env["account.move.line"]
        self.assertIn("od19_source_move_line_id", aml._fields)
        self.assertIn("od19_source_picking_id", aml._fields)
        self.assertEqual(
            aml._fields["od19_source_move_line_id"].comodel_name, "account.move.line"
        )
        self.assertEqual(
            aml._fields["od19_source_picking_id"].comodel_name, "stock.picking"
        )

    def test_source_label_field_on_purchase_order_line(self):
        self.assertIn(
            "od19_pull_source_label", self.env["purchase.order.line"]._fields
        )
