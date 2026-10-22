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

    @staticmethod
    def _key_matches(expected_key, provided_key):
        """Return True only when a key is configured and the values match.

        Fail-closed: when no key is configured (``expected_key`` is empty)
        the request is refused, so an administrator must set a shared
        communication key before any terminal is accepted.
        """
        if not expected_key:
            return False
        return bool(provided_key) and provided_key == expected_key

    def _authorize(self, sn, key, auto_create=True):
        """Resolve and authenticate the device that issued the request.

        A request is accepted only when the device is known and the
        communication key (device level first, then company level) matches
        the value sent by the terminal. Unknown serial numbers are rejected
        unless auto-registration is explicitly enabled *and* the company key
        matches.

        :param sn: serial number reported by the device (``SN`` parameter).
        :param key: communication key sent by the device (``key`` parameter).
        :param auto_create: allow registering an unknown but authenticated
                            device on the fly.
        :return: the ``hr.attendance.device`` record, or ``None`` when the
                 request must be refused.
        """
        if not sn:
            _logger.warning("ZKTeco: request without SN; refused.")
            return None
        Device = request.env['hr.attendance.device'].sudo()
        device = Device._get_device_by_serial(sn)
        if device:
            if not device.active:
                _logger.warning("ZKTeco: archived device SN=%s; refused.", sn)
                return None
            expected_key = device.comm_key or device.company_id.od19_zkteco_comm_key
            if not self._key_matches(expected_key, key):
                _logger.warning(
                    "ZKTeco: invalid or missing key for device SN=%s; refused.",
                    sn,
                )
                return None
        else:
            company = request.env.company
            may_register = (
                auto_create
                and company.od19_zkteco_enabled
                and company.od19_zkteco_allow_auto_register
                and self._key_matches(company.od19_zkteco_comm_key, key)
            )
            if not may_register:
                _logger.warning(
                    "ZKTeco: unknown device SN=%s; refused.", sn,
                )
                return None
            device = Device.create({
                'name': _("ZKTeco %s", sn),
                'serial_number': sn,
                'company_id': company.id,
            })
            _logger.info("ZKTeco: auto-registered device with SN %s", sn)
        device._touch()
        return device

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
        # ``csrf=False`` is required: ZKTeco terminals cannot send a CSRF
        # token. Authentication is enforced through the communication key
        # validated in ``_authorize`` (fail-closed).
        device = self._authorize(SN, key)
        if not device:
            return self._plain("ERROR")

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
    def iclock_getrequest(self, SN=None, key=None, **kwargs):
        # Only a device that already completed the handshake may poll.
        if not self._authorize(SN, key, auto_create=False):
            return self._plain("ERROR")
        # No server-side command queue implemented: tell the device there is
        # nothing to do.
        return self._plain("OK")

    @http.route('/iclock/ping', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_ping(self, SN=None, key=None, **kwargs):
        if not self._authorize(SN, key, auto_create=False):
            return self._plain("ERROR")
        return self._plain("OK")

    @http.route('/iclock/devicecmd', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_devicecmd(self, SN=None, key=None, **kwargs):
        if not self._authorize(SN, key, auto_create=False):
            return self._plain("ERROR")
        return self._plain("OK")

    @http.route('/iclock/test', type='http', auth='public', csrf=False,
                methods=['GET', 'POST'], save_session=False)
    def iclock_test(self, SN=None, key=None, **kwargs):
        # Connectivity probe only: no data is read or written.
        return self._plain("OK")
