# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestStockValuationAdjustment(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'standard_price': 10.0,
        })

    def test_current_value_computation(self):
        """Current value should match product standard_price."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'adjustment_type': 'price_change',
            'reason': 'Market price update',
        })
        self.assertEqual(adj.current_value, 10.0)

    def test_total_adjustment_computation(self):
        """Total adjustment should be (new - current) * quantity."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 12.0,
            'adjustment_type': 'price_change',
            'reason': 'Market price update',
        })
        # (12 - 10) * 5 = 10
        self.assertEqual(adj.total_adjustment, 10.0)

    def test_negative_total_adjustment(self):
        """Total adjustment should be negative when new < current."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 8.0,
            'adjustment_type': 'write_down',
            'reason': 'Price drop',
        })
        # (8 - 10) * 5 = -10
        self.assertEqual(adj.total_adjustment, -10.0)

    def test_workflow_confirm_require_new_value(self):
        """Confirm should fail if new_value is not set."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'adjustment_type': 'price_change',
            'reason': 'Test',
        })
        with self.assertRaises(Exception):
            adj.action_confirm()

    def test_workflow_confirm_to_done(self):
        """Adjustment should go draft -> confirmed -> done."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 15.0,
            'adjustment_type': 'price_change',
            'reason': 'Price increase',
        })
        self.assertEqual(adj.state, 'draft')

        adj.action_confirm()
        self.assertEqual(adj.state, 'confirmed')

        adj.action_approve()
        self.assertEqual(adj.state, 'done')
        self.assertEqual(adj.approved_by, self.env.user)

    def test_approve_updates_product_price(self):
        """Approving a price change should update product standard_price."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 25.0,
            'adjustment_type': 'price_change',
            'reason': 'Price update',
        })
        adj.action_confirm()
        adj.action_approve()
        self.assertEqual(self.product.standard_price, 25.0)

    def test_approve_creates_audit_line(self):
        """Approving should create an audit trail line."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 20.0,
            'adjustment_type': 'price_change',
            'reason': 'Audit test',
        })
        adj.action_confirm()
        adj.action_approve()
        self.assertEqual(len(adj.line_ids), 1)
        self.assertEqual(adj.line_ids.old_value, 10.0)
        self.assertEqual(adj.line_ids.new_value, 20.0)

    def test_reference_sequence(self):
        """Reference should be generated from sequence."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 12.0,
            'adjustment_type': 'price_change',
            'reason': 'Seq test',
        })
        self.assertTrue(adj.name.startswith('SVA/'))

    def test_approve_without_valuation_layer_model(self):
        """Odoo 19 removed stock.valuation.layer; approving must still succeed
        (the valuation-layer creation path is a guarded no-op)."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 12.0,
            'adjustment_type': 'price_change',
            'reason': 'SVL no-op test',
        })
        adj.action_confirm()
        adj.action_approve()
        self.assertEqual(adj.state, 'done')
        self.assertFalse(self.env.get('stock.valuation.layer'))

    def test_approve_requires_stock_manager(self):
        """Only inventory managers can approve a valuation adjustment."""
        base_user_group = self.env.ref('base.group_user')
        stock_user_group = self.env.ref('stock.group_stock_user')
        stock_user = self.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'SVA Stock User',
            'login': 'sva.stock.user@example.com',
            'email': 'sva.stock.user@example.com',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'group_ids': [(6, 0, [base_user_group.id, stock_user_group.id])],
        })
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 12.0,
            'adjustment_type': 'price_change',
            'reason': 'Gate test',
        })
        adj.action_confirm()
        with self.assertRaises(AccessError):
            adj.with_user(stock_user).action_approve()
        self.assertEqual(adj.state, 'confirmed')

    def test_cancel_reverts_price_change(self):
        """Cancelling a done price-change adjustment should revert standard_price."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 20.0,
            'adjustment_type': 'price_change',
            'reason': 'Cancel test',
        })
        adj.action_confirm()
        adj.action_approve()
        self.assertEqual(self.product.standard_price, 20.0)
        adj.action_cancel()
        self.assertEqual(adj.state, 'cancelled')
        self.assertEqual(self.product.standard_price, 10.0)

    def test_reset_to_draft_from_cancelled(self):
        """A cancelled adjustment can be reset to draft."""
        adj = self.env['od19.stock.valuation.adjustment'].create({
            'product_id': self.product.id,
            'quantity': 5.0,
            'new_value': 12.0,
            'adjustment_type': 'price_change',
            'reason': 'Reset test',
        })
        adj.action_confirm()
        adj.action_cancel()
        self.assertEqual(adj.state, 'cancelled')
        adj.action_reset_to_draft()
        self.assertEqual(adj.state, 'draft')
