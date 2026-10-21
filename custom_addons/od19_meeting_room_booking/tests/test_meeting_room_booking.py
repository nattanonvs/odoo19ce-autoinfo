from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMeetingRoomBooking(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Room = cls.env["od19.meeting.room"]
        cls.Booking = cls.env["od19.meeting.room.booking"]

        cls.room = cls.Room.create(
            {
                "name": "Test Meeting Room",
                "capacity": 10,
            }
        )

    def _create_booking(self, **overrides):
        start_dt = fields.Datetime.now() + timedelta(days=1)
        vals = {
            "name": "Weekly Review",
            "room_id": self.room.id,
            "organizer_id": self.env.user.id,
            "participant_count": 4,
            "start_datetime": start_dt,
            "end_datetime": start_dt + timedelta(hours=2),
        }
        vals.update(overrides)
        return self.Booking.create(vals)

    def test_sequence_generated(self):
        booking = self._create_booking()
        self.assertTrue(booking.reference)
        self.assertNotEqual(booking.reference, "New")

    def test_submit_and_approve_flow(self):
        booking = self._create_booking()
        booking.action_submit()
        self.assertEqual(booking.state, "submitted")
        booking.action_approve()
        self.assertEqual(booking.state, "approved")
        self.assertEqual(booking.approved_by, self.env.user)

    def test_overlapping_booking_is_blocked(self):
        booking_a = self._create_booking()
        booking_a.action_submit()
        booking_a.action_approve()
        booking_b = self._create_booking()
        with self.assertRaises(ValidationError):
            booking_b.action_submit()

    def test_capacity_cannot_be_exceeded(self):
        with self.assertRaises(ValidationError):
            self._create_booking(participant_count=99)

    def test_end_datetime_must_be_after_start_datetime(self):
        start_dt = fields.Datetime.now() + timedelta(days=1)
        with self.assertRaises(Exception):
            self._create_booking(
                start_datetime=start_dt,
                end_datetime=start_dt - timedelta(hours=1),
            )
