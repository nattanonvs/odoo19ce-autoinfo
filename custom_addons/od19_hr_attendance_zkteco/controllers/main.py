# -*- coding: utf-8 -*-

import logging

import pytz

from odoo import _, fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ZKTecoController(http.Controller):
    """Endpoints consumed by ZKTeco ADMS / iClock compatible terminals.

    The device is configured with the Odoo host/port as "Cloud Server" and
    pushes its attendance records to ``/iclock/cdata``. It also polls
    ``/iclock/getrequest`` for pending commands and ``/iclock/ping`` to keep
    the session alive.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _plain(self, content):
        return request.make_response(
            content,
            headers=[('Content-Type', 'text/plain; charset=utf-8')],
        )

    def _get_device(self, sn, auto_create=True):
        if not sn:
            return request.env['hr.attendance.device'].sudo().browse()
        Device = request.env['hr.attendance.device'].sudo()
        device = Device._get_device_by_serial(sn)
        if not device and auto_create:
            company = request.env.company
            if company.od19_zkteco_enabled:
                device = Device.create({
                    'name': _("ZKTeco %s", sn),
                    'serial_number': sn,
                    'company_id': company.id,
                })
                _logger.info("ZKTeco: auto-registered device with SN %s", sn)
        return device

    def _check_comm_key(self, device, provided_key):
        if not device or not device.comm_key:
            return True
        if not provided_key:
            return True
        return device.comm_key == provided_key

    def _handshake_body(self, sn, device):
        tz_offset = 7  # default Asia/Bangkok
        tz_name = device.company_id.partner_id.tz if device else None
        if tz_name:
            try:
                tz_offset = int(pytz.timezone(tz_name).utcoffset(
                    fields.Datetime.now()).total_seconds() // 3600)
            except pytz.UnknownTimeZoneError:
                pass
        return (
            "GET OPTION FROM: %(sn)s\n"
            "Stamp=9999\n"
            "OpStamp=9999\n"
            "ErrorDelay=30\n"
            "Delay=10\n"
            "TransTimes=00:00;14:05\n"
            "TransInterval=1\n"
            "TransFlag=1111000000\n"
            "TimeZone=%(tz)s\n"
            "Realtime=1\n"
            "Encrypt=0\n"
            % {'sn': sn, 'tz': tz_offset}
        )

    def _to_utc(self, dt_str, device):
        """Convert a device local timestamp to a naive UTC datetime."""
        try:
            naive = fields.Datetime.to_datetime(dt_str)
        except (ValueError, TypeError):
            return False
        if not naive:
            return False
        tz_name = (device.company_id.partner_id.tz
                   or request.env.user.tz
                   or 'UTC')
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            tz = pytz.utc
        return tz.localize(naive).astimezone(pytz.utc).replace(tzinfo=None)

    def _store_punches(self, device, body):
        """Parse a tab separated ATTLOG payload and store raw punch logs."""
        Log = request.env['hr.attendance.device.log'].sudo()
        created = 0
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            identifier = parts[0].strip()
            punch_time = self._to_utc(parts[1].strip(), device)
            if not identifier or not punch_time:
                continue
            values = {
                'device_id': device.id,
                'employee_identifier': identifier,
                'punch_time': punch_time,
                'punch_type': parts[2].strip() if len(parts) > 2 else '255',
                'verify_type': parts[3].strip() if len(parts) > 3 else '255',
                'work_code': parts[4].strip() if len(parts) > 4 else False,
                'raw_data': line,
            }
            existing = Log.search([
                ('device_id', '=', device.id),
                ('employee_identifier', '=', identifier),
                ('punch_time', '=', punch_time),
            ], limit=1)
            if existing:
                continue
            log = Log.create(values)
            created += 1
            if device.company_id.od19_zkteco_auto_process:
                log._process()
        return created

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------
    @http.route('/iclock/cdata', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_cdata(self, SN=None, options=None, table=None, Stamp=None,
                     key=None, **kwargs):
        device = self._get_device(SN)
        if not device:
            _logger.warning("ZKTeco: unknown device SN=%s on /iclock/cdata", SN)
            return self._plain("OK")

        if not self._check_comm_key(device, key):
            _logger.warning("ZKTeco: invalid comm key for device %s", SN)
            return self._plain("ERROR")

        device._touch()

        if request.httprequest.method == 'GET':
            # Handshake: the device asks for its configuration.
            return self._plain(self._handshake_body(SN, device))

        # POST: data upload (ATTLOG / OPERLOG / ATTPHOTO ...)
        body = request.httprequest.get_data(as_text=True) or ''
        if table == 'ATTLOG':
            created = self._store_punches(device, body)
            _logger.info("ZKTeco: %s punch(es) stored from device %s",
                         created, SN)
            return self._plain("OK: %s" % created)
        # Other tables (OPERLOG, ATTPHOTO, ...) are acknowledged only.
        return self._plain("OK: 0")

    @http.route('/iclock/getrequest', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_getrequest(self, SN=None, **kwargs):
        device = self._get_device(SN)
        if device:
            device._touch()
        # No server-side command queue implemented: tell the device there is
        # nothing to do.
        return self._plain("OK")

    @http.route('/iclock/ping', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_ping(self, SN=None, **kwargs):
        device = self._get_device(SN)
        if device:
            device._touch()
        return self._plain("OK")

    @http.route('/iclock/devicecmd', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_devicecmd(self, SN=None, **kwargs):
        device = self._get_device(SN)
        if device:
            device._touch()
        return self._plain("OK")

    @http.route('/iclock/test', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_test(self, SN=None, **kwargs):
        return self._plain("OK")
