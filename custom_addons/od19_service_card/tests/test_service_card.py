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

    # ------------------------------------------------------------------
    # SLA tests
    # ------------------------------------------------------------------
    def test_sla_deadline_computed_from_create_date(self):
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
            'sla_hours': 24,
        })
        self.assertTrue(card.sla_deadline)
        expected = card.create_date + timedelta(hours=24)
        self.assertEqual(card.sla_deadline, expected)

    def test_no_sla_deadline_when_zero_hours(self):
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
            'sla_hours': 0,
        })
        self.assertFalse(card.sla_deadline)

    def test_sla_breached_when_past_deadline(self):
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
            'sla_hours': 1,
        })
        # Force the deadline to be in the past
        card.sla_deadline = fields.Datetime.now() - timedelta(hours=2)
        card.env.invalidate_all()
        self.assertTrue(card.is_sla_breached)

    def test_sla_not_breached_when_done(self):
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
            'sla_hours': 1,
        })
        card.sla_deadline = fields.Datetime.now() - timedelta(hours=2)
        card.action_confirm()
        card.action_done()
        card.env.invalidate_all()
        self.assertFalse(card.is_sla_breached)

    # ------------------------------------------------------------------
    # Time tracking tests
    # ------------------------------------------------------------------
    def test_duration_computed_from_start_and_end(self):
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
        })
        start = fields.Datetime.now() - timedelta(hours=2, minutes=30)
        end = fields.Datetime.now()
        card.start_time = start
        card.end_time = end
        card.env.invalidate_all()
        self.assertAlmostEqual(card.duration, 2.5, places=1)

    def test_duration_zero_without_end_time(self):
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
        })
        card.start_time = fields.Datetime.now()
        card.env.invalidate_all()
        self.assertEqual(card.duration, 0.0)

    # ------------------------------------------------------------------
    # Team & sale order link tests
    # ------------------------------------------------------------------
    def test_team_id_field_exists(self):
        department = self.env['hr.department'].create({'name': 'Service Team'})
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
            'team_id': department.id,
        })
        self.assertEqual(card.team_id, department)

    def test_sale_order_link(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        card = self.env['od19.service.card'].create({
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'service_type': 'preventive',
            'sale_order_id': order.id,
        })
        self.assertEqual(card.sale_order_id, order)

