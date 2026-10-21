import json
import logging
from urllib.parse import urljoin

import requests

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"


class NotificationService(models.AbstractModel):
    """Abstract service for dispatching notifications across multiple channels.

    Other modules call ``self.env['notification.service'].notify(...)`` to send
    a single message to Email, Odoo Inbox, and LINE simultaneously, according
    to each recipient's notification preference.
    """

    _name = "notification.service"
    _description = "Notification Multi-Channel Service"

    @api.model
    def notify(self, partners, message, event="default", subject=None, subtype_xmlid=None):
        """Queue ``message`` for ``partners`` across their preferred channels.

        Messages are stored in the notification queue and dispatched by the
        ``_cron_process_queue`` cron job. Failed sends are retried up to 3 times.

        :param partners: res.partner recordset (recipients)
        :param message: plain-text message body
        :param event: notification event key (see notification.preference)
        :param subject: optional email subject
        :param subtype_xmlid: optional mail.message subtype external id
                              (e.g. ``mail.mt_comment``) for Odoo inbox
        """
        if not partners or not message:
            return
        partners = partners.filtered("active") if "active" in partners._fields else partners
        if not partners:
            return

        Queue = self.env["od19.notification.queue"]
        for partner in partners:
            user = partner.user_ids[:1]
            channels = self._get_user_channels(user, event)
            for channel in channels:
                if channel not in ("email", "odoo", "line"):
                    _logger.warning("Unknown notification channel: %s", channel)
                    continue
                Queue.create(
                    {
                        "partner_id": partner.id,
                        "channel": channel,
                        "message": message,
                        "subject": subject,
                        "event": event,
                    }
                )

    @api.model
    def _get_user_channels(self, user, event):
        if not user:
            return ["odoo"]
        return self.env["notification.preference"].get_channels(user.id, event)

    @api.model
    def _send_email(self, partner, message, subject=None):
        if not partner.email:
            _logger.info("Skipping email for partner %s: no email address", partner.id)
            return
        template = self.env.ref(
            "od19_notification_multi_channel.mail_template_notification",
            raise_if_not_found=False,
        )
        if template:
            template.with_context(
                notification_message=message,
                notification_subject=subject or "Notification",
            ).send_mail(
                partner.id,
                force_send=True,
                email_values={"email_to": partner.email},
            )
        else:
            self.env["mail.mail"].sudo().create(
                {
                    "subject": subject or "Notification",
                    "body_html": "<p>%s</p>" % message,
                    "email_to": partner.email,
                }
            ).send()

    @api.model
    def _send_odoo_notification(self, partner, message, subtype_xmlid=None):
        subtype = None
        if subtype_xmlid:
            try:
                subtype = self.env.ref(subtype_xmlid)
            except ValueError:
                subtype = None
        if not subtype:
            subtype = self.env.ref("mail.mt_comment", raise_if_not_found=False)
        self.env["mail.thread"].message_notify(
            partner_ids=partner.ids,
            body=message,
            subject=False,
            subtype_id=subtype.id if subtype else None,
        )

    @api.model
    def _send_line(self, partner, message):
        company = self.env.company
        if not company.line_enabled:
            return
        token = company.line_channel_access_token
        line_user_id = partner.line_user_id
        if not token or not line_user_id:
            _logger.info(
                "Skipping LINE for partner %s: missing token or LINE user id",
                partner.id,
            )
            return
        headers = {
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json",
        }
        payload = {
            "to": line_user_id,
            "messages": [{"type": "text", "text": message[:5000]}],
        }
        try:
            response = requests.post(
                urljoin(LINE_PUSH_ENDPOINT, ""),
                headers=headers,
                data=json.dumps(payload),
                timeout=10,
            )
        except requests.exceptions.RequestException as error:
            # Offline / network outage: fail with a clear message instead of a
            # raw requests traceback so the queue retry stays readable.
            _logger.warning(
                "LINE push failed for partner %s: %s", partner.id, error
            )
            raise UserError(
                _(
                    "Cannot reach the LINE Messaging API. "
                    "Please check the internet connection and try again."
                )
            ) from error
        if response.status_code != 200:
            _logger.error(
                "LINE push failed for partner %s: %s %s",
                partner.id,
                response.status_code,
                response.text,
            )
            raise UserError(
                _("LINE push failed: %(status)s %(body)s")
                % {"status": response.status_code, "body": response.text}
            )
