from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMeetingRoomBooking(TransactionCase):
    """A booking is confirmed immediately: no approval step is involved."""

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

    def test_booking_is_confirmed_on_create(self):
        booking = self._create_booking()
        self.assertEqual(booking.state, "booked")

    def test_sequence_generated(self):
        booking = self._create_booking()
        self.assertTrue(booking.reference)
        self.assertNotEqual(booking.reference, "New")

    def test_duration_is_computed(self):
        booking = self._create_booking()
        self.assertAlmostEqual(booking.duration_hours, 2.0, places=2)

    def test_overlapping_booking_is_blocked(self):
        self._create_booking()
        with self.assertRaises(ValidationError):
            self._create_booking(name="Conflicting Review")

    def test_cancelled_booking_frees_the_room(self):
        first = self._create_booking()
        first.action_cancel()
        second = self._create_booking(name="Replacement Review")
        self.assertEqual(second.state, "booked")

    def test_capacity_cannot_be_exceeded(self):
        with self.assertRaises(ValidationError):
            self._create_booking(participant_count=99)

    def test_end_datetime_must_be_after_start_datetime(self):
        start_dt = fields.Datetime.now() + timedelta(days=1)
        with self.assertRaises(ValidationError):
            self._create_booking(
                start_datetime=start_dt,
                end_datetime=start_dt - timedelta(hours=1),
            )

    def test_lifecycle_start_and_complete(self):
        booking = self._create_booking()
        booking.action_start_meeting()
        self.assertEqual(booking.state, "in_use")
        booking.action_complete()
        self.assertEqual(booking.state, "done")

    def test_room_availability_reflects_current_booking(self):
        now = fields.Datetime.now()
        self._create_booking(
            start_datetime=now - timedelta(minutes=30),
            end_datetime=now + timedelta(minutes=30),
        )
        self.room.invalidate_recordset(["availability_state"])
        self.assertEqual(self.room.availability_state, "in_use")

    def test_room_availability_reserved_for_future_booking(self):
        self._create_booking()
        self.room.invalidate_recordset(["availability_state"])
        self.assertEqual(self.room.availability_state, "reserved")

    def test_search_by_availability_state(self):
        self._create_booking()
        self.assertEqual(
            self.Room.search(
                [("id", "=", self.room.id), ("availability_state", "=", "reserved")]
            ),
            self.room,
        )
        self.assertFalse(
            self.Room.search(
                [("id", "=", self.room.id), ("availability_state", "=", "available")]
            )
        )
