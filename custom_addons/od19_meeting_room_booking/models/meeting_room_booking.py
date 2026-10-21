from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# Bookings in these states no longer hold the room.
RELEASED_STATES = ("cancelled",)


class MeetingRoomBooking(models.Model):
    """A single reservation of a meeting room.

    The workflow is intentionally short: a booking is confirmed as soon as it is
    created, so a user only has to pick a room, a time slot and save.
    """

    _name = "od19.meeting.room.booking"
    _description = "Meeting Room Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "start_datetime desc, id desc"
    _check_company_auto = True

    reference = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
    )
    name = fields.Char(string="Meeting Topic", required=True, tracking=True)
    room_id = fields.Many2one(
        comodel_name="od19.meeting.room",
        string="Meeting Room",
        required=True,
        tracking=True,
        index=True,
    )
    organizer_id = fields.Many2one(
        comodel_name="res.users",
        string="Organizer",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    participant_count = fields.Integer(string="Attendees", default=2, tracking=True)
    start_datetime = fields.Datetime(
        string="Start", required=True, tracking=True, index=True
    )
    end_datetime = fields.Datetime(
        string="End", required=True, tracking=True, index=True
    )
    duration_hours = fields.Float(
        string="Duration (hours)", compute="_compute_duration_hours"
    )
    purpose = fields.Text(string="Agenda")
    attendee_summary = fields.Text(string="Attendee List")
    equipment_request = fields.Text(string="Equipment Needed")
    state = fields.Selection(
        selection=[
            ("booked", "Booked"),
            ("in_use", "In Use"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="booked",
        required=True,
        tracking=True,
        copy=False,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    _end_after_start = models.Constraint(
        "CHECK(end_datetime > start_datetime)",
        "The end time must be after the start time.",
    )

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("start_datetime", "end_datetime")
    def _compute_duration_hours(self):
        for booking in self:
            if booking.start_datetime and booking.end_datetime:
                delta = booking.end_datetime - booking.start_datetime
                booking.duration_hours = delta.total_seconds() / 3600.0
            else:
                booking.duration_hours = 0.0

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.model
    def _od19_check_period(self, start_datetime, end_datetime):
        """Reject an inverted period in Python.

        The same rule is enforced by a SQL CHECK constraint, but that one fires
        after the row has been sent to Postgres and surfaces a raw database
        error instead of a readable message, so validate before writing.
        """
        start = fields.Datetime.to_datetime(start_datetime)
        end = fields.Datetime.to_datetime(end_datetime)
        if start and end and end <= start:
            raise ValidationError(_("The end time must be after the start time."))

    @api.constrains("start_datetime", "end_datetime")
    def _check_period(self):
        for booking in self:
            self._od19_check_period(booking.start_datetime, booking.end_datetime)

    @api.constrains("room_id", "start_datetime", "end_datetime", "state")
    def _check_overlapping_booking(self):
        for booking in self:
            if (
                not booking.room_id
                or not booking.start_datetime
                or not booking.end_datetime
                or booking.state in RELEASED_STATES
            ):
                continue
            overlapping = self.search_count(
                [
                    ("id", "!=", booking.id),
                    ("room_id", "=", booking.room_id.id),
                    ("state", "not in", RELEASED_STATES),
                    ("start_datetime", "<", booking.end_datetime),
                    ("end_datetime", ">", booking.start_datetime),
                ]
            )
            if overlapping:
                raise ValidationError(
                    _(
                        "Meeting room %(room)s is already booked during the selected time.",
                        room=booking.room_id.display_name,
                    )
                )

    @api.constrains("participant_count", "room_id")
    def _check_capacity(self):
        for booking in self:
            if (
                booking.room_id
                and booking.participant_count
                and booking.room_id.capacity
                and booking.participant_count > booking.room_id.capacity
            ):
                raise ValidationError(
                    _(
                        "The attendee count exceeds the room capacity (%(capacity)s).",
                        capacity=booking.room_id.capacity,
                    )
                )

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._od19_check_period(
                vals.get("start_datetime"), vals.get("end_datetime")
            )
            if vals.get("reference", _("New")) == _("New"):
                vals["reference"] = (
                    self.env["ir.sequence"].next_by_code("od19.meeting.room.booking")
                    or _("New")
                )
            vals.setdefault("state", "booked")
        return super().create(vals_list)

    def write(self, vals):
        if "start_datetime" in vals or "end_datetime" in vals:
            for booking in self:
                self._od19_check_period(
                    vals.get("start_datetime") or booking.start_datetime,
                    vals.get("end_datetime") or booking.end_datetime,
                )
        return super().write(vals)

    # ------------------------------------------------------------------
    # State actions
    # ------------------------------------------------------------------
    def action_start_meeting(self):
        self.write({"state": "in_use"})

    def action_complete(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reopen(self):
        """Put a cancelled or finished booking back into the booked state."""
        self.write({"state": "booked"})
