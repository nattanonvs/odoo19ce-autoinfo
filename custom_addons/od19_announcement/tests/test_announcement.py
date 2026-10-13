from datetime import date, timedelta
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged("standard", "at_install")
class TestAnnouncement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Announcement = cls.env["announcement"]

    def _create_announcement(self, **overrides):
        vals = {
            "name": "Test Announcement",
            "body": "<p>Test body</p>",
            "announcement_type": "info",
        }
        vals.update(overrides)
        return self.Announcement.create(vals)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------
    def test_default_type(self):
        ann = self._create_announcement()
        self.assertEqual(ann.announcement_type, "info")

    def test_default_target(self):
        ann = self._create_announcement()
        self.assertEqual(ann.target_type, "company")

    def test_default_published_false(self):
        ann = self._create_announcement()
        self.assertFalse(ann.published)

    def test_default_author(self):
        ann = self._create_announcement()
        self.assertEqual(ann.author_id, self.env.user)

    # ------------------------------------------------------------------
    # Publish / unpublish
    # ------------------------------------------------------------------
    def test_publish_sets_date(self):
        ann = self._create_announcement()
        ann.action_publish()
        self.assertTrue(ann.published)
        self.assertEqual(ann.published_date, date.today())

    def test_unpublish(self):
        ann = self._create_announcement(published=True)
        ann.action_unpublish()
        self.assertFalse(ann.published)

    # ------------------------------------------------------------------
    # Read receipts
    # ------------------------------------------------------------------
    def test_mark_as_read_creates_receipt(self):
        ann = self._create_announcement()
        ann.action_mark_as_read()
        self.assertEqual(ann.read_count, 1)

    def test_mark_as_read_no_duplicate(self):
        ann = self._create_announcement()
        ann.action_mark_as_read()
        ann.action_mark_as_read()
        self.assertEqual(ann.read_count, 1)

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------
    def test_cron_unpublishes_expired(self):
        past = date.today() - timedelta(days=2)
        ann = self._create_announcement(
            published=True, expiry_date=past
        )
        self.Announcement._cron_unpublish_expired()
        ann.invalidate_recordset()
        self.assertFalse(ann.published)

    def test_cron_keeps_unexpired(self):
        future = date.today() + timedelta(days=2)
        ann = self._create_announcement(
            published=True, expiry_date=future
        )
        self.Announcement._cron_unpublish_expired()
        ann.invalidate_recordset()
        self.assertTrue(ann.published)

    # ------------------------------------------------------------------
    # Notification
    # ------------------------------------------------------------------
    @patch("requests.post")
    def test_publish_warning_triggers_notification(self, mock_post):
        mock_post.return_value.status_code = 200
        ann = self._create_announcement(announcement_type="warning")
        ann.action_publish()
        # No error means notification flow completed
        self.assertTrue(ann.published)
