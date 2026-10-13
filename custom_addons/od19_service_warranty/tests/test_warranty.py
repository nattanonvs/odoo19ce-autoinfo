# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestWarranty(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'warranty_type': 'years',
            'warranty_duration': 1,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
        })
        cls.lot = cls.env['stock.lot'].create({
            'name': 'LOT001',
            'product_id': cls.product.id,
            'company_id': cls.env.company.id,
        })

    def test_warranty_days_computation(self):
        """Warranty duration in days should be computed correctly."""
        self.product.warranty_type = 'years'
        self.product.warranty_duration = 1
        self.assertEqual(self.product.product_tmpl_id._get_warranty_days(), 365)

        self.product.warranty_type = 'months'
        self.product.warranty_duration = 3
        self.assertEqual(self.product.product_tmpl_id._get_warranty_days(), 90)

        self.product.warranty_type = 'days'
        self.product.warranty_duration = 30
        self.assertEqual(self.product.product_tmpl_id._get_warranty_days(), 30)

        self.product.warranty_type = 'none'
        self.assertEqual(self.product.product_tmpl_id._get_warranty_days(), 0)

    def test_lot_warranty_end_date(self):
        """Warranty end date on lot should be computed from start + duration."""
        today = fields.Date.context_today(self.env.user)
        self.lot.warranty_start_date = today
        expected_end = today + timedelta(days=365)
        self.assertEqual(self.lot.warranty_end_date, expected_end)
        self.assertEqual(self.lot.warranty_status, 'active')

    def test_lot_warranty_expired(self):
        """Warranty status should be expired when end date is past."""
        today = fields.Date.context_today(self.env.user)
        self.lot.warranty_start_date = today - timedelta(days=400)
        self.assertEqual(self.lot.warranty_status, 'expired')

    def test_lot_no_warranty(self):
        """Warranty status should be 'none' when no warranty on product."""
        self.product.warranty_type = 'none'
        today = fields.Date.context_today(self.env.user)
        self.lot.warranty_start_date = today
        self.assertFalse(self.lot.warranty_end_date)
        self.assertEqual(self.lot.warranty_status, 'none')

    def test_claim_under_warranty(self):
        """Claim should detect active warranty from lot."""
        today = fields.Date.context_today(self.env.user)
        self.lot.warranty_start_date = today
        claim = self.env['od19.warranty.claim'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'lot_id': self.lot.id,
            'claim_type': 'warranty',
            'description': 'Defective product',
        })
        self.assertTrue(claim.under_warranty)

    def test_claim_not_under_warranty(self):
        """Claim should detect expired warranty."""
        today = fields.Date.context_today(self.env.user)
        self.lot.warranty_start_date = today - timedelta(days=400)
        claim = self.env['od19.warranty.claim'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'lot_id': self.lot.id,
            'claim_type': 'warranty',
            'description': 'Defective product',
        })
        self.assertFalse(claim.under_warranty)

    def test_claim_workflow(self):
        """Claim should follow draft -> confirmed -> in_progress -> done."""
        claim = self.env['od19.warranty.claim'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'claim_type': 'rma',
            'description': 'Test claim',
        })
        self.assertEqual(claim.state, 'draft')

        claim.action_confirm()
        self.assertEqual(claim.state, 'confirmed')

        claim.action_start()
        self.assertEqual(claim.state, 'in_progress')

        claim.action_done()
        self.assertEqual(claim.state, 'done')

    def test_claim_reject(self):
        """Claim can be rejected from draft."""
        claim = self.env['od19.warranty.claim'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'claim_type': 'rma',
            'description': 'Test claim',
        })
        claim.action_reject()
        self.assertEqual(claim.state, 'rejected')

    def test_claim_sequence(self):
        """Claim name should be generated from sequence."""
        claim = self.env['od19.warranty.claim'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'claim_type': 'rma',
            'description': 'Test claim',
        })
        self.assertTrue(claim.name.startswith('WC/'))

    def test_create_repair_order(self):
        """Creating repair order from claim should link both."""
        claim = self.env['od19.warranty.claim'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'claim_type': 'repair',
            'description': 'Needs repair',
        })
        claim.action_confirm()
        action = claim.action_create_repair_order()
        self.assertEqual(claim.state, 'in_progress')
        self.assertTrue(claim.repair_order_id)
        self.assertEqual(claim.repair_order_id.partner_id, self.partner)
        self.assertEqual(action['res_model'], 'repair.order')
