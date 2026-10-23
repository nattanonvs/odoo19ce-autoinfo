# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HrAttendanceDevice(models.Model):
    _name = 'hr.attendance.device'
    _description = 'Attendance Device (ZKTeco)'
    _order = 'name'

    name = fields.Char(
        string="Device Name",
        required=True,
    )
    serial_number = fields.Char(
        string="Serial Number",
        required=True,
        index=True,
        help="Serial number reported by the device (SN parameter).",
    )
    device_model = fields.Char(string="Model")
    firmware_version = fields.Char(string="Firmware Version")
    device_ip = fields.Char(string="Device IP")
    comm_key = fields.Char(
        string="Communication Key",
        help="Device-level communication key. When left empty, the "
             "company-level key from Attendance settings is used instead. "
             "The terminal must send the matching key or the request is "
             "refused.",
    )
    location = fields.Char(
        string="Location",
        help="Where the terminal is physically installed.",
    )
    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)
    last_activity = fields.Datetime(
        string="Last Activity",
        readonly=True,
    )
    log_ids = fields.One2many(
        'hr.attendance.device.log',
        'device_id',
        string="Punch Logs",
    )
    log_count = fields.Integer(
        string="Punch Count",
        compute='_compute_log_count',
    )
    state = fields.Selection(
        selection=[
            ('online', 'Online'),
            ('offline', 'Offline'),
        ],
        string="Status",
        compute='_compute_state',
        search='_search_state',
    )

    _serial_number_uniq = models.Constraint(
        'unique(serial_number)',
        'The device serial number must be unique.',
    )

    @api.depends('log_ids')
    def _compute_log_count(self):
        for device in self:
            device.log_count = len(device.log_ids)

    @api.depends('last_activity')
    def _compute_state(self):
        now = fields.Datetime.now()
        for device in self:
            if device.last_activity and (now - device.last_activity).total_seconds() < 300:
                device.state = 'online'
            else:
                device.state = 'offline'

    @api.model
    def _search_state(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError(_("Unsupported operator for device state."))
        if isinstance(value, (list, tuple)):
            value = value[0]
        threshold = fields.Datetime.to_string(
            fields.Datetime.now() - timedelta(minutes=5))
        is_online = (value == 'online')
        if operator == '!=':
            is_online = not is_online
        if is_online:
            return [('last_activity', '>=', threshold)]
        return ['|', ('last_activity', '=', False),
                ('last_activity', '<', threshold)]

    @api.model
    def _get_device_by_serial(self, serial_number):
        """Return the device matching the given serial number, if any."""
        if not serial_number:
            return self.browse()
        return self.sudo().search([('serial_number', '=', serial_number)], limit=1)

    def _touch(self):
        """Record device activity (used as a lightweight heartbeat)."""
        self.sudo().write({'last_activity': fields.Datetime.now()})

    def action_view_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Punch Logs'),
            'res_model': 'hr.attendance.device.log',
            'view_mode': 'list,form',
            'domain': [('device_id', '=', self.id)],
            'context': {'default_device_id': self.id},
        }

    def action_process_logs(self):
        """Manually process every pending punch of this device."""
        logs = self.env['hr.attendance.device.log'].search([
            ('device_id', 'in', self.ids),
            ('state', '=', 'draft'),
        ])
        logs._process()
        return True
