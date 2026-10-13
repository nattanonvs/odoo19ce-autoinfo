# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestServiceCard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Equipment',
            'type': 'consu',
            'service_interval': 90,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Customer',
        })

    def test_next_service_date_computation(self):
        """Next service date should be service_date + interval."""
        today = fields.Date.context_today(self.env.user)
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_date': today,
            'service_interval': 90,
            'service_type': 'preventive',
        })
        expected = today + timedelta(days=90)
        self.assertEqual(card.next_service_date, expected)

    def test_no_next_service_date_when_zero_interval(self):
        """No next service date when interval is 0."""
        today = fields.Date.context_today(self.env.user)
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_date': today,
            'service_interval': 0,
            'service_type': 'preventive',
        })
        self.assertFalse(card.next_service_date)

    def test_service_card_workflow(self):
        """Service card should follow draft -> confirmed -> done."""
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
        })
        self.assertEqual(card.state, 'draft')

        card.action_confirm()
        self.assertEqual(card.state, 'confirmed')

        card.action_done()
        self.assertEqual(card.state, 'done')

    def test_service_card_cancel(self):
        """Service card can be cancelled from draft or confirmed."""
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
        })
        card.action_cancel()
        self.assertEqual(card.state, 'cancelled')

        card.action_reset_to_draft()
        self.assertEqual(card.state, 'draft')

    def test_service_card_sequence(self):
        """Service card name should be generated from sequence."""
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
        })
        self.assertTrue(card.name.startswith('SC/'))

    def test_product_default_service_interval(self):
        """Product template should have service_interval field."""
        self.assertEqual(self.product.product_tmpl_id.service_interval, 90)
