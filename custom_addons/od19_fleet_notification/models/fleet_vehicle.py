import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    od19_insurance_expire_date = fields.Date(
        string='Insurance Expiry Date / วันที่หมดอายุประกัน',
        tracking=True,
        help='Date when the vehicle insurance expires.',
    )
    od19_act_expire_date = fields.Date(
        string='Act Expiry Date / วันที่หมดอายุภาษี (Act)',
        tracking=True,
        help='Date when the vehicle Act (tax) expires.',
    )
    od19_insurance_reminder_days = fields.Integer(
        string='Insurance Reminder Days',
        default=30,
        help='Number of days before insurance expiry to send a reminder.',
    )
    od19_act_reminder_days = fields.Integer(
        string='Act Reminder Days',
        default=30,
        help='Number of days before Act expiry to send a reminder.',
    )

    # ------------------------------------------------------------------
    # Expiry notification cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_send_expiry_notifications(self):
        """Find vehicles with insurance/Act expiring soon or expired and notify
        fleet managers.

        Uses ``notification.service`` (from ``od19_notification_multi_channel)
        when available, otherwise falls back to ``mail.template`` + ``mail.mail``.
        """
        today = fields.Date.context_today(self)
        vehicles = self.search([
            '|',
            ('od19_insurance_expire_date', '!=', False),
            ('od19_act_expire_date', '!=', False),
        ])

        lines = []
        for vehicle in vehicles:
            ins_date = vehicle.od19_insurance_expire_date
            act_date = vehicle.od19_act_expire_date

            if ins_date:
                ins_days = (ins_date - today).days
                ins_reminder = vehicle.od19_insurance_reminder_days or 30
                if ins_days <= ins_reminder:
                    lines.append({
                        'vehicle': vehicle,
                        'type': _('Insurance'),
                        'expiry_date': ins_date,
                        'days_remaining': ins_days,
                    })

            if act_date:
                act_days = (act_date - today).days
                act_reminder = vehicle.od19_act_reminder_days or 30
                if act_days <= act_reminder:
                    lines.append({
                        'vehicle': vehicle,
                        'type': _('Act'),
                        'expiry_date': act_date,
                        'days_remaining': act_days,
                    })

        if not lines:
            _logger.info('Fleet expiry notification: no vehicles due for reminder.')
            return

        recipients = self._get_expiry_notification_recipients()
        if not recipients:
            _logger.warning(
                'Fleet expiry notification: no recipients found '
                '(no fleet managers and no configured recipient).')
            return

        message = self._build_expiry_notification_message(lines)
        subject = _('Fleet Insurance / Act Expiry Reminder')

        if 'notification.service' in self.env:
            self.env['notification.service'].notify(
                recipients,
                message,
                event='fleet_expiry',
                subject=subject,
            )
        else:
            self._send_expiry_email_fallback(recipients, lines, subject)

    @api.model
    def _get_expiry_notification_recipients(self):
        """Return a ``res.partner`` recordset of notification recipients.

        Prefers users in the ``fleet.fleet_group_manager`` group. Falls back to
        a company-level configurable recipient if set (see ``res.company``).
        """
        manager_group = self.env.ref('fleet.fleet_group_manager', raise_if_not_found=False)
        partners = self.env['res.partner']
        if manager_group:
            users = self.env['res.users'].search([
                ('group_ids', 'in', manager_group.id),
                ('share', '=', False),
            ])
            partners = users.mapped('partner_id')

        # Optional company-level override recipient
        company = self.env.company
        override = getattr(company, 'od19_fleet_notification_recipient_id', False)
        if override:
            partners |= override

        return partners

    @api.model
    def _build_expiry_lines(self, lines):
        """Build a list of plain dicts suitable for the QWeb mail template."""
        result = []
        for line in sorted(lines, key=lambda l: (l['days_remaining'], l['vehicle'].name or '')):
            vehicle = line['vehicle']
            days = line['days_remaining']
            if days < 0:
                status = _('EXPIRED %s day(s) ago') % abs(days)
            elif days == 0:
                status = _('expires today')
            else:
                status = _('%s day(s) remaining') % days
            result.append({
                'vehicle_name': vehicle.name or _('Vehicle'),
                'plate': vehicle.license_plate or _('No Plate'),
                'type': line['type'],
                'expiry_date': str(line['expiry_date']),
                'days_remaining': days,
                'status': status,
            })
        return result

    @api.model
    def _build_expiry_notification_message(self, lines):
        """Build a plain-text summary message for the expiry notification."""
        rows = []
        for line in self._build_expiry_lines(lines):
            rows.append(
                '- %s (%s) | %s | %s | %s' % (
                    line['vehicle_name'],
                    line['plate'],
                    line['type'],
                    line['expiry_date'],
                    line['status'],
                )
            )
        header = _('The following fleet vehicles have insurance/Act expiring soon or already expired:')
        return '%s\n\n%s' % (header, '\n'.join(rows))

    @api.model
    def _send_expiry_email_fallback(self, recipients, lines, subject):
        """Send the expiry notification email via ``mail.template`` when
        ``od19_notification_multi_channel`` is not installed."""
        template = self.env.ref(
            'od19_fleet_notification.mail_template_fleet_expiry_notification',
            raise_if_not_found=False,
        )
        expiry_lines = self._build_expiry_lines(lines)
        for partner in recipients:
            if not partner.email:
                continue
            if template:
                template.with_context(expiry_lines=expiry_lines).send_mail(
                    partner.id,
                    force_send=False,
                    email_values={'subject': subject},
                )
            else:
                # Last-resort fallback if the template was deleted
                self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': '<p>%s</p><pre>%s</pre>' % (
                        subject,
                        self._build_expiry_notification_message(lines),
                    ),
                    'email_to': partner.email,
                    'auto_delete': True,
                }).send()
