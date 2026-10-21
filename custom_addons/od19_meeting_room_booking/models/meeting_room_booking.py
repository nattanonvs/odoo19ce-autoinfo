from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MeetingRoomBooking(models.Model):
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
        required=True,
        tracking=True,
        index=True,
    )
    organizer_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        index=True,
    )
    participant_count = fields.Integer(default=2, tracking=True)
    start_datetime = fields.Datetime(required=True, tracking=True, index=True)
    end_datetime = fields.Datetime(required=True, tracking=True, index=True)
    duration_hours = fields.Float(compute="_compute_duration_hours")
    purpose = fields.Text()
    attendee_summary = fields.Text(string="Attendees")
    equipment_request = fields.Text()
    approval_note = fields.Text()
    approved_by = fields.Many2one(comodel_name="res.users", readonly=True)
    approved_on = fields.Datetime(readonly=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("in_use", "In Use"),
            ("done", "Done"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
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

    _date_order = models.Constraint(
        "CHECK(end_datetime > start_datetime)",
        "The end time must be after the start time.",
    )

    @api.depends("start_datetime", "end_datetime")
    def _compute_duration_hours(self):
        for booking in self:
            if booking.start_datetime and booking.end_datetime:
                duration = booking.end_datetime - booking.start_datetime
                booking.duration_hours = duration.total_seconds() / 3600.0
            else:
                booking.duration_hours = 0.0

    @api.constrains("room_id", "start_datetime", "end_datetime", "state")
    def _check_overlapping_booking(self):
        for booking in self:
            if (
                not booking.room_id
                or not booking.start_datetime
                or not booking.end_datetime
                or booking.state in ("draft", "cancelled", "rejected")
            ):
                continue
            overlap_count = self.search_count(
                [
                    ("id", "!=", booking.id),
                    ("room_id", "=", booking.room_id.id),
                    ("state", "not in", ("draft", "cancelled", "rejected")),
                    ("start_datetime", "<", booking.end_datetime),
                    ("end_datetime", ">", booking.start_datetime),
                ]
            )
            if overlap_count:
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
                        "The participant count exceeds the room capacity (%(capacity)s).",
                        capacity=booking.room_id.capacity,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", _("New")) == _("New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "od19.meeting.room.booking"
                ) or _("New")
        return super().create(vals_list)

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_approve(self):
        self.write(
            {
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_on": fields.Datetime.now(),
            }
        )

    def action_start_meeting(self):
        self.write({"state": "in_use"})

    def action_complete(self):
        self.write({"state": "done"})

    def action_reject(self):
        self.write({"state": "rejected"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_reset_draft(self):
        self.write(
            {
                "state": "draft",
                "approved_by": False,
                "approved_on": False,
            }
        )
