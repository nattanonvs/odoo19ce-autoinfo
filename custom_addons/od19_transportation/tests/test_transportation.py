# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, new_test_user
from odoo.exceptions import UserError


class TestTransportation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route = cls.env['od19.transport.route'].create({
            'name': 'Bangkok - Pattaya',
            'origin': 'Bangkok',
            'destination': 'Pattaya',
            'distance_km': 150.0,
        })
        # Create fleet vehicle with brand and model
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'TestBrand'})
        model = cls.env['fleet.vehicle.model'].create({
            'name': 'TestModel',
            'brand_id': brand.id,
        })
        cls.vehicle = cls.env['fleet.vehicle'].create({
            'license_plate': 'กข-1234',
            'model_id': model.id,
        })
        cls.employee = cls.env['hr.employee'].search([], limit=1)
        if not cls.employee:
            cls.employee = cls.env['hr.employee'].create({'name': 'Test Driver'})
        cls.stock_manager = new_test_user(
            cls.env,
            login='od19_transport_stock_manager',
            groups='stock.group_stock_manager',
        )

    def _create_transport_order(self, transport_cost=5000.0):
        return self.env['od19.transport.order'].create({
            'origin_location': 'Bangkok',
            'destination_location': 'Pattaya',
            'route_id': self.route.id,
            'vehicle_id': self.vehicle.id,
            'driver_id': self.employee.id,
            'distance_km': 150.0,
            'transport_cost': transport_cost,
        })

    def test_route_creation(self):
        """Route should be created with correct fields."""
        self.assertEqual(self.route.origin, 'Bangkok')
        self.assertEqual(self.route.destination, 'Pattaya')
        self.assertEqual(self.route.distance_km, 150.0)

    def test_transport_order_creation(self):
        """Transport order should be created in draft state."""
        order = self._create_transport_order()
        self.assertEqual(order.state, 'draft')
        self.assertTrue(order.name)

    def test_sequence_generation(self):
        """Transport orders should get unique sequence names."""
        order1 = self._create_transport_order()
        order2 = self._create_transport_order()
        self.assertNotEqual(order1.name, order2.name)

    def test_confirm_requires_vehicle(self):
        """Confirming without vehicle should raise error."""
        order = self._create_transport_order()
        order.vehicle_id = False
        with self.assertRaises(Exception):
            order.action_confirm()

    def test_confirm_requires_driver(self):
        """Confirming without driver should raise error."""
        order = self._create_transport_order()
        order.driver_id = False
        with self.assertRaises(Exception):
            order.action_confirm()

    def test_workflow_draft_to_delivered(self):
        """Full workflow: draft -> confirmed -> in_transit -> delivered."""
        order = self._create_transport_order()
        order.action_confirm()
        self.assertEqual(order.state, 'confirmed')
        order.action_start_transit()
        self.assertEqual(order.state, 'in_transit')
        self.assertTrue(order.departure_time)
        order.action_deliver()
        self.assertEqual(order.state, 'delivered')
        self.assertTrue(order.arrival_time)

    def test_start_transit_from_draft_raises(self):
        """Starting transit from draft should raise error."""
        order = self._create_transport_order()
        with self.assertRaises(Exception):
            order.action_start_transit()

    def test_deliver_from_confirmed_raises(self):
        """Delivering from confirmed (not in_transit) should raise error."""
        order = self._create_transport_order()
        order.action_confirm()
        with self.assertRaises(Exception):
            order.action_deliver()

    def test_cancel_delivered_raises(self):
        """Cancelling a delivered order should raise error."""
        order = self._create_transport_order()
        order.action_confirm()
        order.action_start_transit()
        order.action_deliver()
        with self.assertRaises(Exception):
            order.action_cancel()

    def test_tier_definition_model_names_include_transport_order(self):
        names = self.env['tier.definition']._get_tier_validation_model_names()
        self.assertIn('od19.transport.order', names)

    def test_low_cost_confirms_without_approval(self):
        """Orders below the approval threshold confirm directly."""
        order = self._create_transport_order(transport_cost=5000.0)
        self.assertFalse(order.need_validation)
        order.action_confirm()
        self.assertEqual(order.state, 'confirmed')

    def test_high_cost_requires_approval(self):
        """Orders above the threshold route to waiting approval."""
        order = self._create_transport_order(transport_cost=100000.0)
        self.assertTrue(order.need_validation)
        order.action_confirm()
        self.assertEqual(order.state, 'waiting_approval')
        self.assertTrue(order.review_ids)
        self.assertIn(order.validation_status, ('pending', 'waiting'))

    def test_cannot_confirm_before_approval(self):
        """Confirming a waiting order before validation must raise."""
        order = self._create_transport_order(transport_cost=100000.0)
        order.action_confirm()
        self.assertEqual(order.state, 'waiting_approval')
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_manager_approval_allows_confirm(self):
        """After the stock manager validates, the order can be confirmed."""
        order = self._create_transport_order(transport_cost=100000.0)
        order.action_confirm()
        self.assertEqual(order.state, 'waiting_approval')
        order.with_user(self.stock_manager).validate_tier()
        self.assertEqual(order.validation_status, 'validated')
        order.action_confirm()
        self.assertEqual(order.state, 'confirmed')
