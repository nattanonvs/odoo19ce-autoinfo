import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestNotificationMultiChannel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Channel = cls.env["notification.channel"]
        cls.Preference = cls.env["notification.preference"]
        cls.Service = cls.env["notification.service"]
        cls.Partner = cls.env["res.partner"]

        cls.channel_email = cls.env.ref(
            "od19_notification_multi_channel.notification_channel_email"
        )
        cls.channel_odoo = cls.env.ref(
            "od19_notification_multi_channel.notification_channel_odoo"
        )
        cls.channel_line = cls.env.ref(
            "od19_notification_multi_channel.notification_channel_line"
        )

        cls.user = cls.env.ref("base.user_admin")
        cls.partner = cls.user.partner_id
        cls.partner.write({"email": "admin@example.com", "line_user_id": "U12345"})

        cls.company = cls.env.company
        cls.company.write(
            {
                "line_enabled": True,
                "line_channel_access_token": "test-token",
            }
        )

    # ------------------------------------------------------------------
    # Channel & preference
    # ------------------------------------------------------------------
    def test_default_channels_created(self):
        channels = self.Channel.search([])
        types = set(channels.mapped("channel_type"))
        self.assertIn("email", types)
        self.assertIn("odoo", types)
        self.assertIn("line", types)

    def test_get_channels_without_preference(self):
        channels = self.Preference.get_channels(self.user.id, "default")
        self.assertEqual(channels, ["odoo"])

    def test_get_channels_with_preference(self):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [
                    (6, 0, [self.channel_email.id, self.channel_line.id])
                ],
            }
        )
        channels = self.Preference.get_channels(self.user.id, "default")
        self.assertIn("email", channels)
        self.assertIn("line", channels)
        self.assertNotIn("odoo", channels)

    def test_get_channels_fallback_to_default(self):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_odoo.id])],
            }
        )
        channels = self.Preference.get_channels(self.user.id, "asset_loan_due")
        self.assertEqual(channels, ["odoo"])

    # ------------------------------------------------------------------
    # notify() dispatching (now routed through the queue)
    # ------------------------------------------------------------------
    def test_notify_creates_queue_items(self):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [
                    (6, 0, [self.channel_email.id, self.channel_odoo.id, self.channel_line.id])
                ],
            }
        )
        Queue = self.env["od19.notification.queue"]
        before = Queue.search_count([])
        self.Service.notify(self.partner, "Test message")
        after = Queue.search_count([])
        self.assertEqual(after - before, 3)

    @patch("requests.post")
    def test_notify_skips_line_when_disabled(self, mock_post):
        self.company.line_enabled = False
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        self.Service.notify(self.partner, "Test message")
        # Queue item is created but LINE is not called until processed.
        queue = self.env["od19.notification.queue"].search([], order="id desc", limit=1)
        self.assertEqual(queue.channel, "line")
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_notify_skips_line_without_user_id(self, mock_post):
        self.partner.line_user_id = False
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        self.Service.notify(self.partner, "Test message")
        queue = self.env["od19.notification.queue"].search([], order="id desc", limit=1)
        self.assertEqual(queue.channel, "line")
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_line_push_strips_html_before_sending(self, mock_post):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        mock_post.return_value.status_code = 200
        queue = self.env["od19.notification.queue"].create(
            {
                "partner_id": self.partner.id,
                "channel": "line",
                "message": "<p>Hello <b>LINE</b></p><br/>New line",
            }
        )
        queue.action_send()
        self.assertEqual(queue.state, "sent")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("data") or (
            call_args.args[2] if len(call_args.args) > 2 else "{}"
        )
        data = json.loads(payload)
        self.assertNotIn("<b>", data["messages"][0]["text"])
        self.assertNotIn("<p>", data["messages"][0]["text"])
        self.assertIn("Hello LINE", data["messages"][0]["text"])

    @patch("requests.post")
    def test_notify_empty_message_does_nothing(self, mock_post):
        before = self.env["od19.notification.queue"].search_count([])
        self.Service.notify(self.partner, "")
        after = self.env["od19.notification.queue"].search_count([])
        self.assertEqual(after, before, "No queue item for empty message")
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_notify_empty_partners_does_nothing(self, mock_post):
        before = self.env["od19.notification.queue"].search_count([])
        self.Service.notify(self.Partner, "Test")
        after = self.env["od19.notification.queue"].search_count([])
        self.assertEqual(after, before, "No queue item for empty partners")
        mock_post.assert_not_called()

    # ------------------------------------------------------------------
    # Notification queue processing & retry
    # ------------------------------------------------------------------
    @patch("requests.post")
    def test_queue_send_marks_sent(self, mock_post):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        mock_post.return_value.status_code = 200
        queue = self.env["od19.notification.queue"].create(
            {
                "partner_id": self.partner.id,
                "channel": "line",
                "message": "Hello",
            }
        )
        queue.action_send()
        self.assertEqual(queue.state, "sent")

    @patch("requests.post")
    def test_queue_failure_increments_retry(self, mock_post):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        mock_post.return_value.status_code = 500
        queue = self.env["od19.notification.queue"].create(
            {
                "partner_id": self.partner.id,
                "channel": "line",
                "message": "Hello",
            }
        )
        queue.action_send()
        self.assertEqual(queue.state, "failed")
        self.assertEqual(queue.retry_count, 1)
        self.assertTrue(queue.error_message)

    @patch("requests.post")
    def test_cron_processes_pending_and_retries_failed(self, mock_post):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        mock_post.return_value.status_code = 200
        # Create a pending item
        pending = self.env["od19.notification.queue"].create(
            {
                "partner_id": self.partner.id,
                "channel": "line",
                "message": "Pending",
            }
        )
        # Create a failed item with retry_count < 3
        failed = self.env["od19.notification.queue"].create(
            {
                "partner_id": self.partner.id,
                "channel": "line",
                "message": "Failed",
                "state": "failed",
                "retry_count": 1,
            }
        )
        self.env["od19.notification.queue"]._cron_process_queue()
        self.assertEqual(pending.state, "sent")
        self.assertEqual(failed.state, "sent")

    def test_cron_skips_failed_exceeding_max_retry(self):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        failed = self.env["od19.notification.queue"].create(
            {
                "partner_id": self.partner.id,
                "channel": "line",
                "message": "Failed",
                "state": "failed",
                "retry_count": 3,
            }
        )
        self.env["od19.notification.queue"]._cron_process_queue()
        # Should remain failed since retry_count >= MAX_RETRY
        self.assertEqual(failed.state, "failed")

