from odoo import api, fields, models


class MeetingRoom(models.Model):
    _name = "od19.meeting.room"
    _description = "Meeting Room"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name, id"
    _check_company_auto = True

    name = fields.Char(required=True, tracking=True, translate=True)
    code = fields.Char(tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    building = fields.Char(tracking=True)
    floor = fields.Char(tracking=True)
    capacity = fields.Integer(default=1, tracking=True)
    color = fields.Integer(default=1)
    image_1920 = fields.Image(max_width=1920, max_height=1920)
    has_projector = fields.Boolean(string="Projector")
    has_video_conference = fields.Boolean(string="Video Conference")
    has_whiteboard = fields.Boolean(string="Whiteboard")
    has_display = fields.Boolean(string="Large Display")
    booking_policy = fields.Text(translate=True)
    note = fields.Html(translate=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    booking_ids = fields.One2many(
        comodel_name="od19.meeting.room.booking",
        inverse_name="room_id",
        string="Bookings",
    )
    booking_count = fields.Integer(compute="_compute_booking_count")
    availability_state = fields.Selection(
        selection=[
            ("available", "Available"),
            ("reserved", "Reserved"),
            ("in_use", "In Use"),
        ],
        compute="_compute_availability_state",
        search="_search_availability_state",
    )

    @api.depends("booking_ids")
    def _compute_booking_count(self):
        grouped = self.env["od19.meeting.room.booking"]._read_group(
            [("room_id", "in", self.ids)],
            ["room_id"],
            ["__count"],
        )
        counts = {room.id: count for room, count in grouped}
        for room in self:
            room.booking_count = counts.get(room.id, 0)

    @api.depends("booking_ids.state", "booking_ids.start_datetime", "booking_ids.end_datetime")
    def _compute_availability_state(self):
        now = fields.Datetime.now()
        Booking = self.env["od19.meeting.room.booking"]
        for room in self:
            active_booking = Booking.search(
                [
                    ("room_id", "=", room.id),
                    ("state", "in", ("booked", "in_use")),
                    ("start_datetime", "<=", now),
                    ("end_datetime", ">", now),
                ],
                limit=1,
            )
            future_booking = Booking.search(
                [
                    ("room_id", "=", room.id),
                    ("state", "=", "booked"),
                    ("start_datetime", ">", now),
                ],
                limit=1,
            )
            if active_booking:
                room.availability_state = "in_use"
            elif future_booking:
                room.availability_state = "reserved"
            else:
                room.availability_state = "available"

    @api.model
    def _search_availability_state(self, operator, value):
        """Make the computed ``availability_state`` usable inside search domains."""
        if operator in ("in", "not in"):
            values = list(value or [])
        else:
            values = [value]
        matching = self.env["od19.meeting.room"].search([]).filtered(
            lambda room: room.availability_state in values
        )
        if operator in ("!=", "not in"):
            return [("id", "not in", matching.ids)]
        return [("id", "in", matching.ids)]

    def _od19_current_booking(self):
        """Return the booking that currently occupies the room, if any."""
        self.ensure_one()
        now = fields.Datetime.now()
        return self.env["od19.meeting.room.booking"].search(
            [
                ("room_id", "=", self.id),
                ("state", "in", ("booked", "in_use")),
                ("start_datetime", "<=", now),
                ("end_datetime", ">", now),
            ],
            limit=1,
        )

    def _od19_next_booking(self):
        """Return the next upcoming booking of the room, if any."""
        self.ensure_one()
        return self.env["od19.meeting.room.booking"].search(
            [
                ("room_id", "=", self.id),
                ("state", "=", "booked"),
                ("start_datetime", ">", fields.Datetime.now()),
            ],
            order="start_datetime asc",
            limit=1,
        )

    def action_view_bookings(self):
        self.ensure_one()
        action = self.env.ref(
            "od19_meeting_room_booking.action_meeting_room_booking"
        ).read()[0]
        action["domain"] = [("room_id", "=", self.id)]
        action["context"] = {"default_room_id": self.id}
        return action
