import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

MAX_RETRY = 3


def _strip_html(text):
    """Remove HTML tags and decode common entities for plain-text channels."""
    if not text:
        return text
    # Replace block-level tags with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div\s*>", "\n", text, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common entities
    replacements = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&apos;": "'",
        "&nbsp;": " ",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class NotificationQueue(models.Model):
    _name = "od19.notification.queue"
    _description = "Notification Queue"
    _order = "create_date desc"

    partner_id = fields.Many2one(
        "res.partner",
        string="Recipient",
        required=True,
        ondelete="cascade",
        index=True,
    )
    channel = fields.Selection(
        [
            ("email", "Email"),
            ("odoo", "Odoo Inbox"),
            ("line", "LINE"),
        ],
        string="Channel",
        required=True,
        index=True,
    )
    message = fields.Text(string="Message", required=True)
    subject = fields.Char(string="Subject")
    event = fields.Char(string="Event", default="default", index=True)
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("sending", "Sending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="pending",
        required=True,
        index=True,
    )
    retry_count = fields.Integer(
        string="Retry Count",
        default=0,
        help="Number of times this notification has been retried.",
    )
    error_message = fields.Text(string="Error Message", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    def action_send(self):
        """Process a single queued notification."""
        self.ensure_one()
        service = self.env["notification.service"]
        self.write({"state": "sending"})
        try:
            if self.channel == "email":
                service._send_email(self.partner_id, self.message, self.subject)
            elif self.channel == "odoo":
                service._send_odoo_notification(self.partner_id, self.message)
            elif self.channel == "line":
                plain_message = _strip_html(self.message)
                service._send_line(self.partner_id, plain_message)
            else:
                raise ValueError("Unknown channel: %s" % self.channel)
            self.write({"state": "sent", "error_message": False})
        except Exception as exc:  # noqa: BLE001
            _logger.error(
                "Notification queue #%s failed on channel %s: %s",
                self.id,
                self.channel,
                exc,
                exc_info=True,
            )
            self.write(
                {
                    "state": "failed",
                    "error_message": str(exc),
                    "retry_count": self.retry_count + 1,
                }
            )

    @api.model
    def _cron_process_queue(self):
        """Process pending notifications and retry failed ones (up to MAX_RETRY)."""
        # Process pending items first
        pending = self.search([("state", "=", "pending")], limit=100)
        for item in pending:
            item.action_send()

        # Retry failed items that haven't exceeded max retries
        failed = self.search(
            [
                ("state", "=", "failed"),
                ("retry_count", "<", MAX_RETRY),
            ],
            limit=100,
        )
        for item in failed:
            item.action_send()
