# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAssetMultiBill(AccountTestInvoicingCommon):
    """Multi-bill support for assets built on top of account_asset_management."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.asset_model = cls.env["account.asset"]
        cls.asset_line_model = cls.env["account.asset.line"]

        cls.asset_account = cls.company_data["default_account_assets"]
        cls.profile = cls.env["account.asset.profile"].create(
            {
                "name": "IT Equipment - 3 Years",
                "account_asset_id": cls.asset_account.id,
                "account_depreciation_id": cls.asset_account.id,
                "account_expense_depreciation_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "account_residual_value_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "journal_id": cls.company_data["default_journal_misc"].id,
                "method_time": "year",
                "method_number": 3,
                "method_period": "year",
                "open_asset": True,
            }
        )
        # Linking the profile to the asset account makes every invoice line
        # booked on that account qualify for automatic asset creation, which
        # mirrors the standard OCA configuration.
        cls.asset_account.asset_profile_id = cls.profile.id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_bill(self, amount, name="Asset", target_asset=None):
        """Create a vendor bill with a single line booked on the asset
        account, optionally merged into an existing asset."""
        line_vals = {
            "name": name,
            "quantity": 1.0,
            "price_unit": amount,
            "account_id": self.asset_account.id,
        }
        if target_asset:
            line_vals["od19_target_asset_id"] = target_asset.id
        return (
            self.env["account.move"]
            .with_context(check_move_validity=False)
            .create(
                {
                    "move_type": "in_invoice",
                    "invoice_date": fields.Date.context_today(self.env.user),
                    "partner_id": self.partner_a.id,
                    "invoice_line_ids": [Command.create(line_vals)],
                }
            )
        )

    def _get_single_asset(self):
        assets = self.asset_model.search([])
        self.assertEqual(len(assets), 1)
        return assets

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_01_merge_two_bills_into_one_asset(self):
        """Two bills merged into the same asset produce a single asset whose
        purchase value is the sum of both bills."""
        self.assertEqual(self.asset_model.search_count([]), 0)

        # Bill 1 creates the asset (standard OCA behaviour).
        bill_1 = self._create_bill(2000.0, name="Server")
        bill_1.action_post()

        asset = self._get_single_asset()
        self.assertEqual(asset.purchase_value, 2000.0)
        self.assertEqual(asset.state, "open")

        # Bill 2 is merged into the existing asset.
        bill_2 = self._create_bill(500.0, name="Extra RAM", target_asset=asset)
        bill_2.action_post()

        # No new asset was created and the value was summed up.
        self.assertEqual(self.asset_model.search_count([]), 1)
        self.assertEqual(asset.purchase_value, 2500.0)
        self.assertEqual(asset.depreciation_base, 2500.0)
        self.assertIn(bill_2, asset.od19_additional_bill_ids)

        # The bill line is linked to the target asset and no extra asset
        # line links back to the additional bill.
        merge_line = bill_2.line_ids.filtered(
            lambda line: line.od19_target_asset_id == asset
        )
        self.assertEqual(merge_line.asset_id, asset)
        self.assertNotIn(
            bill_2, asset._od19_get_source_moves(),
            "The additional bill must not become the primary source document.",
        )

    def test_02_merge_blocked_when_asset_depreciated(self):
        """A bill cannot be merged into an asset that already has posted
        depreciation entries."""
        bill_1 = self._create_bill(3000.0, name="Machine")
        bill_1.action_post()
        asset = self._get_single_asset()

        dep_line = asset.depreciation_line_ids.filtered(
            lambda line: line.type == "depreciate"
        )[:1]
        dep_line.create_move()
        self.assertTrue(
            asset.depreciation_line_ids.filtered(
                lambda line: line.move_id and line.move_id.state == "posted"
            ),
            "A posted depreciation entry is expected for this test.",
        )

        bill_2 = self._create_bill(1000.0, name="Attachment", target_asset=asset)
        with self.assertRaises(UserError):
            bill_2.action_post()
        # The bill stays in draft and the asset value is untouched.
        self.assertEqual(bill_2.state, "draft")
        self.assertEqual(asset.purchase_value, 3000.0)

    def test_03_merge_blocked_when_asset_not_open(self):
        """A bill cannot be merged into an asset that is not draft/open."""
        bill_1 = self._create_bill(1000.0, name="Asset 1")
        bill_1.action_post()
        asset = self._get_single_asset()
        asset.state = "close"

        bill_2 = self._create_bill(100.0, name="Asset 2", target_asset=asset)
        with self.assertRaises(UserError):
            bill_2.action_post()

    def test_04_additional_bill_cannot_be_source(self):
        """The primary bill that created the asset cannot be listed again as
        an additional document."""
        bill_1 = self._create_bill(1000.0, name="Asset")
        bill_1.action_post()
        asset = self._get_single_asset()
        self.assertEqual(asset._od19_get_source_moves(), bill_1)

        with self.assertRaises(ValidationError):
            asset.od19_additional_bill_ids = [Command.link(bill_1.id)]

    def test_05_open_documents_action(self):
        """The 'open documents' buttons return a standard act_window: one
        document opens its form, several open a list, none shows a
        notification."""
        asset = self.asset_model.create(
            {
                "name": "Standalone",
                "profile_id": self.profile.id,
                "purchase_value": 1000.0,
                "date_start": fields.Date.context_today(self.env.user),
            }
        )

        # No document -> notification.
        action = asset.action_open_additional_bills()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")

        bill_a = self._create_bill(100.0, name="Doc A")
        bill_b = self._create_bill(200.0, name="Doc B")

        # Single document -> form.
        asset.od19_additional_bill_ids = [Command.set([bill_a.id])]
        action = asset.action_open_additional_bills()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["view_mode"], "form")
        self.assertEqual(action["res_id"], bill_a.id)

        # Several documents -> list.
        asset.od19_additional_bill_ids = [Command.set([bill_a.id, bill_b.id])]
        action = asset.action_open_additional_bills()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertNotIn("res_id", action)
        self.assertEqual(set(action["domain"][0][2]), {bill_a.id, bill_b.id})

    def test_06_button_draft_reverts_merge(self):
        """Resetting a merged bill to draft removes its value from the asset
        and clears the link."""
        bill_1 = self._create_bill(2000.0, name="Server")
        bill_1.action_post()
        asset = self._get_single_asset()

        bill_2 = self._create_bill(500.0, name="Extra RAM", target_asset=asset)
        bill_2.action_post()
        self.assertEqual(asset.purchase_value, 2500.0)
        self.assertIn(bill_2, asset.od19_additional_bill_ids)

        bill_2.button_draft()

        self.assertEqual(bill_2.state, "draft")
        self.assertEqual(asset.purchase_value, 2000.0)
        self.assertNotIn(bill_2, asset.od19_additional_bill_ids)
        self.assertFalse(
            bill_2.line_ids.filtered(
                lambda line: line.od19_target_asset_id == asset
            ).asset_id
        )
