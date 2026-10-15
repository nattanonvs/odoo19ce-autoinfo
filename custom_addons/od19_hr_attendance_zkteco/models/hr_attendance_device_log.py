# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class HrAttendanceDeviceLog(models.Model):
    _name = 'hr.attendance.device.log'
    _description = 'Attendance Device Punch Log (ZKTeco)'
    _order = 'punch_time desc, id desc'

    device_id = fields.Many2one(
        'hr.attendance.device',
        string="Device",
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='device_id.company_id',
        store=True,
        index=True,
    )
    employee_identifier = fields.Char(
        string="Device ID",
        required=True,
        index=True,
        help="Raw PIN / Badge ID read from the device.",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        ondelete='set null',
        index=True,
    )
    punch_time = fields.Datetime(
        string="Punch Time",
        required=True,
        index=True,
    )
    punch_type = fields.Selection(
        selection=[
            ('0', 'Check In'),
            ('1', 'Check Out'),
            ('2', 'Break Out'),
            ('3', 'Break In'),
            ('4', 'Overtime In'),
            ('5', 'Overtime Out'),
            ('255', 'Unknown'),
        ],
        string="Punch Type",
        default='255',
    )
    verify_type = fields.Selection(
        selection=[
            ('1', 'Fingerprint'),
            ('2', 'Password'),
            ('3', 'Card'),
            ('4', 'Face'),
            ('15', 'Face'),
            ('255', 'Other'),
        ],
        string="Verification Mode",
        default='255',
    )
    work_code = fields.Char(string="Work Code")
    state = fields.Selection(
        selection=[
            ('draft', 'To Process'),
            ('processed', 'Processed'),
            ('duplicate', 'Duplicate'),
            ('no_employee', 'Employee Not Found'),
            ('error', 'Error'),
        ],
        string="Status",
        default='draft',
        required=True,
        index=True,
    )
    error_message = fields.Text(string="Error Detail", readonly=True)
    attendance_id = fields.Many2one(
        'hr.attendance',
        string="Attendance",
        ondelete='set null',
        readonly=True,
    )
    raw_data = fields.Text(string="Raw Data", readonly=True)

    _log_uniq = models.Constraint(
        'unique(device_id, employee_identifier, punch_time)',
        'This punch already exists for this device.',
    )

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def action_process(self):
        """Process the selected punches again (button)."""
        self._process()
        return True

    def _process(self):
        for log in self:
            log._process_one()
        return True

    def _process_one(self):
        self.ensure_one()
        if self.state not in ('draft', 'error', 'no_employee'):
            return
        employee = self._find_employee()
        if not employee:
            match_field = self.company_id.od19_zkteco_match_field or 'barcode'
            self.write({
                'state': 'no_employee',
                'error_message': _(
                    "No employee found with %(field)s = %(value)s.",
                    field=match_field,
                    value=self.employee_identifier,
                ),
            })
            return
        attendance, state, message = self._pair_attendance(employee)
        self.write({
            'employee_id': employee.id,
            'attendance_id': attendance.id if attendance else False,
            'state': state,
            'error_message': message or False,
        })

    def _find_employee(self):
        """Match an employee using the configured company match field."""
        self.ensure_one()
        match_field = self.company_id.od19_zkteco_match_field or 'barcode'
        if match_field not in ('barcode', 'pin'):
            match_field = 'barcode'
        employee = self.env['hr.employee'].sudo().search([
            (match_field, '=', self.employee_identifier),
            ('company_id', 'in', [False, self.company_id.id]),
        ], limit=1)
        return employee

    def _pair_attendance(self, employee):
        """Create or close an attendance for the given punch.

        Returns a tuple (attendance, state, message).
        """
        self.ensure_one()
        Attendance = self.env['hr.attendance'].sudo()
        open_attendance = Attendance.search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], order='check_in desc', limit=1)
        try:
            if open_attendance:
                grace = timedelta(
                    minutes=self.company_id.od19_zkteco_grace_minutes or 0)
                if self.punch_time <= open_attendance.check_in + grace:
                    return open_attendance, 'duplicate', _(
                        "Punch ignored: within the check-out grace period.")
                open_attendance.write({
                    'check_out': self.punch_time,
                    'out_mode': 'technical',
                })
                return open_attendance, 'processed', False
            attendance = Attendance.create({
                'employee_id': employee.id,
                'check_in': self.punch_time,
                'in_mode': 'technical',
                'out_mode': 'technical',
            })
            return attendance, 'processed', False
        except ValidationError as error:
            return False, 'error', str(error)

    @api.model
    def _cron_process_pending_logs(self):
        """Safety-net cron: process any punch that is still pending."""
        pending = self.search([('state', '=', 'draft')], limit=2000)
        if pending:
            _logger.info("ZKTeco: processing %s pending punch(es).", len(pending))
            pending._process()
        return True
