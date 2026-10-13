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
    # notify() dispatching
    # ------------------------------------------------------------------
    @patch("requests.post")
    def test_notify_dispatches_to_selected_channels(self, mock_post):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [
                    (6, 0, [self.channel_email.id, self.channel_odoo.id, self.channel_line.id])
                ],
            }
        )
        mock_post.return_value.status_code = 200
        mail_before = self.env["mail.mail"].search_count([])
        notif_before = self.env["mail.notification"].search_count([])

        self.Service.notify(self.partner, "Test message")

        mail_after = self.env["mail.mail"].search_count([])
        notif_after = self.env["mail.notification"].search_count([])
        self.assertGreater(mail_after, mail_before, "Email should be sent")
        self.assertGreater(notif_after, notif_before, "Odoo notification should be sent")
        mock_post.assert_called_once()

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
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_line_push_calls_line_api(self, mock_post):
        self.Preference.create(
            {
                "user_id": self.user.id,
                "event": "default",
                "channel_ids": [(6, 0, [self.channel_line.id])],
            }
        )
        mock_post.return_value.status_code = 200
        self.Service.notify(self.partner, "Hello LINE")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args.kwargs.get("data") or (
            call_args.args[2] if len(call_args.args) > 2 else "{}"
        )
        data = json.loads(payload)
        self.assertEqual(data["to"], "U12345")
        self.assertEqual(data["messages"][0]["text"], "Hello LINE")

    @patch("requests.post")
    def test_notify_empty_message_does_nothing(self, mock_post):
        mail_before = self.env["mail.mail"].search_count([])
        self.Service.notify(self.partner, "")
        mail_after = self.env["mail.mail"].search_count([])
        self.assertEqual(mail_after, mail_before, "No email for empty message")
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_notify_empty_partners_does_nothing(self, mock_post):
        mail_before = self.env["mail.mail"].search_count([])
        self.Service.notify(self.Partner, "Test")
        mail_after = self.env["mail.mail"].search_count([])
        self.assertEqual(mail_after, mail_before, "No email for empty partners")
        mock_post.assert_not_called()
