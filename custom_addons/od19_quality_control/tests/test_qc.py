# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestQcInspection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Supplier',
        })

    def test_qty_rejected_computation(self):
        """Rejected quantity should be tested - accepted."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 10.0,
            'qty_accepted': 8.0,
        })
        self.assertEqual(inspection.qty_rejected, 2.0)

    def test_result_pass_when_all_lines_pass(self):
        """Result should be pass when all inspection lines pass."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 5.0,
            'qty_accepted': 5.0,
            'line_ids': [
                (0, 0, {'parameter': 'Color', 'expected_value': 'Red', 'actual_value': 'Red'}),
                (0, 0, {'parameter': 'Size', 'expected_value': 'M', 'actual_value': 'M'}),
            ],
        })
        self.assertEqual(inspection.result, 'pass')

    def test_result_fail_when_any_line_fails(self):
        """Result should be fail when any inspection line fails."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 5.0,
            'qty_accepted': 5.0,
            'line_ids': [
                (0, 0, {'parameter': 'Color', 'expected_value': 'Red', 'actual_value': 'Blue'}),
            ],
        })
        self.assertEqual(inspection.result, 'fail')

    def test_line_result_pass(self):
        """Line result should be pass when expected matches actual."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'line_ids': [
                (0, 0, {'parameter': 'Weight', 'expected_value': '100g', 'actual_value': '100g'}),
            ],
        })
        self.assertEqual(inspection.line_ids.result, 'pass')

    def test_line_result_fail(self):
        """Line result should be fail when expected doesn't match actual."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'line_ids': [
                (0, 0, {'parameter': 'Weight', 'expected_value': '100g', 'actual_value': '150g'}),
            ],
        })
        self.assertEqual(inspection.line_ids.result, 'fail')

    def test_inspection_workflow_pass(self):
        """Inspection should follow draft -> in_progress -> passed."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 5.0,
            'qty_accepted': 5.0,
        })
        self.assertEqual(inspection.state, 'draft')

        inspection.action_start()
        self.assertEqual(inspection.state, 'in_progress')

        inspection.action_pass()
        self.assertEqual(inspection.state, 'passed')

    def test_inspection_workflow_fail(self):
        """Inspection can be marked as failed."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'outgoing',
            'qty_tested': 5.0,
            'qty_accepted': 2.0,
        })
        inspection.action_fail()
        self.assertEqual(inspection.state, 'failed')

    def test_inspection_sequence(self):
        """Inspection name should be generated from sequence."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
        })
        self.assertTrue(inspection.name.startswith('QC/'))

    def test_inspection_cancel(self):
        """Inspection can be cancelled from draft."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
        })
        inspection.action_cancel()
        self.assertEqual(inspection.state, 'cancelled')

    def test_create_nonconformity_from_failed_inspection(self):
        """A failed inspection can raise a linked ISO nonconformity."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 5.0,
            'qty_accepted': 2.0,
        })
        inspection.action_fail()
        self.assertEqual(inspection.result, 'fail')
        inspection.action_create_nonconformity()
        self.assertTrue(inspection.nc_id)
        self.assertEqual(inspection.nc_id.category, 'quality')
        self.assertEqual(inspection.nc_id.source, 'incoming')

    def test_create_nonconformity_skips_when_already_linked(self):
        """Calling the action twice does not create a second nonconformity."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 5.0,
            'qty_accepted': 2.0,
        })
        inspection.action_create_nonconformity()
        nc = inspection.nc_id
        inspection.action_create_nonconformity()
        self.assertEqual(inspection.nc_id, nc)

    def test_create_nonconformity_from_passed_inspection_raises(self):
        """A passed inspection cannot raise a nonconformity."""
        inspection = self.env['od19.qc.inspection'].create({
            'product_id': self.product.id,
            'partner_id': self.partner.id,
            'inspection_type': 'incoming',
            'qty_tested': 5.0,
            'qty_accepted': 5.0,
        })
        with self.assertRaises(Exception):
            inspection.action_create_nonconformity()
