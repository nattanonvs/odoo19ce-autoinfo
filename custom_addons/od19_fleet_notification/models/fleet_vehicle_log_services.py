import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    od19_service_done_notified = fields.Boolean(
        string='Service Done Notified',
        default=False,
        help='Whether the "service done" notification has already been sent.',
    )

    def write(self, vals):
        """Detect state transition to ``done`` and send a notification to the
        vehicle's responsible user and driver."""
        res = super().write(vals)
        if vals.get('state') == 'done':
            for record in self:
                if not record.od19_service_done_notified:
                    record._notify_service_done()
                    record.od19_service_done_notified = True
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if vals.get('state') == 'done' and not record.od19_service_done_notified:
                record._notify_service_done()
                record.od19_service_done_notified = True
        return records

    def _notify_service_done(self):
        """Send a "service done" notification to the vehicle's manager and
        driver. Uses ``notification.service`` when available, otherwise falls
        back to ``mail.template`` and a chatter post."""
        self.ensure_one()
        vehicle = self.vehicle_id
        if not vehicle:
            return

        recipients = self._get_service_done_recipients()
        if not recipients:
            _logger.info(
                'Service done notification skipped for service %s: '
                'no recipients (no manager / driver).', self.id)
            return

        message = self._build_service_done_message()
        subject = _('Service Done: %s') % (vehicle.name or _('Vehicle'))
        ctx = self._build_service_done_context()

        if 'notification.service' in self.env:
            self.env['notification.service'].notify(
                recipients,
                message,
                event='fleet_service_done',
                subject=subject,
            )
        else:
            template = self.env.ref(
                'od19_fleet_notification.mail_template_fleet_service_done',
                raise_if_not_found=False,
            )
            for partner in recipients:
                if not partner.email:
                    continue
                if template:
                    template.with_context(**ctx).send_mail(
                        partner.id,
                        force_send=False,
                        email_values={'subject': subject},
                    )
                else:
                    self.env['mail.mail'].sudo().create({
                        'subject': subject,
                        'body_html': '<p>%s</p>' % message.replace('\n', '<br/>'),
                        'email_to': partner.email,
                        'auto_delete': True,
                    }).send()

        # Always log the notification on the service log chatter for traceability
        self.message_post(
            body='<p>%s</p>' % message.replace('\n', '<br/>'),
            subject=subject,
            subtype_xmlid='mail.mt_comment',
        )

    def _build_service_done_context(self):
        """Build the QWeb context dict for the service-done mail template."""
        self.ensure_one()
        vehicle = self.vehicle_id
        return {
            'vehicle_name': vehicle.name or _('Vehicle'),
            'plate': vehicle.license_plate or _('No Plate'),
            'service_type': self.service_type_id.name if self.service_type_id else _('Service'),
            'date': str(self.date or fields.Date.context_today(self)),
            'amount': self.amount or 0.0,
            'description': self.description or '',
        }

    def _get_service_done_recipients(self):
        """Return the partners to notify when a service is done: the vehicle's
        fleet manager and driver."""
        self.ensure_one()
        vehicle = self.vehicle_id
        partners = self.env['res.partner']
        if vehicle.manager_id:
            partners |= vehicle.manager_id.partner_id
        if vehicle.driver_id:
            partners |= vehicle.driver_id
        return partners

    def _build_service_done_message(self):
        self.ensure_one()
        vehicle = self.vehicle_id
        plate = vehicle.license_plate or _('No Plate')
        service_type = self.service_type_id.name if self.service_type_id else _('Service')
        amount = self.amount or 0.0
        date = self.date or fields.Date.context_today(self)
        description = self.description or ''

        lines = [
            _('Vehicle: %s (%s)') % (vehicle.name or _('Vehicle'), plate),
            _('Service Type: %s') % service_type,
            _('Date: %s') % date,
            _('Cost: %s') % amount,
        ]
        if description:
            lines.append(_('Description: %s') % description)
        return _('A service has been completed for your vehicle.') + '\n\n' + '\n'.join(lines)
