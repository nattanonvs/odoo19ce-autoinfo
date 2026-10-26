# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase
from odoo.tools import mute_logger

# The controller logs a warning whenever it refuses a terminal. Two tests below
# exercise those refusals on purpose, so the warning is expected output there.
CONTROLLER_LOGGER = 'odoo.addons.od19_hr_attendance_zkteco.controllers.main'

# A duplicate serial number makes PostgreSQL raise a unique violation, which the
# Odoo cursor reports through ``odoo.sql_db`` before the exception propagates.
# The test below asserts that behaviour on purpose.
SQL_LOGGER = 'odoo.sql_db'


@tagged('post_install', '-at_install', 'od19_zkteco')
class TestZKTecoPunch(TransactionCase):
    """Business-logic tests for the ZKTeco punch processing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            'od19_zkteco_enabled': True,
            'od19_zkteco_match_field': 'barcode',
            'od19_zkteco_grace_minutes': 0,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'ZKTeco Test Employee',
            'barcode': 'ZK-0001',
            'pin': '4321',
            'company_id': cls.company.id,
        })
        cls.device = cls.env['hr.attendance.device'].create({
            'name': 'Test Terminal',
            'serial_number': 'TEST-SN-001',
            'company_id': cls.company.id,
        })

    def _make_log(self, identifier, punch_time, **kwargs):
        vals = {
            'device_id': self.device.id,
            'employee_identifier': identifier,
            'punch_time': punch_time,
        }
        vals.update(kwargs)
        return self.env['hr.attendance.device.log'].create(vals)

    @mute_logger(SQL_LOGGER)
    def test_serial_number_is_unique(self):
        with self.assertRaises(Exception):
            self.env['hr.attendance.device'].create({
                'name': 'Duplicate',
                'serial_number': 'TEST-SN-001',
                'company_id': self.company.id,
            })

    def test_get_device_by_serial(self):
        device = self.env['hr.attendance.device']._get_device_by_serial('TEST-SN-001')
        self.assertEqual(device, self.device)
        self.assertFalse(
            self.env['hr.attendance.device']._get_device_by_serial('UNKNOWN'))

    def test_punch_creates_then_closes_attendance(self):
        log_in = self._make_log('ZK-0001', '2026-10-15 01:00:00')
        log_in._process()
        self.assertEqual(log_in.state, 'processed')
        self.assertEqual(log_in.employee_id, self.employee)
        attendance = log_in.attendance_id
        self.assertTrue(attendance)
        self.assertFalse(attendance.check_out)
        self.assertEqual(attendance.in_mode, 'technical')

        log_out = self._make_log('ZK-0001', '2026-10-15 10:00:00')
        log_out._process()
        self.assertEqual(log_out.state, 'processed')
        self.assertEqual(log_out.attendance_id, attendance)
        self.assertTrue(attendance.check_out)
        self.assertEqual(attendance.out_mode, 'technical')

    def test_employee_not_found(self):
        log = self._make_log('UNKNOWN-ID', '2026-10-15 01:00:00')
        log._process()
        self.assertEqual(log.state, 'no_employee')
        self.assertFalse(log.employee_id)

    def test_duplicate_punch_within_grace_is_ignored(self):
        self.company.od19_zkteco_grace_minutes = 5
        log_in = self._make_log('ZK-0001', '2026-10-15 01:00:00')
        log_in._process()
        log_dup = self._make_log('ZK-0001', '2026-10-15 01:03:00')
        log_dup._process()
        self.assertEqual(log_dup.state, 'duplicate')
        self.assertFalse(log_in.attendance_id.check_out)

    def test_pin_match_field(self):
        self.company.od19_zkteco_match_field = 'pin'
        log = self._make_log('4321', '2026-10-15 02:00:00')
        log._process()
        self.assertEqual(log.state, 'processed')
        self.assertEqual(log.employee_id, self.employee)

    def test_cron_processes_pending_logs(self):
        self._make_log('ZK-0001', '2026-10-15 03:00:00')
        self.env['hr.attendance.device.log']._cron_process_pending_logs()
        pending = self.env['hr.attendance.device.log'].search([
            ('state', '=', 'draft')])
        self.assertFalse(pending)


@tagged('post_install', '-at_install', 'od19_zkteco')
class TestZKTecoController(HttpCase):
    """HTTP contract of the ADMS / iClock endpoints (fail-closed auth)."""

    KEY = 'ZK-KEY-123'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({
            'od19_zkteco_enabled': True,
            'od19_zkteco_comm_key': cls.KEY,
        })
        cls.device = cls.env['hr.attendance.device'].create({
            'name': 'HTTP Test Terminal',
            'serial_number': 'HTTP-SN-001',
            'company_id': cls.company.id,
        })

    @mute_logger(CONTROLLER_LOGGER)
    def test_cdata_without_key_is_refused(self):
        response = self.url_open(
            '/iclock/cdata?SN=HTTP-SN-001&options=all', timeout=60)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.strip(), 'ERROR')

    def test_cdata_handshake(self):
        response = self.url_open(
            '/iclock/cdata?SN=HTTP-SN-001&options=all&key=%s' % self.KEY,
            timeout=60,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('GET OPTION FROM: HTTP-SN-001', response.text)

    def test_cdata_attlog_upload(self):
        payload = '1001\t2026-10-15 08:30:12\t0\t1\t0\t0\t0\n'
        response = self.url_open(
            '/iclock/cdata?SN=HTTP-SN-001&table=ATTLOG&Stamp=1&key=%s'
            % self.KEY,
            data=payload,
            timeout=60,
            headers={'Content-Type': 'text/plain'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.text.startswith('OK'))

    def test_ping_and_getrequest(self):
        for url in ('/iclock/ping?SN=HTTP-SN-001&key=%s' % self.KEY,
                    '/iclock/getrequest?SN=HTTP-SN-001&key=%s' % self.KEY):
            response = self.url_open(url, timeout=60)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.text.strip(), 'OK')

    @mute_logger(CONTROLLER_LOGGER)
    def test_ping_refuses_unknown_device(self):
        response = self.url_open(
            '/iclock/ping?SN=UNKNOWN-SN&key=%s' % self.KEY, timeout=60)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text.strip(), 'ERROR')

